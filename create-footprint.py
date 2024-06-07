import numpy as np
import xarray as xr
import pandas as pd
import logging
import os

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - [%(levelname)s] %(message)s',
                    datefmt='%d/%m/%Y %H:%M:%S')
logger = logging.getLogger(__name__)

AIR_DENSITY_URL = "/usr/local/FLEXPART/vertical_profile_of_air_density.csv"
PIXEL_AREA_URL = "/usr/local/FLEXPART/pixel_areas_005deg.nc"

IDX_CHUNK = 160
IDX_CHUNK_FOR_COORDS = IDX_CHUNK * 40

def get_air_vertical_profile():
    vertical_profile_of_air_density = pd.read_csv(AIR_DENSITY_URL, index_col='height_in_m', dtype=np.float32)['density_in_kg_per_m3']
    vertical_profile_of_air_density = xr.DataArray.from_series(vertical_profile_of_air_density).rename({'height_in_m': 'height'})
    vertical_profile_of_air_density['height'] = vertical_profile_of_air_density.height.astype('f4')
    vertical_profile_of_air_density.name = 'air_density'
    vertical_profile_of_air_density.attrs = dict(long_name='air_density', units='kg m-3')
    return vertical_profile_of_air_density

def _normalize_longitude_ufunc(arr, smallest_lon_coord=-180.):
    return (arr - smallest_lon_coord) % 360. + smallest_lon_coord

def normalize_longitude(ds, lon_label, smallest_lon_coord=-180., keep_attrs=False):
    lon_coords = ds[lon_label]
    aligned_lon_coords = _normalize_longitude_ufunc(lon_coords, smallest_lon_coord=smallest_lon_coord)
    if keep_attrs:
        aligned_lon_coords = aligned_lon_coords.assign_attrs(lon_coords.attrs)
    if not lon_coords.equals(aligned_lon_coords):
        old_lon_coords_monotonic = lon_coords.indexes[lon_label].is_monotonic_increasing
        ds = ds.assign_coords({lon_label: aligned_lon_coords})
        if old_lon_coords_monotonic:
            smallest_lon_idx = aligned_lon_coords.argmin(dim=lon_label).item()
            ds = ds.roll(shifts={lon_label: -smallest_lon_idx}, roll_coords=True)
        else:
            ds = ds.sortby(lon_label)
    return ds

def is_coord_regularly_gridded(coord, abs_err=None):
    """
    Checks if a coordinate variable is regularly gridded (spaced)
    :param coord: a 1-dim array-like
    :param abs_err: float or timedelta; maximal allowed absolute error when checking for equal spaces
    :return: bool
    """
    coord = np.asanyarray(coord)
    if len(coord.shape) != 1:
        raise ValueError(f'coord must be 1-dimensional')
    n, = coord.shape
    if n < 2:
        return True
    d_coord = np.diff(coord)
    if abs_err is None:
        try:
            eps = np.finfo(coord.dtype).eps
        except ValueError:
            # dtype not inexact
            return np.all(d_coord == d_coord[0])
        # floating-point
        abs_err = 4 * eps * np.max(np.fabs(coord))
    return np.all(np.fabs(d_coord - d_coord[0]) <= 2 * abs_err)

def make_coordinates_increasing(ds, coord_labels, allow_sorting=True):
    """
    Sorts coordinates
    :param self: an xarray Dataset or DataArray
    :param coord_labels: a string or an interable of strings - labels of dataset's coordinates
    :param allow_sorting: bool; default True; indicate if sortby method is allowed to be used as a last resort
    :return: ds with a chosen coordinate(s) in increasing order
    """
    if isinstance(coord_labels, str):
        coord_labels = (coord_labels, )
    for coord_label in coord_labels:
        if not ds.indexes[coord_label].is_monotonic_increasing:
            if ds.indexes[coord_label].is_monotonic_decreasing:
                ds = ds.isel({coord_label: slice(None, None, -1)})
            elif allow_sorting:
                ds = ds.sortby(coord_label)
            else:
                raise ValueError(f'{ds.xrx.short_dataset_repr()} has coordinate {coord_label} which is neither increasing nor decreasing')
    return ds

