from pathlib import Path

import pandas as pd


def create_station_time_series(
    source_path,
    export_path,
    metric,
    provinces_to_exclude=None,
    provinces_to_include=None,
    max_interpolation_days=10,
    start_date=None,
    end_date=None,
):
    """Create and export a date-by-station time series for one station metric."""
    if provinces_to_exclude is not None and provinces_to_include is not None:
        raise ValueError(
            "Use either provinces_to_exclude or provinces_to_include, not both."
        )
    if max_interpolation_days is not None and max_interpolation_days < 0:
        raise ValueError("max_interpolation_days must be non-negative or None.")

    start_date = (
        pd.to_datetime(start_date, errors="raise")
        if start_date is not None
        else None
    )
    end_date = (
        pd.to_datetime(end_date, errors="raise") if end_date is not None else None
    )
    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("start_date must be on or before end_date.")

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
            if start_date is not None:
                in_range = dates >= start_date
                if end_date is not None:
                    in_range &= dates <= end_date
                dates = dates[in_range]
                values = values[in_range]
            elif end_date is not None:
                in_range = dates <= end_date
                dates = dates[in_range]
                values = values[in_range]

            if dates.empty:
                print(
                    f"{file_path.name}: {records_processed} records processed "
                    "(excluded)"
                )
                continue

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


def create_station_daily_averages(
    source_path,
    export_path,
    metric,
    provinces_to_exclude=None,
    provinces_to_include=None,
):
    """Create and export a 365-day station climatology for one metric."""
    if provinces_to_exclude is not None and provinces_to_include is not None:
        raise ValueError(
            "Use either provinces_to_exclude or provinces_to_include, not both."
        )

    source_path = Path(source_path)
    files = sorted(source_path.glob("*_hist.csv"))
    if not files:
        raise FileNotFoundError(f"No *_hist.csv files found in {source_path}")

    station_averages = []
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
            valid_values = pd.DataFrame(
                {"month": dates.dt.month, "day": dates.dt.day, "value": values}
            ).query("not (month == 2 and day == 29)")
            station_average = valid_values.groupby(["month", "day"])["value"].mean()
            station_averages.append(station_average.rename(station_id))
            print(f"{file_path.name}: {records_processed} records processed")
        except Exception as error:
            print(
                f"{file_path.name}: {records_processed} records processed "
                f"(skipped: {error})"
            )

    if not station_averages:
        raise ValueError("No station files remain after applying the province filter.")

    canonical_dates = pd.date_range("1900-01-01", "1900-12-31", freq="D", name="fecha")
    canonical_keys = pd.MultiIndex.from_arrays(
        [canonical_dates.month, canonical_dates.day], names=["month", "day"]
    )
    result = pd.concat(
        [series.reindex(canonical_keys) for series in station_averages], axis=1
    )
    result.index = canonical_dates
    result = result.sort_index(axis=1)

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