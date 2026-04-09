"""
Central config — loads .env once for all local runs.
Import this at the top of any connector/etl file.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Walk up to find ops/.env — works from any subdirectory
_here = Path(__file__).parent
_env_path = _here / "ops" / ".env"

load_dotenv(dotenv_path=_env_path, override=False)
