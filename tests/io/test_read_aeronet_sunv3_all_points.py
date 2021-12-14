#!/usr/bin/env python3
"""
Created on Mon Jul  9 14:14:29 2018
"""
import os

import numpy as np
import numpy.testing as npt
import pytest

from pyaerocom.io.read_aeronet_sunv3 import ReadAeronetSunV3

from ..conftest import data_unavail


@data_unavail
@pytest.fixture(scope="module")
def reader():
    return ReadAeronetSunV3("AeronetSunV3L2Subset.AP")


@data_unavail
def test_get_file_list(reader):
    assert len(reader.get_file_list()) == 2


@data_unavail
def test_read_file(reader):
    from pyaerocom.stationdata import StationData

    file = reader.files[0]
    assert os.path.basename(file) == "19930101_20211120_Karlsruhe.lev20.gz"
    data = reader.read_file(file)
    assert isinstance(data, StationData)
    # assert data.latitude[0] == pytest.approx(49.09, 0.01)
    # assert data.longitude[0] ==  pytest.approx(8.42, 0.01)
    assert data.station_name[0] == "Karlsruhe"
    assert all(x in data for x in ["od550aer", "ang4487aer"])

    # actual = [data["od550aer"][:10].mean(), data["ang4487aer"][:10].mean()]
    # desired = [0.287, 1.787]
    # npt.assert_allclose(actual, desired, rtol=1e-3)


# @data_unavail
# def test_read(reader):
#     from pyaerocom.ungriddeddata import UngriddedData
#
#     files = reader.files[2:3]
#     assert all(os.path.basename(x) in ("Agoufou.lev30", "Alta_Floresta.lev30") for x in files)
#     data = reader.read(files=files)
#
#     assert isinstance(data, UngriddedData)
#     assert data.unique_station_names == ["Agoufou", "Alta_Floresta"]
#     assert data.contains_vars == ["od550aer", "ang4487aer"]
#     assert data.contains_instruments == ["sun_photometer"]
#     assert data.shape == (11990, 12)
#     npt.assert_allclose(np.nanmean(data._data[:, data._DATAINDEX]), 0.676, rtol=1e-3)


@data_unavail
def test_read_add_common_meta(reader):
    files = reader.files
    data = reader.read("od550aer", files=files, common_meta={"bla": 42})
    assert all("bla" in x for x in data.metadata.values())


if __name__ == "__main__":
    import sys

    pytest.main(sys.argv)
