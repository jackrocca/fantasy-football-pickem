"""
One-off repair utilities for Google Sheets data consistency.
"""
import sys
import os
import pandas as pd

# Ensure project root is on path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.sheets_storage import get_sheets_storage


def repair_odds_cache():
    """Ensure odds_cache sheet has correct headers and rows aligned."""
    storage = get_sheets_storage()
    ws = storage._get_worksheet("odds_cache")
    df = storage._worksheet_to_dataframe(ws)

    expected_cols = ["week", "year", "cache_date", "odds_data"]

    if df.empty:
        clean = pd.DataFrame(columns=expected_cols)
    else:
        # Keep only expected columns, create missing ones, and reorder
        clean = df.copy()
        for col in expected_cols:
            if col not in clean.columns:
                clean[col] = pd.NA
        # Drop unexpected columns
        clean = clean[expected_cols]

    # Write back (clears first, then writes headers+data)
    storage._dataframe_to_worksheet(clean, ws)
    storage.flush()
    return len(clean)


if __name__ == "__main__":
    rows = repair_odds_cache()
    print(f"✅ Repaired odds_cache with {rows} rows and correct headers.")


