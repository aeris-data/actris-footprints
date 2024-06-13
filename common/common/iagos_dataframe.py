import pandas as pd
from . import utils

_IAGOS_MEASUREMENT_INSTRUMENT_CODES = {'P1', 'P2b', 'PC2', 'PC1', 'PM'}


class IagosDataFrame(pd.DataFrame):
    def __init__(self, df):
        super().__init__(df)

    def get_iagos_measurement(self, measurement):
        keys = {measurement + '_' + suffix for suffix in _IAGOS_MEASUREMENT_INSTRUMENT_CODES} & set(self)
        try:
            key = utils.unique(keys)
        except ValueError:
            raise KeyError(f'{measurement}: keys={keys}')
        return self[key]

    def get_iagos_measurement_or_default(self, measurement, default=None):
        try:
            return self.get_iagos_measurement(measurement)
        except KeyError:
            return default
