import re
import pathlib
import logging
import dask.distributed
from .log import logger
from . import log


def start_dask_logging(dask_client, log_dir=None, logfile_url=None, logging_level=logging.WARNING):
    def worker_setup(dask_worker):
        _start_logging_on_worker(dask_worker=dask_worker, logfile_url=logfile_url, log_dir=log_dir, logging_level=logging_level)

    if not log_dir and not logfile_url:
        raise ValueError('either logfile_url or log_dir must be specify')
    dask_client.register_worker_callbacks(worker_setup)


def _escape_filename(filename):
    return re.sub('[^\w\-_\. ]', '_', filename)


def _start_logging_on_worker(dask_worker=None, logfile_url=None, log_dir=None, logging_level=logging.WARNING):
    if not log_dir and not logfile_url:
        raise ValueError('either logfile_url or log_dir must be specify')

    if dask_worker is None:
        dask_worker = dask.distributed.get_worker()
    logger_name = f'worker_on_{dask_worker.address}'
    log._logger = logging.getLogger(logger_name)

    current_logging_level = logger().getEffectiveLevel()
    if not current_logging_level or current_logging_level > logging_level:
        logger().setLevel(logging_level)

    if not logfile_url:
        pathlib.Path(log_dir).mkdir(exist_ok=True)
        logfile_url = pathlib.PurePath(log_dir, _escape_filename(f'{logger_name}.log'))
    else:
        logfile_url = pathlib.PurePath(logfile_url)
    handler = logging.FileHandler(str(logfile_url))
    handler.setLevel(logging_level)
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - in %(module)s.%(funcName)s (line %(lineno)d): %(message)s')
    handler.setFormatter(formatter)
    logger().addHandler(handler)
    logger().log(logging.INFO, f'Dask logger {logger_name} started!')
