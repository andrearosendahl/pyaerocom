from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from xarray import open_dataarray

from pyaerocom import ColocatedData
from pyaerocom.access_testdata import AccessTestData
from pyaerocom.griddeddata import GriddedData

TESTDATADIR = AccessTestData().testdatadir

CHECK_PATHS = SimpleNamespace(
    tm5aod="modeldata/TM5-met2010_CTRL-TEST/renamed/aerocom3_TM5_AP3-CTRL2016_od550aer_Column_2010_monthly.nc",
    coldata_tm5_aeronet="coldata/od550aer_REF-AeronetSunV3L2Subset.daily_MOD-TM5_AP3-CTRL2016_20100101_20101231_monthly_WORLD-noMOUNTAINS.nc",
    tm5_tm5="coldata/od550aer_REF-TM5_AP3-CTRL2016_MOD-TM5_AP3-CTRL2016_20100101_20101231_monthly_WORLD-noMOUNTAINS.nc",
)


@pytest.fixture(scope="session")
def data_tm5():
    path = TESTDATADIR / CHECK_PATHS.tm5aod
    assert path.exists()
    data = GriddedData(path)
    return data


def load_coldata_tm5_aeronet_from_scratch(path: Path) -> ColocatedData:

    arr = open_dataarray(path)
    if "_min_num_obs" in arr.attrs:
        info = {}
        for val in arr.attrs["_min_num_obs"].split(";")[:-1]:
            to, fr, num = val.split(",")
            if not to in info:
                info[to] = {}
            if not fr in info[to]:
                info[to][fr] = {}
            info[to][fr] = int(num)
        arr.attrs["min_num_obs"] = info
    cd = ColocatedData()
    cd.data = arr
    return cd


@pytest.fixture(scope="session")
def coldata_tm5_aeronet() -> ColocatedData:
    path = TESTDATADIR / CHECK_PATHS.coldata_tm5_aeronet
    return load_coldata_tm5_aeronet_from_scratch(path)


@pytest.fixture(scope="session")
def coldata_tm5_tm5() -> ColocatedData:
    path = TESTDATADIR / CHECK_PATHS.tm5_tm5
    return load_coldata_tm5_aeronet_from_scratch(path)
