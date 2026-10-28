import time
from pathlib import Path

import pandas as pd
import requests


# ============================================================
# SETTINGS
# ============================================================

SYMBOLS = {
    "BTCUSDT": "XBTUSD",
    "ETHUSDT": "ETHUSD",
    "SOLUSDT": "SOLUSD",
}

INTERVAL = 1

URL = "https://api.kraken.com/0/public/OHLC"

DATA_DIR = Path(__file__).parent


# ============================================================
# DOWNLOAD LATEST DATA
# ============================================================

def download_symbol(symbol, pair):

    print()
    print("=" * 60)
    print(f"Updating {symbol} using Kraken API...")
    print("=" * 60)

    params = {
        "pair": pair,
        "interval": INTERVAL,
    }

    response = requests.get(
        URL,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    result = response.json()

    if result.get("error"):
        raise RuntimeError(
            f"Kraken API error: {result['error']}"
        )

    # Kraken returns a pair-specific key and a "last" key.
    pair_key = next(
        (
            key for key in result["result"]
            if key != "last"
        ),
        None,
    )

    if pair_key is None:
        raise RuntimeError(
            f"No candle data returned for {symbol}"
        )

    candles = result["result"][pair_key]

    if not candles:
        raise RuntimeError(
            f"No candles available for {symbol}"
        )

    df_new = pd.DataFrame(
        candles,
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "vwap",
            "volume",
            "count",
        ],
    )

    # Kraken timestamps are in seconds.
    df_new["timestamp"] = pd.to_datetime(
        pd.to_numeric(df_new["timestamp"]),
        unit="s",
        utc=True,
    )

    columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    for column in columns:
        df_new[column] = pd.to_numeric(
            df_new[column],
            errors="coerce",
        )

    df_new = df_new[
        ["timestamp", "open", "high", "low", "close", "volume"]
    ]

    df_new = df_new.dropna()

    # Existing CSV file.
    output_file = DATA_DIR / f"{symbol}_{INTERVAL}m.csv"

    # Preserve historical data and append/update recent candles.
    if output_file.exists():

        print("Existing historical CSV found.")

        df_old = pd.read_csv(output_file)

        if "timestamp" in df_old.columns:

            df_old["timestamp"] = pd.to_datetime(
                df_old["timestamp"],
                utc=True,
                errors="coerce",
            )

            for column in columns:
                if column in df_old.columns:
                    df_old[column] = pd.to_numeric(
                        df_old[column],
                        errors="coerce",
                    )

            required_columns = [
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]

            if all(
                column in df_old.columns
                for column in required_columns
            ):
                df_old = df_old[required_columns]

                df = pd.concat(
                    [df_old, df_new],
                    ignore_index=True,
                )
            else:
                raise RuntimeError(
                    f"Existing CSV has unexpected columns: {output_file}"
                )

        else:
            raise RuntimeError(
                f"Existing CSV has no timestamp column: {output_file}"
            )

    else:
        df = df_new

    # Remove duplicate candles and sort by time.
    df = df.dropna(
        subset=["timestamp"]
    )

    df = df.drop_duplicates(
        subset=["timestamp"],
        keep="last",
    )

    df = df.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    # Save combined historical and recent data.
    df.to_csv(
        output_file,
        index=False,
    )

    print(f"Symbol       : {symbol}")
    print(f"New candles  : {len(df_new)}")
    print(f"Total candles: {len(df)}")
    print(f"Latest candle: {df['timestamp'].max()}")
    print(f"Saved file   : {output_file}")
    print("Update successful!")


# ============================================================
# DOWNLOAD ALL SYMBOLS
# ============================================================

def download_all_symbols():

    print()
    print("=" * 60)
    print("LATEST CRYPTO MARKET DATA UPDATE")
    print("Data source: Kraken public API")
    print("=" * 60)

    failed_symbols = []

    for symbol, pair in SYMBOLS.items():

        try:
            download_symbol(symbol, pair)

        except Exception as error:
            failed_symbols.append(symbol)

            print()
            print(f"ERROR updating {symbol}: {error}")

        time.sleep(1)

    print()
    print("=" * 60)

    if failed_symbols:
        print("UPDATE INCOMPLETE!")
        print("Failed symbols:", ", ".join(failed_symbols))
        print(
            "Check the errors above. "
            "Some CSV files may still contain old data."
        )
    else:
        print("ALL SYMBOLS UPDATED SUCCESSFULLY")

    print("=" * 60)

    return len(failed_symbols) == 0


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    success = download_all_symbols()

    if not success:
        raise SystemExit(
            "Market data update failed for one or more symbols."
        )

