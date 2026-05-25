import pandas as pd


def safe_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def safe_stat(df, column, func):
    if column not in df.columns:
        return None

    return func(safe_numeric(df[column]))

def calculate_longest_gap_days(df):

    # Required columns
    if "fecha" not in df.columns or "tmed" not in df.columns:
        return None

    # Parse dates
    fechas = pd.to_datetime(df["fecha"], errors="coerce")

    # Valid tmed values
    valid_tmed = safe_numeric(df["tmed"]).notna()

    # Keep only rows with valid date and valid tmed
    valid_dates = fechas[valid_tmed & fechas.notna()]

    if valid_dates.empty:
        return None

    # Remove duplicates and sort
    valid_dates = pd.Series(valid_dates.unique()).sort_values()

    if len(valid_dates) < 2:
        return 0

    # Difference between consecutive valid dates
    diffs = valid_dates.diff().dt.days.fillna(1)

    # Gap is missing intermediate days only
    longest_gap = max(diffs.max() - 1, 0)

    return int(longest_gap)