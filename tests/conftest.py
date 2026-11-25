"""Point the whole test session at a throwaway SQLite file.

This runs before any test module imports `app`, so `app.core.config.settings`
and the SQLAlchemy engine pick up the temporary DATABASE_URL instead of the
developer's real gtmos.db. Every run starts from an empty database.
"""
import os
import tempfile
from pathlib import Path

_TMP_DIR = Path(tempfile.mkdtemp(prefix="gtmos_test_"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP_DIR / 'gtmos_test.db').as_posix()}"
os.environ["LLM_MODE"] = "mock"
