"""Exercise the real CLI entry point without downloading datasets."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


def run_cli(tmp_path, *args):
    return subprocess.run([sys.executable,'-m','bake',*args], cwd=tmp_path,
        env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[1])},
        capture_output=True,text=True,timeout=30)


def test_help_loads_the_entire_bake_entry_point(tmp_path):
    result = run_cli(tmp_path,'--help')
    assert result.returncode==0, result.stderr
    assert not (tmp_path/'data').exists()


@pytest.mark.parametrize('args', [('--spacing','0'), ('--full','--style','--gain','-1'),
                                  ('--material',)])
def test_invalid_options_fail_before_downloading_or_writing(tmp_path,args):
    result = run_cli(tmp_path,*args)
    assert result.returncode==2, result.stderr
    assert not (tmp_path/'data').exists()
    assert not (tmp_path/'public').exists()
