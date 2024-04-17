import numpy as np
import pytest

from pyaerocom.griddeddata import GriddedData
from pyaerocom.vert_coords import *
from tests.fixtures.tm5 import data_tm5


@pytest.fixture
def alt(data_tm5: GriddedData):
    return AltitudeAccess(data_tm5)


@pytest.fixture
def sin_wave():
    return np.sin(np.arange(1000))


def test_atmosphere_sigma_coordinate_to_pressure(sin_wave):
    assert isinstance(atmosphere_sigma_coordinate_to_pressure(0.5, 1, 1), float)

    result = atmosphere_sigma_coordinate_to_pressure(sin_wave, 1, 1)
    assert isinstance(result, np.ndarray)

    assert len(result) == len(sin_wave)


def test_atmosphere_hybrid_sigma_pressure_coordinate_to_pressure(sin_wave):
    with pytest.raises(ValueError):
        atmosphere_hybrid_sigma_pressure_coordinate_to_pressure(np.ones(5), np.ones(4), 1, 1)

    result = atmosphere_hybrid_sigma_pressure_coordinate_to_pressure(sin_wave, sin_wave, 1, 1)
    assert len(result) == len(sin_wave)


def test_geopotentialheight2altitude():
    with pytest.raises(NotImplementedError):
        geopotentialheight2altitude(5)


def test_pressure2altitude():
    result = pressure2altitude(7)

    assert isinstance(result, float)


@pytest.mark.parametrize(
    "name,expected",
    (
        ("altitude", True),
        ("air_pressure", True),
        ("model_level_number", True),
        ("hfjlkfhldsa", False),
    ),
)
def test_is_supported(name: str, expected: bool):
    assert is_supported(name) == expected


def test_VerticalCoordinate_exceptions():
    # Unsupported variable name during initialization.
    with pytest.raises(ValueError):
        VerticalCoordinate("jtlkjhsklrg")

    # Attempt calculating pressure for unsupported variable.
    vert = VerticalCoordinate("asc")
    with pytest.raises(CoordinateNameError):
        vert.calc_pressure(np.ones(5))


def test_AltitudeAccess_exceptions():
    with pytest.raises(ValueError):
        AltitudeAccess(None)


def test_AltitudeAccess(alt: AltitudeAccess):
    assert True
