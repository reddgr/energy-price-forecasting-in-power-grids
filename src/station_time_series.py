from pathlib import Path

import pandas as pd


def create_station_time_series(
    source_path,
    export_path,
    metric,
    provinces_to_exclude=None,
    provinces_to_include=None,
    max_interpolation_days=10,
):
    """Create and export a date-by-station time series for one station metric."""
    if provinces_to_exclude is not None and provinces_to_include is not None:
        raise ValueError(
            "Use either provinces_to_exclude or provinces_to_include, not both."
        )
    if max_interpolation_days is not None and max_interpolation_days < 0:
        raise ValueError("max_interpolation_days must be non-negative or None.")

    source_path = Path(source_path)
    files = sorted(source_path.glob("*_hist.csv"))
    if not files:
        raise FileNotFoundError(f"No *_hist.csv files found in {source_path}")

    station_series = []
    station_id_discrepancies = []
    for file_path in files:
        station_id = file_path.name.removesuffix("_hist.csv")
        records_processed = 0
        try:
            station_df = pd.read_csv(file_path)
            records_processed = len(station_df)

            required_columns = {"fecha", "indicativo", "provincia", metric}
            missing_columns = required_columns.difference(station_df.columns)
            if missing_columns:
                raise ValueError(f"missing columns: {sorted(missing_columns)}")

            indicativo_values = station_df["indicativo"].dropna().astype(str).unique()
            if any(indicativo != station_id for indicativo in indicativo_values):
                station_id_discrepancies.append(
                    {
                        "source_file": file_path.name,
                        "station_id": station_id,
                        "indicativo_values": ", ".join(indicativo_values),
                    }
                )

            dates = pd.to_datetime(station_df["fecha"], errors="raise")
            if dates.duplicated().any():
                raise ValueError("duplicated dates")

            latest_row = station_df.loc[dates.idxmax()]
            province = latest_row["provincia"]
            if pd.isna(province):
                raise ValueError("missing province in most recent record")
            if provinces_to_exclude is not None and province in provinces_to_exclude:
                print(f"{file_path.name}: {records_processed} records processed (excluded)")
                continue
            if provinces_to_include is not None and province not in provinces_to_include:
                print(f"{file_path.name}: {records_processed} records processed (excluded)")
                continue

            values = pd.to_numeric(station_df[metric], errors="coerce")
            station_series.append(
                pd.Series(values.to_numpy(), index=dates, name=station_id)
            )
            print(f"{file_path.name}: {records_processed} records processed")
        except Exception as error:
            print(
                f"{file_path.name}: {records_processed} records processed "
                f"(skipped: {error})"
            )

    if not station_series:
        raise ValueError("No station files remain after applying the province filter.")

    global_start = min(series.index.min() for series in station_series)
    global_end = max(series.index.max() for series in station_series)
    date_index = pd.date_range(global_start, global_end, freq="D", name="fecha")
    result = pd.concat(
        [series.reindex(date_index) for series in station_series], axis=1
    ).sort_index(axis=1)

    if max_interpolation_days:
        result = result.interpolate(
            method="linear",
            limit=max_interpolation_days,
            limit_area="inside",
        )

    export_path = Path(export_path)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(export_path, index=True)

    discrepancy_log_path = (
        source_path.parent.parent.parent / "logs" / "station_id_discrepancies.csv"
    )
    discrepancy_log_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        station_id_discrepancies,
        columns=["source_file", "station_id", "indicativo_values"],
    ).to_csv(discrepancy_log_path, index=False)

    return result