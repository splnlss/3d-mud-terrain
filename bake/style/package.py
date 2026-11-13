"""Publish complete portable packages without damaging the previous result."""
from contextlib import contextmanager
import json
from pathlib import Path,PurePosixPath
import shutil
import tempfile


def write_package(stage: Path, metadata: dict) -> None:
    stage=Path(stage)
    if metadata.get('schema_version')!=1:raise ValueError('unsupported package schema')
    files=metadata.get('files',[])
    if not isinstance(files,list):raise ValueError('files must be relative package paths')
    for value in files:
        if not isinstance(value,str) or '\\' in value or ':' in value:
            raise ValueError('relative package paths required')
        relative=PurePosixPath(value)
        if relative.is_absolute() or '..' in relative.parts or value in ['', '.']:
            raise ValueError('relative paths must not escape package')
        target=stage/value
        if not target.resolve().is_relative_to(stage.resolve()):raise ValueError('path escape')
        if not target.is_file():raise ValueError(f'missing package file: {value}')
    (stage/'manifest.json').write_text(json.dumps(metadata,indent=2,allow_nan=False)+'\n')


@contextmanager
def package_stage(destination):
    destination=Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.is_symlink() or (destination.exists() and not (destination/'.terrain-style-package').is_file()):
        raise ValueError('destination is not a managed style package')
    with tempfile.TemporaryDirectory(prefix=f'.{destination.name}-stage-',dir=destination.parent) as temporary:
        stage=Path(temporary)
        yield stage
        metadata=json.loads((stage/'manifest.json').read_text())
        write_package(stage,metadata)
        (stage/'.terrain-style-package').write_text('terrain-style-v1\n')
        backup=None
        if destination.exists():
            backup=Path(tempfile.mkdtemp(prefix=f'.{destination.name}-backup-',dir=destination.parent))
            backup.rmdir();destination.rename(backup)
        try:stage.rename(destination)
        except BaseException:
            if backup is not None:backup.rename(destination)
            raise
        if backup is not None:shutil.rmtree(backup)
