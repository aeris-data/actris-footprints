import socket
import pathlib

homedir = str(pathlib.Path.home())

if 'aeropc' in socket.gethostname():
    ecmwf_data_path = '/home/wolp/data/ECMWF'
    iagos_data_path = '/home/wolp/data/iagosv2-netcdf-L2'
    iagos_data_path_L1 = '/home/wolp/data/iagosv2-netcdf-L1'
    flexpart_data_path = '/home/wolp/data/flexpart-V9.2'
    flexpart_output_data_path = '/home/wolp/data/pv_analysis'   # TODO: remove as deprecated
    iagos_ancillary_data_path = '/home/wolp/data/ancillary'
    log_path = '/home/wolp/logs'
    catalogues_path = '/home/wolp/catalogues'
    aux_path = '/home/wolp/data/tmp'
    flexpart_as_hdf_path = '/home/wolp/data/fp_as_hdf'
    flexpart_as_netcdf_path = '/home/wolp/data/fp_as_netcdf'
    softio_data_path = '/home/wolp/data/softio'
else:
    ecmwf_data_path = '/o3p/ECMWF/ENFILES'
    iagos_data_path = '/o3p/iagos/iagosv2/netcdf/L2'
    iagos_data_path_L1 = '/o3p/iagos/iagosv2/netcdf/L1'
    flexpart_data_path = '/o3p/iagos/flexpart/V9.2'
    flexpart_output_data_path = '/o3p/wolp/FP_BULK'     # TODO: remove as deprecated
    iagos_ancillary_data_path = '/o3p/wolp/ancillary'
    log_path = str(pathlib.PurePath(homedir, 'logs'))
    tmp_path = str(pathlib.PurePath(homedir, 'tmp'))
    pathlib.Path(tmp_path).mkdir(exist_ok=True)
    catalogues_path = '/o3p/wolp/catalogues'
    aux_path = '/home/wolp/data/tmp'
    flexpart_as_hdf_path = '/o3p/wolp/fp_as_hdf'
    flexpart_as_netcdf_path = '/o3p/wolp/fp_as_netcdf'
    softio_data_path = '/o3p/wolp/softio/V1.0.1'
