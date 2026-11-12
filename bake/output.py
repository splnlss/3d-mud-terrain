"""Publish completed bake outputs while preserving the previous working scene."""
from contextlib import contextmanager
import json
from pathlib import Path
import shutil
import tempfile


@contextmanager
def output_stage(destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    known = {'tileset.json','manifest.json','terrain.glb','tiles','masks','detail','subtrees','.bake-output'}

    def check_destination():
        if destination.is_symlink() or (destination.exists() and (
            not destination.is_dir() or any(path.name not in known for path in destination.iterdir()))):
            raise ValueError(f'unrecognised files in output folder: {destination}')

    check_destination()
    with tempfile.TemporaryDirectory(prefix=f'.{destination.name}-build-', dir=destination.parent) as directory:
        stage = Path(directory)
        yield stage
        # Incomplete metadata or encoder failure cannot replace the working output.
        for name in ['manifest.json', 'tileset.json']:
            json.loads((stage/name).read_text())
        (stage/'.bake-output').write_text('san-luis-relief v1\n')
        check_destination()
        backup = None
        if destination.exists():
            backup = Path(tempfile.mkdtemp(prefix=f'.{destination.name}-previous-', dir=destination.parent))
            backup.rmdir()
            destination.rename(backup)
        try:
            stage.rename(destination)
        except BaseException:
            if backup is not None and not destination.exists():
                backup.rename(destination)
            raise
        if backup is not None:
            shutil.rmtree(backup)
