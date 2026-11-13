"""Prepare pinned KTX tools locally, without a system-wide installation."""
import hashlib
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bake.tooling import download_verified,ktx_tool
KTX_VERSION = '4.4.2'
KTX_SHA256 = '500bd8f9d63358c3f3a0d83b724c8574436a72c37dc0e4bad90ec1ca38032c3c'
dest = ROOT/'data/tools/ktx'
if not (dest/'bin/toktx').exists() and not shutil.which('toktx'):
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise SystemExit('Install KTX-Software 4.4.2 (toktx) on PATH for this platform.')
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        package = temp/'ktx.pkg'
        download_verified(f'https://github.com/KhronosGroup/KTX-Software/releases/download/v{KTX_VERSION}/KTX-Software-{KTX_VERSION}-Darwin-arm64.pkg', package,KTX_SHA256)
        if hashlib.sha256(package.read_bytes()).hexdigest() != KTX_SHA256:
            raise SystemExit('KTX package checksum mismatch')
        subprocess.run(['pkgutil', '--expand-full', str(package), str(temp/'expanded')], check=True)
        (dest/'bin').mkdir(parents=True, exist_ok=True)
        (dest/'lib').mkdir(parents=True, exist_ok=True)
        prefix = temp/'expanded'/f'KTX-Software-{KTX_VERSION}-Darwin-arm64'
        shutil.copy2(Path(str(prefix)+'-tools.pkg')/'Payload/usr/local/bin/toktx', dest/'bin/toktx')
        shutil.copy2(Path(str(prefix)+'-library.pkg')/f'Payload/usr/local/lib/libktx.{KTX_VERSION}.dylib', dest/'lib/libktx.4.dylib')

# Self-host the engine's Basis transcoder; no third-party runtime requests.
wasm = ROOT/'public/wasm/basis'
wasm.mkdir(parents=True, exist_ok=True)
hashes={
 'basis.wasm.js':'82143c2193310331a3186530cc1615950f5ddd4d308aa6a25d82ad1d5933c624',
 'basis.wasm.wasm':'70ed1e72dea7132706ee4e8637d9fc1e348ea03bb3a46644372f309067c47eef',
 'basis.js':'c85407f23254399027517c51dc129e49f3e4abec47450c8f144b2007f64565e9',
}
for name,digest in hashes.items():
    path=wasm/name
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
        download_verified(f'https://raw.githubusercontent.com/playcanvas/engine/v2.24.0/examples/assets/wasm/basis/{name}',path,digest)
ktx_tool()
print('Verified KTX tools and PlayCanvas Basis decoder ready.')
