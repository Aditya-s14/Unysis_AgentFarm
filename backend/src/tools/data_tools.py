"""Data-loading helpers (CSV seed files etc.)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from ..config.logging_config import get_logger

logger = get_logger(__name__)


def load_csv(path: str | Path) -> List[Dict[str, Any]]:
    """Load a CSV file into a list of dicts using ``pandas``.

    TODO: wire to seed scripts in ``src/models/database.py``.
    """

    import pandas as pd  # local import to keep module import cheap

    p = Path(path)
    if not p.exists():
        logger.warning("csv_not_found", path=str(p))
        return []
    df = pd.read_csv(p)
    return df.to_dict(orient="records")
