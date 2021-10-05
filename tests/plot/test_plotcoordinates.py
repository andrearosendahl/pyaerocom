import pytest
import cartopy
import numpy as np

import pyaerocom.plot.plotcoordinates as mod


@pytest.mark.parametrize('args', [
    dict(), dict(legend=False), dict(label='bla'), dict(marker='^'),
    dict(ylim=(-50, -10)),dict(xlim=(-50, 50)), dict(fix_aspect=True),
    dict(title='Blaaaaa'), dict(gridlines=True)
])
def test_plot_coordinates(args):
    lats = np.arange(10)
    lons = np.arange(10)
    val = mod.plot_coordinates(lons=lons, lats=lats, **args)
    assert isinstance(val, cartopy.mpl.geoaxes.GeoAxes)
