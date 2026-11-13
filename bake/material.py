"""Offline material fields and procedurally authored, periodic detail textures."""
from pathlib import Path
import subprocess
import tempfile

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, laplace, map_coordinates
from scipy.spatial import cKDTree
from bake.tooling import ktx_tool

SUN_DIRECTION = (0.6,0.45,0.55)


def material_fields(heights, spacing, sun=SUN_DIRECTION, landform=None):
    # Primary materials follow broad source landforms, independent of added clods.
    source = heights if landform is None else landform
    smooth = gaussian_filter(source, max(1,200/spacing))
    dy, dx = np.gradient(smooth, spacing)
    slope = np.hypot(dx, dy)
    up = 1/np.sqrt(1+slope*slope)
    curvature = laplace(smooth)/(spacing*spacing)
    # glTF/PlayCanvas normal is (-dH/dEast, 1, -dH/dSouth).
    sx,sy,sz = np.asarray(sun)/np.linalg.norm(sun)
    aspect = (-dx*sx+sy-dy*sz)*up
    crust = np.clip(.92-curvature*9-slope*1.6+aspect*.10, 0, 1)
    dust = np.clip(.15+.6*up**4, 0, 1)
    # Local horizon approximation, baked once in the global frame.
    occlusion = np.exp(-np.maximum(gaussian_filter(heights, 6)-heights, 0)*.025)
    return np.stack([crust, np.full_like(crust, .5), dust, occlusion], axis=-1)


def detail_textures(size=512):
    rng = np.random.default_rng(4271)
    noise = rng.random((size, size)).astype('float32')
    coarse = gaussian_filter(noise, max(size/70, .5), mode='wrap')
    coarse = (coarse-coarse.min())/(np.ptp(coarse)+1e-6)
    grain = gaussian_filter(noise, .6, mode='wrap')
    # Packed irregular clasts with dark joints, rather than smooth noise alone.
    # Periodic nearest-neighbour distances keep the authored gravel tile seamless.
    cells = max(3,size//12)
    sy,sx = np.mgrid[0:cells,0:cells]
    sites = np.column_stack([sx.ravel(),sy.ravel()])
    sites = rng.uniform(0,size,sites.shape)
    yy,xx = np.mgrid[0:size,0:size]
    distance,nearest = cKDTree(sites,boxsize=size).query(np.column_stack([xx.ravel(),yy.ravel()]),k=2)
    dome = np.maximum(1-(distance[:,0]/np.maximum(distance[:,1],1e-5))**1.8,0)**.65
    variation = rng.uniform(.7,1,len(sites))[nearest[:,0]]
    gravel = gaussian_filter((dome*variation).reshape(size,size),.6,mode='wrap')
    granular = .75*gravel+.18*coarse+.07*grain
    crust = gaussian_filter(noise, max(size/35, 1), mode='wrap')
    crust = (crust-crust.min())/(np.ptp(crust)+1e-6)
    result = {}
    for name, height, strength in [('crust', crust, 2), ('granular', granular, 10)]:
        variation = np.clip(.5+.5*height if name=='granular' else .85+.15*height, 0, 1)
        result[name+'-albedo'] = (np.repeat(variation[:, :, None], 3, axis=-1)*255).astype('uint8')
        dx = (np.roll(height, -1, 1)-np.roll(height, 1, 1))*strength
        dy = (np.roll(height, -1, 0)-np.roll(height, 1, 0))*strength
        normal = np.stack([-dx, -dy, np.ones_like(dx)], axis=-1)
        normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
        result[name+'-normal'] = np.round((normal*.5+.5)*255).astype('uint8')
    # Pack sparse miniature marks beside the albedo variation. They never become objects.
    atlas = result['crust-albedo']
    atlas[:,:,1:] = 0
    for _ in range(max(1, size*size//22000)):
        cy, cx = rng.integers(0,size,2)
        for dy,dx in [(0,0),(0,1),(1,0),(-1,0),(0,-1)]:
            atlas[(cy+dy)%size,(cx+dx)%size,1] = 210 if dx==dy==0 else 100
    for _ in range(max(1, size*size//80000)):
        cy, cx = rng.integers(0,size,2)
        for step in range(max(3,size//45)):
            atlas[(cy+step//3)%size,(cx+step)%size,2] = 180
    return result


def encode_ktx(pixels, path):
    executable,_ = ktx_tool()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        png = Path(directory)/'input.png'
        Image.fromarray(pixels).save(png)
        subprocess.run([executable, '--t2', '--encode', 'uastc', '--uastc_quality', '1',
                        '--zcmp', '9', '--genmipmap', '--assign_oetf', 'linear',
                        '--threads', '2', str(path), str(png)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def sample_fields(fields, positions, size):
    col = (positions[:, 0]/size+.5)*(fields.shape[1]-1)
    row = (.5+positions[:, 2]/size)*(fields.shape[0]-1)
    return np.stack([map_coordinates(fields[:, :, i], [row, col], order=1, mode='nearest')
                     for i in range(4)], axis=-1)


def write_mask(fields, bounds, size, path, resolution=256, shore_distance=None):
    west, south, east, north = bounds
    # One half-texel halo: shader UV maps exact tile boundaries to texel centres.
    xs = np.linspace(west, east, resolution)
    zs = -np.linspace(north, south, resolution)
    xx, zz = np.meshgrid(xs, zs)
    positions = np.column_stack([xx.ravel(), np.zeros(xx.size), zz.ravel()])
    pixels = np.clip(sample_fields(fields, positions, size).reshape(resolution, resolution, 4)*255, 0, 255).astype('uint8')
    if shore_distance is not None:
        row = (.5+positions[:,2]/size)*(shore_distance.shape[0]-1)
        col = (.5+positions[:,0]/size)*(shore_distance.shape[1]-1)
        pixels[:,:,3] = np.clip(map_coordinates(shore_distance, [row,col], order=1,
                                    mode='nearest').reshape(resolution,resolution)*255, 0, 255).astype('uint8')
    encode_ktx(pixels, path)
