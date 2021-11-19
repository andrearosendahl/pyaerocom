import numpy as np
import pandas as pd
import pytest
import xarray as xr
from iris.cube import Cube

from pyaerocom import GriddedData, TsType
from pyaerocom.helpers import resample_time_dataarray, resample_timeseries
from pyaerocom.time_resampler import TimeResampler

# get default resampling "min_num_obs"
min_num_obs_default = {
    "yearly": {"monthly": 3},
    "monthly": {"daily": 7},
    "daily": {"hourly": 6},
    "hourly": {"minutely": 15},
}

# get stricter constraints (from Hans issue)
min_num_obs_custom = {
    "yearly": {"monthly": 9},
    "monthly": {"weekly": 3},
    "weekly": {"daily": 5},
    "daily": {"hourly": 18},
    "hourly": {"minutely": 45},
}


@pytest.fixture(scope="module")
def fakedata_hourly():
    idx = pd.date_range(start="1-1-2010 00:00:00", end="1-13-2010 23:59:59", freq="h")

    data = np.sin(range(len(idx)))
    data[44:65] = np.nan
    return pd.Series(data, idx)


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(np.asarray([1]), id="np.array"),
        pytest.param(GriddedData(), id="GriddedData"),
        pytest.param(Cube([]), id="Cube"),
    ],
)
def test_TimeResampler_invalid_input_data(data):
    tr = TimeResampler()
    with pytest.raises(ValueError) as e:
        tr.input_data = data
    assert str(e.value) == "Invalid input: need Series or DataArray"


@pytest.mark.parametrize(
    "data,resampler_function",
    [
        pytest.param(pd.Series(dtype=np.float64), resample_timeseries, id="pd.Series"),
        pytest.param(xr.DataArray(), resample_time_dataarray, id="xr.DataArray"),
    ],
)
def test_TimeResampler_fun(data, resampler_function):
    tr = TimeResampler()
    tr.input_data = data
    assert tr.fun == resampler_function


@pytest.mark.parametrize(
    "from_ts_type,to_ts_type,min_num_obs,how,expected",
    [
        (
            TsType("3hourly"),
            TsType("monthly"),
            min_num_obs_default,
            dict(monthly={"daily": "max"}),
            [("daily", 2, "mean"), ("monthly", 7, "max")],
        ),
        (
            TsType("84hourly"),
            TsType("6daily"),
            {"daily": {"minutely": 12}},
            "median",
            [("6daily", 0, "median")],
        ),
        (
            TsType("84hourly"),
            TsType("6daily"),
            {"daily": {"hourly": 12}},
            "median",
            [("6daily", 1, "median")],
        ),
        (TsType("hourly"), TsType("daily"), 3, "median", [("daily", 3, "median")]),
        (TsType("3hourly"), TsType("monthly"), 3, "mean", [("monthly", 3, "mean")]),
        (
            TsType("3hourly"),
            TsType("monthly"),
            min_num_obs_default,
            "mean",
            [("daily", 2, "mean"), ("monthly", 7, "mean")],
        ),
        (TsType("2daily"), TsType("weekly"), min_num_obs_custom, "max", [("weekly", 2, "max")]),
    ],
)
def test_TimeResampler__gen_index(from_ts_type, to_ts_type, min_num_obs, how, expected):
    val = TimeResampler()._gen_idx(from_ts_type, to_ts_type, min_num_obs, how)
    assert val == expected


@pytest.mark.parametrize(
    "args,output_len,output_numnotnan,lup",
    [
        (
            dict(
                to_ts_type="monthly",
                from_ts_type="hourly",
                how=dict(monthly=dict(daily="sum"), daily=dict(hourly="max")),
                min_num_obs=dict(monthly=dict(daily=15), daily=dict(hourly=1)),
            ),
            1,
            0,
            False,
        ),
        (dict(to_ts_type="monthly", from_ts_type="hourly"), 1, 1, True),
        (
            dict(
                to_ts_type="monthly",
                from_ts_type="hourly",
                how=dict(daily=dict(hourly="sum")),
                min_num_obs=min_num_obs_custom,
            ),
            1,
            0,
            False,
        ),
        (dict(to_ts_type="monthly", from_ts_type="hourly", how="median"), 1, 1, True),
        (dict(to_ts_type="daily", from_ts_type="hourly", how="median"), 13, 13, True),
        (dict(to_ts_type="daily", from_ts_type="hourly", how="median"), 13, 13, True),
        (
            dict(
                to_ts_type="daily",
                from_ts_type="hourly",
                how="median",
                min_num_obs=min_num_obs_default,
            ),
            13,
            13,
            True,
        ),
        (
            dict(
                to_ts_type="daily",
                from_ts_type="hourly",
                how="median",
                min_num_obs=min_num_obs_custom,
            ),
            13,
            12,
            True,
        ),
        (
            dict(
                to_ts_type="monthly",
                from_ts_type="hourly",
                how="median",
                min_num_obs=min_num_obs_default,
            ),
            1,
            1,
            True,
        ),
        (
            dict(
                to_ts_type="monthly",
                from_ts_type="hourly",
                how="median",
                min_num_obs=min_num_obs_custom,
            ),
            1,
            0,
            True,
        ),
    ],
)
def test_TimeResampler_resample(fakedata_hourly, args, output_len, output_numnotnan, lup):
    tr = TimeResampler(input_data=fakedata_hourly)
    ts = tr.resample(**args)
    assert len(ts) == output_len
    notnan = ~np.isnan(ts)
    assert notnan.sum() == output_numnotnan
    assert tr.last_units_preserved == lup
