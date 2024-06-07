import numpy as np
import pandas as pd
import xarray as xr
import softio
import fpsim
import sys
import glob
import os
import logging
import json

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - [%(levelname)s] %(message)s',
                    datefmt='%d/%m/%Y %H:%M:%S')
logger = logging.getLogger(__name__)

def apply_softio(flexpart_output: str, softio_output_dir: str, station_short_name: str) -> str:
    """
    This function apply SOFT-IO to the given FLEXPART output.

    Args:
        flexpart_output   (str) : path to the FLEXPART output netCDF file
        softio_output_dir (str) : path to the directory where to store the output SOFT-IO file

    Returns:
        str: string of the filepath to the soft-io output netcdf file
    """
    filename = os.path.basename(flexpart_output)
    station = filename.split("-")[0]
    date    = filename.split("-")[1]
    softio_output_file = f"{softio_output_dir}/softio-{filename}"
    logger.info(f"Processing station {station} for the date {date}")
    if not os.path.exists(softio_output_file):
        try:
            fp_ds = fpsim.open_fp_dataset(flexpart_output)
            alt   = fp_ds.RELZZ1.values[0]
            ds_res = xr.Dataset()

            logger.info("Calculating GFAS inventory")
            gfas_ds = softio.get_co_contrib(emission_inventory="gfas", fpsim_ds=fp_ds, time_granularity='3h')
            gfas_ds = gfas_ds.sum('time').squeeze()
            gfas_ds = gfas_ds.assign_coords({"height":alt,
                                            "station_id": station_short_name}).expand_dims(["height",
                                                                                "station_id",
                                                                                "release_time"]).set_coords(["height",
                                                                                                    "station_id",
                                                                                                    "release_time"])

            logger.info("Calculating CEDS2 inventory")
            ceds_ds = softio.get_co_contrib(emission_inventory="ceds2", fpsim_ds=fp_ds, time_granularity='3h')
            ceds_ds = ceds_ds.sum('time').squeeze()
            ceds_ds = ceds_ds.assign_coords({"height":alt,
                                            "station_id": station_short_name}).expand_dims(["height",
                                                                                "station_id",
                                                                                "release_time"]).set_coords(["height",
                                                                                                    "station_id",
                                                                                                    "release_time"])

            ds_res = xr.concat([gfas_ds, ceds_ds], dim=pd.Index(['GFAS', 'CEDS'], name='em_inv'))
            
            ds_res.to_netcdf(softio_output_file)
            return softio_output_file
        except Exception as e:
            logger.error(e)
            return ""
    else:
        return softio_output_file

def add_to_database(softio_file: str, softio_database: str) -> int:
    """
    This function append/insert a SOFT-IO netCDF result to a bigger netCDF ("database") file,
    where multiple different SOFT-IO results are merged.

    Args:
        softio_file     (str) : path to the SOFT-IO output netCDF file
        softio_database (str) : path to the database file

    Returns:
        int: 0 if successful, 1 if error has occured
    """
    if os.path.exists(softio_database):
        try:
            ds_in = xr.open_dataset(softio_file).drop_vars(["release_lon","release_lat","release_pressure","release_npart"])
            ds_out = xr.open_dataset(softio_database)
            ds = xr.merge([ds_in, ds_out])
            ds_in.close()
            ds_out.close()
            ds.to_netcdf(softio_database)
            return 0
        except Exception as e:
            logger.error(e)
            return 1
    else:
        try:
            ds_in = xr.open_dataset(softio_file).drop_vars(["release_lon","release_lat","release_pressure","release_npart"])
            ds_in.to_netcdf(softio_database)
            return 0
        except Exception as e:
            logger.error(e)
            return 1

if __name__=="__main__":
    """
    Main function

    Args:
        -f / --file   : path to the FLEXPART output netCDF file
        -n / --name   : short name of the ACTRIS station (same as in the JSON configuration file)
        -d / --dir    : path to the directory where to store the output SOFT-IO file
        -o / --output : path to the SOFT-IO merged database file where to add new data
    """

    import argparse
    
    parser = argparse.ArgumentParser(description="Applying SOFT-IO to the FLEXPART output for the ACTRIS stations",
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-f", "--file", type=str, help="Path to the FLEXPART output netCDF file")
    parser.add_argument("-n", "--name", type=str, help="Short name of the ACTRIS station in question")
    parser.add_argument("-d", "--dir", type=str, help="Path to the directory where to store the output SOFT-IO file")
    parser.add_argument("-o", "--output", type=str, help="Path to the SOFT-IO merged database file where to add new data")
    args = parser.parse_args()

    logger.info("Calling SOFT-io")
    softio_file = apply_softio(args.file, args.dir, args.name)
    if args.output is not None:
        logger.info("Adding to the database")
        status_code = add_to_database(softio_file, args.output)