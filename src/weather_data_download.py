"""
Weather station data download utilities for AEMET API.
"""

import pandas as pd
import time
import json
from typing import Union, Dict


def download_station_data(client, station_id, start_date, max_retries=5, sleep_seconds=5):
    """
    Downloads weather station data from a given start date until current date.
    Queries data in 180-day batches and concatenates results.
    
    Args:
        client: AemetClient instance for API calls
        station_id: AEMET station ID (e.g., "0367")
        start_date: Start date as string (format: "YYYY-MM-DD")
        max_retries: Number of retries for failed queries (default: 5)
        sleep_seconds: Seconds to sleep between queries (default: 5)
    
    Returns:
        DataFrame with all retrieved data, deduplicated by 'fecha'
    """
    all_data = pd.DataFrame()
    current_start = start_date
    n_dias = 180
    
    while True:
        # Calculate end date (180 days from current start)
        end_date = (pd.to_datetime(current_start) + pd.Timedelta(days=n_dias)).strftime("%Y-%m-%d")
        
        # Try to fetch with retries
        retries = 0
        data_batch = None
        
        while retries < max_retries:
            try:
                print(f"Fetching data for station {station_id} from {current_start} to {end_date}...")
                data_batch = pd.DataFrame(client.fetch_station_history(station_id, current_start, end_date))
                
                if len(data_batch) > 0:
                    first_date = data_batch['fecha'].iloc[0]
                    last_date = data_batch['fecha'].iloc[-1]
                    print(f"✓ Retrieved {len(data_batch)} records (from {first_date} to {last_date})")
                else:
                    print(f"✓ Retrieved 0 records")
                break
                
            except Exception as e:
                retries += 1
                print(f"✗ Error: {str(e)} (Retry {retries}/{max_retries})")
                if retries < max_retries:
                    time.sleep(sleep_seconds)
        
        # If all retries failed, exit
        if data_batch is None:
            print(f"Failed to retrieve data after {max_retries} retries. Stopping.")
            break
        
        # If no data retrieved, we've reached the end
        if len(data_batch) == 0:
            print("No more data available. Stopping.")
            break
        
        # Append batch to all_data
        all_data = pd.concat([all_data, data_batch], ignore_index=True)
        
        # Update start date for next query (next day after last retrieved date)
        last_fecha = pd.to_datetime(data_batch['fecha'].iloc[-1])
        current_start = (last_fecha + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

        # If next start date is within the last 7 days, consider download complete
        if pd.to_datetime(current_start) >= (pd.Timestamp.today().normalize() - pd.Timedelta(days=7)):
            print("Reached recent dates (<7 days). Stopping.")
            break
        
        # Sleep before next query
        time.sleep(sleep_seconds)
    
    # Remove duplicates based on 'fecha'
    if len(all_data) > 0:
        initial_count = len(all_data)
        all_data = all_data.drop_duplicates(subset=['fecha'], keep='first')
        duplicates_removed = initial_count - len(all_data)
        if duplicates_removed > 0:
            print(f"\nRemoved {duplicates_removed} duplicate records")
        print(f"\nFinal dataset: {len(all_data)} records")
    
    return all_data.reset_index(drop=True)


def cast_columns(df: pd.DataFrame, schema: Union[Dict[str, str], str]) -> pd.DataFrame:
    """
    Cast dataframe columns based on a schema.

    Parameters
    - df: DataFrame to cast (modified in-place and returned).
    - schema: dict mapping column -> dtype (e.g. "datetime", "string", "Int64", "float")
              or a path to a JSON file containing such dict.

    Returns
    - The same DataFrame with casted columns.
    """
    if isinstance(schema, str):
        with open(schema, "r", encoding="utf-8") as f:
            schema = json.load(f)

    date_cols = [col for col, dtype in schema.items() if dtype == "datetime"]
    text_cols = [col for col, dtype in schema.items() if dtype == "string"]
    int_cols = [col for col, dtype in schema.items() if dtype == "Int64"]
    float_cols = [col for col, dtype in schema.items() if dtype == "float"]

    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format="%Y-%m-%d", errors="coerce")

    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    for col in int_cols:
        if col in df.columns:
            df[col] = (
                pd.to_numeric(df[col].astype("string").str.replace(",", ".", regex=False), errors="coerce")
                .astype("Int64")
            )

    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype("string").str.replace(",", ".", regex=False), errors="coerce")

    return df