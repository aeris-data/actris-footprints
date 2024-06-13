import numpy as np
import xarray as xr
import pandas as pd
import logging
import os
import sys

# sys.path.append('/usr/local/footprints/')

import fpout

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - [%(levelname)s] %(message)s',
                    datefmt='%d/%m/%Y %H:%M:%S')
logger = logging.getLogger(__name__)

IDX_CHUNK = 160
IDX_CHUNK_FOR_COORDS = IDX_CHUNK * 40

def get_footprint_data(flexpart_output: str, station_short_name: str) -> xr.Dataset :
    """
    This function computes footprint image from the FLEXPART output

    Args:
        flexpart_output (str): path to the FLEXPART output netCDF file

    Returns:
        xr.Dataset: computed footprint in the xarray.Dataset format
    """
    with fpout.open_dataset(flexpart_output, max_chunk_size=1e8) as _ds:
        da = _ds['spec001_mr']
        t = _ds['release_time'][0].dt.round("h").values.astype('M8[ns]')
        station_code = station_short_name
        res_time = da.sum('height').squeeze(['nageclass']).mean('pointspec')
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