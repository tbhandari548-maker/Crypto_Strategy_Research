import time
import shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests


# ==========================================
# CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
BACKUP_DIR = BASE_DIR / "backup_before_history"

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

INTERVAL = "1m"
DAYS = 180

API_URL = "https://api.binance.com/api/v3/klines"

COLUMNS = [
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
]


# ==========================================
# DOWNLOAD HISTORICAL DATA
# ==========================================

def download_symbol(symbol, start_time, end_time):
    session = requests.Session()

    rows = []
    current_time = start_time

    print(f"\nDownloading {symbol} history...")

    while current_time < end_time:
        params = {
            "symbol": symbol,
            "interval": INTERVAL,
            "startTime": current_time,
            "endTime": end_time,
            "limit": 1000,
        }

        response = None

        for attempt in range(4):
            try:
                response = session.get(
                    API_URL,
                    params=params,
                    timeout=30,
                )

                if response.status_code == 429:
                    time.sleep(2 * (attempt + 1))
                    continue

                response.raise_for_status()
                break

            except requests.RequestException:
                if attempt == 3:
                    raise

                time.sleep(2 * (attempt + 1))

        if response is None or response.status_code != 200:
            raise RuntimeError(
                f"{symbol}: API request failed."
            )

        batch = response.json()

        if not batch:
            break

        rows.extend(batch)

        # Move to the next candle after the last downloaded candle.
        last_open_time = int(batch[-1][0])
        next_time = last_open_time + 60_000

        if next_time <= current_time:
            raise RuntimeError(
                f"{symbol}: pagination did not advance."
            )

        current_time = next_time

        print(
            f"\r{symbol}: {len(rows):,} candles downloaded",
            end="",
            flush=True,
        )

        time.sleep(0.12)

    print()

    if not rows:
        raise RuntimeError(
            f"No historical data received for {symbol}."
        )

    df = pd.DataFrame(
        rows,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "trades",
            "taker_buy_base",
            "taker_buy_quote",
            "ignore",
        ],
    )

    # Binance timestamps are in milliseconds.
    df["timestamp"] = pd.to_datetime(
        df["open_time"],
        unit="ms",
        utc=True,
    )

    df = df[COLUMNS]

    for column in ["open", "high", "low", "close", "volume"]:
        df[column] = pd.to_numeric(
            df[column],
            errors="raise",
        )

    df = (
        df.drop_duplicates(subset="timestamp")
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    return df


# ==========================================
# MAIN
# ==========================================

def main():
    end_dt = datetime.now(timezone.utc).replace(
        second=0,
        microsecond=0,
    )

    start_dt = end_dt - timedelta(days=DAYS)

    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)

    print("=" * 55)
    print("CRYPTO STRATEGY - HISTORICAL DATA DOWNLOAD")
    print("=" * 55)
    print(f"Period: {start_dt.isoformat()} to {end_dt.isoformat()}")
    print(f"Duration: {DAYS} days")
    print(f"Interval: {INTERVAL}")
    print(f"Symbols: {', '.join(SYMBOLS)}")

    # Download everything first.
    # Existing files are not changed if downloading fails.
    downloaded_data = {}

    for symbol in SYMBOLS:
        downloaded_data[symbol] = download_symbol(
            symbol,
            start_ms,
            end_ms,
        )

    # Back up existing CSV files before replacing them.
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    files_to_backup = []

    for symbol in SYMBOLS:
        files_to_backup.extend(
            BASE_DIR.glob(f"{symbol}_*.csv")
        )

    backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_folder = BACKUP_DIR / backup_time
    backup_folder.mkdir(parents=True, exist_ok=True)

    for file_path in files_to_backup:
        shutil.copy2(
            file_path,
            backup_folder / file_path.name,
        )

    print(f"\nBackup saved in: {backup_folder}")

    # Replace 1-minute datasets with one consistent source.
    for symbol, df in downloaded_data.items():
        output_path = BASE_DIR / f"{symbol}_1m.csv"

        df.to_csv(output_path, index=False)

        print(f"\nSaved: {output_path.name}")
        print(f"Total candles: {len(df):,}")
        print(f"First candle: {df['timestamp'].iloc[0]}")
        print(f"Last candle:  {df['timestamp'].iloc[-1]}")

    print("\nHistorical download completed successfully.")
    print("Next step: run data/resample_data.py")


if __name__ == "__main__":
    main()