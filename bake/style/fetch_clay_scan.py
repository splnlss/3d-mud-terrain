"""Fetch pinned CC0 Poly Haven source maps for the clay calibration study."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request

ASSET='brown_mud_03'
MAPS={
 'base-color':('diff','17715ddf1687eb647dc7e539c2aa10d4'),
 'height':('disp','ef05a5db35177d86b6579d51d67a485f'),
 'roughness':('rough','aedd830eae260a6a7fd1c4c9a53dae24'),
 'normal':('nor_gl','1a8a551a6244ce20491aa0f32b1a1023'),
}


def fetch(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    def download(item):
        key,(suffix,expected)=item;path=output/f'{key}.png'
        url=f'https://dl.polyhaven.org/file/ph-assets/Textures/png/2k/{ASSET}/{ASSET}_{suffix}_2k.png'
        if not path.exists():
            with urllib.request.urlopen(url) as response:path.write_bytes(response.read())
        if hashlib.md5(path.read_bytes()).hexdigest()!=expected:
            raise ValueError(f'Source checksum mismatch: {key}')
        return key,{'url':url,'md5':expected,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    with ThreadPoolExecutor(max_workers=4) as pool:files=dict(pool.map(download,MAPS.items()))
    manifest={'source':f'https://polyhaven.com/a/{ASSET}','author':'Rob Tuytel','license':'CC0',
        'license_url':'https://polyhaven.com/license','source_span_m':1.3,'files':files,
        'use':'Surface-detail calibration; source photos remain art-direction authority.'}
    (output/'provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    fetch(parser.parse_args().output)
