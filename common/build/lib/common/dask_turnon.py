import dask.distributed
import socket

from .log import logger
from .tempdir import get_tempdir


def dask_turnon(parallel_workers, **kwargs):
    # turn on Dask
    workdir = get_tempdir()
    cluster = dask.distributed.LocalCluster(
        n_workers=parallel_workers,
        local_directory=str(workdir),
        **kwargs
    )
    dask_client = dask.distributed.Client(cluster)
    logger().info('Parallel processing switched on.')
    try:
        hostname = socket.gethostname()
    except:
        hostname = 'unknown'
    logger().info(f'Host name: {hostname}')
    try:
        port = dask_client.scheduler_info()['services']['dashboard']
    except:
        port = 'unknown'
    logger().info(f'Dask dashboard port: {port}')
    logger().info(f'Dask client: {dask_client}')
    return dask_client
