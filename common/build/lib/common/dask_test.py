import numpy as np

from .log import logger

logger().warning('started to generate x...')

N = 1000
x = np.random.normal(size=(N, N))

logger().warning(f'finished to generate x; x[0, 0] = {x[0, 0]}')