def regrid(ds, target_coords, method='mean', tolerance=None, skipna=None, keep_attrs=False,
            keep_ori_dims_order=True, keep_ori_coords=True, **agg_method_kwargs):

    # check if target dimensions are contained in dimensions of ds
    ds_dims = ds.dims
    for coord_label in target_coords:
        if coord_label not in ds_dims:
            raise ValueError(f'{coord_label} not found among ds dimensions: {list(ds_dims)}')

    if keep_ori_dims_order:
        target_coords = {coord_label: target_coords[coord_label] for coord_label in ds_dims if coord_label in target_coords}

    ds = make_coordinates_increasing(ds, target_coords.keys())

    if method in ['linear', 'nearest']:
        interpolator_kwargs = {'fill_value': 'extrapolate'} if method == 'nearest' else None
        regridded_ds = ds.interp(coords=target_coords, method=method, assume_sorted=True, kwargs=interpolator_kwargs)
    else:
        # check if target coordinates are equally spaced
        for coord_label, target_coord in target_coords.items():
            if not is_coord_regularly_gridded(target_coord):
                raise ValueError(f'{coord_label} is not be regularly gridded: {target_coord}')
        # check if coordinates of ds are equally spaced
        for coord_label in target_coords:
            if not is_coord_regularly_gridded(ds[coord_label]):
                raise ValueError(f'ds has {coord_label} coordinate not regularly gridded: {ds[coord_label]}')

        # trim the domain of ds to target_coords, if necessary
        trim_by_dim = {}
        for coord_label, target_coord in target_coords.items():
            target_coord = np.asanyarray(target_coord)
            n_target_coord, = target_coord.shape
            target_coord_min, target_coord_max = target_coord.min(), target_coord.max()
            if n_target_coord >= 2:
                step = (target_coord_max - target_coord_min) / (n_target_coord - 1)
                if ds[coord_label].min() < target_coord_min - step / 2 or \
                        ds[coord_label].max() > target_coord_max + step / 2:
                    trim_by_dim[coord_label] = slice(target_coord_min - step / 2, target_coord_max + step / 2)
        if trim_by_dim:
            ds = ds.sel(trim_by_dim)

        # coarsen
        window_size = {}
        for coord_label, target_coord in target_coords.items():
            if len(ds[coord_label]) % len(target_coord) != 0:
                raise ValueError(f'resolution of {coord_label} not compatible: '
                                    f'{len(ds[coord_label])} must be a multiple of {len(target_coord)}\n'
                                    f'ds[{coord_label}] = {ds[coord_label]}\n'
                                    f'target_coord = {target_coord}')
            window_size_for_coord = len(ds[coord_label]) // len(target_coord)
            if window_size_for_coord > 1:
                window_size[coord_label] = window_size_for_coord
        coarsen_ds = ds.coarsen(dim=window_size, boundary='exact', coord_func='mean')
        coarsen_ds_agg_method = getattr(coarsen_ds, method)
        if skipna is not None:
            agg_method_kwargs['skipna'] = skipna
        if keep_attrs is not None:
            agg_method_kwargs['keep_attrs'] = keep_attrs
        regridded_ds = coarsen_ds_agg_method(**agg_method_kwargs)

        # adjust coordinates of regridded_ds so that they fit to target_coords
        # necessary to map existing coordinates to new coordinates (e.g. x_=x, etc),
        # or to rearrange increasing coords to decreasing (or vice-versa)
        # and if it has no essential effect, it is a cheap operation
        try:
            regridded_ds = regridded_ds.sel(target_coords, method='nearest', tolerance=tolerance)
        except KeyError:
            raise ValueError(f"target grid is not compatible with a source grid; "
                                f"check grids or adjust 'tolerance' parameter\n"
                                f"regridded_ds={regridded_ds}\n"
                                f"target_coords={target_coord}")
        # overwrite coordinates
        regridded_ds = regridded_ds.assign_coords({r_dim: target_coords[r_dim]
                                                    for r_dim in set(regridded_ds.dims).intersection(target_coords)})
    # drop the dataset/dataaray original coordinate variables which became auxiliary coordinates after regridding
    if not keep_ori_coords:
        ori_coords_became_aux_coords = [coord for coord in regridded_ds.coords
                                        if coord in target_coords and coord not in regridded_ds.dims]
        regridded_ds = regridded_ds.reset_coords(ori_coords_became_aux_coords, drop=True)
    return regridded_ds

