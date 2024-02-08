import fpout
import sys
import xarray as xr
import os
import glob
import argparse
import logging
from common import log, utils
from common.log import logger
import pandas as pd
import datetime as dt

IDX_CHUNK = 160
IDX_CHUNK_FOR_COORDS = IDX_CHUNK * 40

STATIONS_CODE = {"PicDuMidi":"PDM",
                 "PuyDeDome":"PUY",
                 "SIRTA":"SAC",
                 "ObservatoirePerenne":"OPE",
                 "Maido":"RUN",
                 "Lamto":"LTO"}

def get_footprint_data(flexpart_output: str) -> xr.Dataset :
    """
    This function computes footprint image from the FLEXPART output

    Args:
        flexpart_output (str): path to the FLEXPART output netCDF file

    Returns:
        xr.Dataset: computed footprint in the xarray.Dataset format
    """
    with fpout.open_dataset(flexpart_output, max_chunk_size=1e8) as _ds:
        da = _ds['res_time']
        t = _ds['release_time'][0].dt.round("H").values.astype('M8[ns]')
        station_code = STATIONS_CODE[os.path.basename(flexpart_output).split("-")[0]]
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

def create_footprints(flexpart_output: str, output_file_with_footprints: str) -> None:
    """
    This function merges the new footprint with the bigger footprints database of
    other simulations

    Args:
        flexpart_output             (str): path to the FLEXPART output netCDF file
        output_file_with_footprints (str): path to the zarr merged database with footprints
    """
    logger().info(f"Creating footprint from file {flexpart_output}")
    ds = get_footprint_data(flexpart_output)
    if os.path.exists(output_file_with_footprints):
        with xr.open_zarr(output_file_with_footprints) as zarr_ds:
            output = xr.merge([zarr_ds, ds])
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
        -o / --output : path to the zarr merged database with footprints
    """

    import argparse
    
    parser = argparse.ArgumentParser(description="Computing footprint integrated image from the FLEXPART output",
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-f", "--file", type=str, help="Path to the FLEXPART output netCDF file")
    parser.add_argument("-o", "--output", type=str, help="Path to the zarr merged database with footprints")
    args = parser.parse_args()

    # log.start_logging(args.logfile, logging_level=logging.INFO)

    create_footprints(args.file, args.output)
    
