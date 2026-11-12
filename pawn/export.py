"""CSV export utilities for reports and data extracts."""

import csv
import os
from decimal import Decimal
from typing import Any


def export_csv(rows: list[dict[str, Any]], path: str) -> None:
    """Export a list of dictionaries to a CSV file at the specified path."""
    dest_dir = os.path.dirname(os.path.abspath(path))
    if dest_dir:
        os.makedirs(dest_dir, exist_ok=True)

    if not rows:
        with open(path, mode="w", newline="", encoding="utf-8") as f:
            pass
        return

    # Collect all field names in order of occurrence
    fieldnames: list[str] = []
    for r in rows:
        for k in r.keys():
            if k not in fieldnames:
                fieldnames.append(k)

    with open(path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for r in rows:
            formatted_row = {
                k: (str(v) if isinstance(v, Decimal) else ("" if v is None else str(v)))
                for k, v in r.items()
            }
            writer.writerow(formatted_row)


export_laporan_csv = export_csv
