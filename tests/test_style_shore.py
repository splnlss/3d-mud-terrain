"""Shore support must create a bed and banks rather than floating water strips."""
import numpy as np


def test_channel_and_lake_banks_support_water_without_cut_shelves():
    from bake.style.shore import support_shore
    x,z=np.meshgrid(np.arange(-60,61,2),np.arange(-60,61,2))
    for inside in [abs(x)<12,x*x+z*z<24**2]:
        surface=np.full(x.shape,100.)
        ground=120+np.sin(x/30)*10+np.cos(z/30)*5
        shaped,band=support_shore(ground,surface,inside,2,30)
        assert np.max(shaped[inside])<=98
        assert np.min(shaped[(~inside)&(band>0)])>100
        assert np.isfinite(shaped).all()
        # There is no hard shelf at the outer edge of the blend band.
        outside=band==0
        np.testing.assert_allclose(shaped[outside],ground[outside])
