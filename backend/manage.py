#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import site
import sys
from pathlib import Path


def _bootstrap_local_venv():
    """
    Ensure the local virtualenv site-packages are on sys.path even if the user
    calls `python3 manage.py ...` instead of `.venv/bin/python ...`.
    """
    base_dir = Path(__file__).resolve().parent
    venv_dir = base_dir / ".venv"
    if not venv_dir.exists():
        return

    candidates = []
    lib_dir = venv_dir / "lib"
    if lib_dir.exists():
        candidates.extend((python_dir / "site-packages") for python_dir in lib_dir.glob("python*"))

    # Windows-style layout
    candidates.append(venv_dir / "Lib" / "site-packages")

    for path in candidates:
        if path.exists():
            site.addsitedir(path)


def main():
    """Run administrative tasks."""
    _bootstrap_local_venv()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
