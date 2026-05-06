"""
Weather station data download utilities for AEMET API.
"""

import pandas as pd
import time


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