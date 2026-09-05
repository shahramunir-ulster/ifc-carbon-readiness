from __future__ import annotations

import hashlib
from pathlib import Path


APPLICATION_VERSION = '1.2.3'


def source_tree_sha256(root: str | Path) -> str:
    """Hash the executable application source using paths plus file contents."""
    root_path = Path(root).resolve()
    files = [root_path / 'app.py']
    files.extend(sorted((root_path / 'src').glob('*.py')))
    files.extend(sorted((root_path / 'scripts').glob('*.py')))
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(root_path).as_posix().encode('utf-8')
        digest.update(relative + b'\0')
        digest.update(path.read_bytes())
        digest.update(b'\0')
    return digest.hexdigest()