def regrid_lon_lat(dataset, target_resol_ds=None, longitude=None, latitude=None, method='mean', tolerance=None,
                    longitude_circular=None, skipna=None, keep_attrs=False, **agg_method_kwargs):
    ds = dataset
    # Target data
    lon, lat = "longitude", "latitude"
    longitude = target_resol_ds[lon]
    latitude = target_resol_ds[lat]
    # Source data / pixel area
    lon_label, lat_label = "lon", "lat"
    ds_lon = ds[lon_label]
    ds_lon_span = abs(ds_lon[-1] - ds_lon[0])
    # check if longitude is circular
    if longitude_circular is None and len(longitude) >= 2:
        eps = np.finfo(ds_lon.dtype).eps
        ds_lon_delta = abs(ds_lon[1] - ds_lon[0])
        longitude_circular = bool(abs(ds_lon_span - 360.) <= 8. * 360. * eps or
                                    abs(ds_lon_span + ds_lon_delta - 360.) <= 8. * 360. * eps)
    # handle overlapping target longitude coordinates if necessary
    longitude_ori = None
    if longitude_circular:
        # remove target longitude coordinate which is overlapping mod 360
        eps = np.finfo(longitude.dtype).eps
        if abs(abs(longitude[-1] - longitude[0]) - 360.) <= 8. * 360. * eps:
            longitude_ori = longitude
            longitude = longitude[:-1]
        # remove ds' longitude coordinate which is overlapping mod 360
        eps = np.finfo(ds_lon.dtype).eps
        if abs(ds_lon_span - 360.) <= 8. * 360. * eps:
            ds = ds.isel({lon_label: slice(None, -1)})
    smallest_longitude_coord = (np.amin(np.asanyarray(longitude)) + np.amax(np.asanyarray(longitude)) - 360.) / 2
    ds = normalize_longitude(ds, lon_label=lon_label, smallest_lon_coord=smallest_longitude_coord, keep_attrs=True)
    ds_lon = ds[lon_label]
    if method in ['linear', 'nearest'] and longitude_circular:
        lon_coord = ds_lon.values
        extended_lon_coord = np.concatenate(([lon_coord[-1]], lon_coord, [lon_coord[0]]))
        extended_lon_coord_normalized = np.array(extended_lon_coord)
        extended_lon_coord_normalized[0] = extended_lon_coord_normalized[0] - 360.
        extended_lon_coord_normalized[-1] = extended_lon_coord_normalized[-1] + 360.
        lon_attrs = ds_lon.attrs
        ds = ds\
            .sel({lon_label: extended_lon_coord})\
            .assign_coords({lon_label: extended_lon_coord_normalized})
        ds[lon_label].attrs = lon_attrs
    ds = regrid(ds, {lon_label: longitude, lat_label: latitude}, method=method, tolerance=tolerance,
                            skipna=skipna, keep_attrs=keep_attrs, keep_ori_coords=False, **agg_method_kwargs)
    if longitude_circular and longitude_ori is not None:
        lon_idx = np.arange(len(longitude_ori))
        lon_idx[-1] = 0
        ds = ds.isel({lon_label: lon_idx}).assign_coords({lon_label: longitude_ori})
    return ds

def _rt_transform_by_air_density(dataset):
    vertical_profile_of_air_density = get_air_vertical_profile()
    mean_height = 0.5 * (dataset["RELZZ1"] + dataset["RELZZ2"])
    density = vertical_profile_of_air_density.interp(coords={'height': mean_height + dataset["ORO"]}).astype(np.float32)
    dataset["spec001_mr"] = dataset["spec001_mr"] * density
    dataset["spec001_mr"].attrs['units'] = 's.m-3'
    return dataset

