"""Offline relief shaping in a single global coordinate frame."""
import numpy as np
from scipy.ndimage import gaussian_filter


def remap_height(heights, base, gain=5, knee=800):
    if gain <= 0 or knee <= 0:
        raise ValueError('curve gain and knee must be positive')
    return base + gain*knee*np.log1p(np.maximum(heights-base, 0)/knee)


def clod_displacement(x, north, amplitude=25):
    # Smooth, bounded lobes, deterministic at the same world position at every LOD.
    def noise(px, py):
        ix, iy = np.floor(px).astype('int64'), np.floor(py).astype('int64')
        fx, fy = px-ix, py-iy
        fx, fy = fx*fx*(3-2*fx), fy*fy*(3-2*fy)
        def hash_value(dx, dy):
            h = ((ix+dx)*374761393 + (iy+dy)*668265263 + 4271) & 0xffffffff
            h = ((h ^ (h >> 13))*1274126177) & 0xffffffff
            return (h ^ (h >> 16))/4294967295*2-1
        a = hash_value(0, 0)*(1-fx)+hash_value(1, 0)*fx
        b = hash_value(0, 1)*(1-fx)+hash_value(1, 1)*fx
        return a*(1-fy)+b*fy
    return amplitude*(.6*noise(x/170, north/170)+.3*noise(x/480+31, north/480-19)
                      +.1*noise(x/53-17, north/53+41))


def shape_dem(heights, size, base, gain=5, knee=800, amplitude=25, edge_width=0, rounding_sigma=2):
    rounded = gaussian_filter(heights, sigma=rounding_sigma)
    if gain<=0 or knee<=0:
        raise ValueError('curve gain and knee must be positive')
    # In-place curve avoids several 500 MB temporaries for the full 10 m grid.
    result = rounded
    result -= base
    np.maximum(result, 0, out=result)
    result /= knee
    np.log1p(result, out=result)
    result *= gain*knee
    result += base
    x = np.linspace(-size/2, size/2, heights.shape[1], dtype='float32')[None, :]
    # Work in rows to avoid allocating several extra full-size source rasters.
    for start in range(0, len(heights), 128):
        end = min(start+128, len(heights))
        north = (size/2-np.arange(start, end, dtype='float32')*size/(len(heights)-1))[:, None]
        result[start:end] += clod_displacement(x, north, amplitude)
        if edge_width>0:
            distance = np.minimum(size/2-np.abs(x), size/2-np.abs(north))
            t = np.clip(distance/edge_width, 0, 1)
            blend = t*t*(3-2*t)
            result[start:end] = base+(result[start:end]-base)*blend
    return result
