import math
import numpy as np
import pandas as pd
import xarray as xr
import sys
from . import utils


_eps = 10. * sys.float_info.epsilon


def midpoint(u, v, p=0.5):
    """
    :return: (1-p)*u + p*v
    """
    return u + p * (v - u)


def linear_interpolation(x0, xys):
    (x1, y1), (x2, y2) = xys
    if isinstance(x0, pd.Timestamp):
        x0, x1, x2 = x0.timestamp(), x1.timestamp(), x2.timestamp()
    dist_x0_x1 = abs(x1 - x0)
    dist_x0_x2 = abs(x2 - x0)
    dist = dist_x0_x1 + dist_x0_x2
    assert math.isclose(dist, abs(x2 - x1)), (x0, x1, x2)
    p = dist_x0_x1 / dist if dist > _eps else .5
    return midpoint(y1, y2, p)


def resample_by_linear_interpolation2(data, new_index):
    """
    Resample a pandas Series or DataFrame to a new index using linear interpolation.
    In case the new index falls outside a range of the data's original index, then constant extrapolation is applied.

    :param data: pandas Series or DataFrame
    :param new_index: an Iterable (e.g. pandas Index)
    :return: pandas Series or DataFrame
    """

    # FIXME: in case fp is a time series with a long block of NaN, the missing data should not be just interpolated but left as NaN
    new_index = pd.Index(new_index)
    return data\
        .reindex(index=new_index.union(data.index))\
        .interpolate(method='index', limit_direction='both')\
        .reindex(index=new_index)


def resample_by_linear_interpolation(data, new_index):
    """
    Resample a pandas Series or DataFrame to a new index using linear interpolation.
    In case the new index falls outside a range of the data's original index, then constant extrapolation is applied.

    :param data: pandas Series or DataFrame
    :param new_index: an Iterable (e.g. pandas Index)
    :return: pandas Series or DataFrame
    """

    # FIXME: in case fp is a time series with a long block of NaN, the missing data should not be just interpolated but left as NaN
    ds = xr.Dataset(data)
    return ds.interp(coords=dict(t=new_index), method='linear', assume_sorted=True, kwargs=dict(fill_value='extrapolate'))


def linear_interpolation2(x0, xys):
    # TODO: deprecated (remove)
    (x1, y1), (x2, y2) = xys
    dist_x0_x1 = abs(x1 - x0)
    dist_x0_x2 = abs(x2 - x0)
    dist = dist_x0_x1 + dist_x0_x2
    #FIXME: there is a problem when dist is a pandas.Timedelta object
    p = dist_x0_x1 / dist #if dist > _eps else .5
    return midpoint(y1, y2, p)


class InterpolationNode:
    # TODO: deprecated (remove)
    def __init__(self, label, value=math.nan, parent=None):
        self._label = label
        self._value = value
        self._children = []
        self._parent = parent
        if self._parent is not None:
            self._parent._add_child(self)

    def _add_child(self, child):
        self._children.append(child)

    def interpolate(self, labels):
        if len(labels) > 0:
            label, *remaining_labels = labels
            labels_values = [(child._label, child.interpolate(remaining_labels)) for child in self._children]
            if len(labels_values) == 2:
                return linear_interpolation(label, labels_values)
            elif len(labels_values) == 1:
                _, value = labels_values[0]
                return value
            else:
                raise ValueError(f'cannot interpolate from {len(labels_values)} values')
        else:
            return self._value