def open_dataset(dataset_filepath: str):
    ds = xr.open_dataset(dataset_filepath)
    ds_area = xr.open_dataset(PIXEL_AREA_URL)
    ds_new = regrid_lon_lat(ds_area, target_resol_ds=ds, method="sum", longitude_circular=True)
    ds = ds.assign_coords(area=ds_new["Pixel_area"])
    values = _rt_transform_by_air_density(ds)
    sim_end = np.datetime64(pd.Timestamp(ds.attrs['iedate'] + 'T' + ds.attrs['ietime']))
    rel_time_start = (sim_end + ds.RELSTART)
    values = values.assign_coords({'release_time': ('pointspec', rel_time_start.data,
                                    {'long_name': 'release time',
                                    'description': 'time coordinate of the center of a release box'})})
    return values

def get_footprint_data(flexpart_output: str) -> xr.Dataset :
    """
    This function computes footprint image from the FLEXPART output

    Args:
        flexpart_output (str): path to the FLEXPART output netCDF file

    Returns:
        xr.Dataset: computed footprint in the xarray.Dataset format
    """
    with open_dataset(flexpart_output) as _ds:
        da = _ds['spec001_mr']
        t = _ds['release_time'][0].dt.round("h").values.astype('M8[ns]')
        station_code = station_short_name
        res_time = da.sum('height').squeeze('nageclass').mean('pointspec')
        res_time_norm = res_time
        res_time_per_km2 = res_time_norm.sum('time') / res_time_norm['area'] * 1e6
        res_time_per_km2 = res_time_per_km2.reset_coords(drop=True).astype('f2')
        res_time_per_km2 = res_time_per_km2.compute()
        alt = _ds.RELZZ1.values[0]
        output = xr.Dataset(
            data_vars={'res_time_per_km2': res_time_per_km2},
            coords={'time': t, 'station_id': station_code, 'height': alt}
        )
        output = output.expand_dims(['time', 'station_id', 'height']).set_coords(['time', 'station_id', 'height'])
    return output

def create_footprints(flexpart_output: str, output_file_with_footprints: str, station_short_name: str) -> None:
    """
    This function merges the new footprint with the bigger footprints database of
    other simulations

    Args:
        flexpart_output             (str): path to the FLEXPART output netCDF file
        output_file_with_footprints (str): path to the zarr merged database with footprints
    """
    logger.info(f"Creating footprint from file {flexpart_output}")
    ds = get_footprint_data(flexpart_output, station_short_name)
    if os.path.exists(output_file_with_footprints):
        with xr.open_zarr(output_file_with_footprints) as zarr_ds:
            output = xr.merge([zarr_ds, ds])
    else:
        output = ds
    encoding = {}
    for v in list(output.coords) + list(output.data_vars):
        v_dims = list(output[v].dims)
        _chunks = dict(zip(v_dims, (-1,) * len(v_dims)))
        _chunks['time'] = IDX_CHUNK if v == 'res_time_per_km2' else IDX_CHUNK_FOR_COORDS
        encoding[v] = {'chunks': tuple(_chunks.values())}
    with output.to_zarr(store=output_file_with_footprints, mode='w', encoding=encoding) as _store:
        pass

if __name__ == '__main__':
    """
    Main function

    Args:
        -f / --file   : path to the FLEXPART output netCDF file
        -n / --name   : short name of the ACTRIS station (same as in the JSON configuration file)
        -o / --output : path to the zarr merged database with footprints
    """

    import argparse
    
    parser = argparse.ArgumentParser(description="Computing footprint integrated image from the FLEXPART output",
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-f", "--file", type=str, help="Path to the FLEXPART output netCDF file")
    parser.add_argument("-n", "--name", type=str, help="Short name of the ACTRIS station in question")
    parser.add_argument("-o", "--output", type=str, help="Path to the zarr merged database with footprints")
    args = parser.parse_args()

    logger.info(f"Processing {args.file}")
    create_footprints(args.file, args.output, args.name)
