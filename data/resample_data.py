from pathlib import Path

import pandas as pd


# ============================================================
# SETTINGS
# ============================================================

DATA_DIR = Path(__file__).parent

SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
]

INPUT_INTERVAL = "1m"

TIMEFRAMES = {
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1D",
}


# ============================================================
# RESAMPLE ONE SYMBOL
# ============================================================

def resample_symbol(symbol):

    input_file = (
        DATA_DIR /
        f"{symbol}_{INPUT_INTERVAL}.csv"
    )

    print()
    print("=" * 50)
    print(f"Processing {symbol}")
    print("=" * 50)

    if not input_file.exists():

        print(
            f"ERROR: {input_file} not found."
        )

        return

    # Read data
    df = pd.read_csv(input_file)

    # Timestamp
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        utc=True,
    )

    # Set timestamp as index
    df = df.set_index("timestamp")

    # Numeric columns
    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    for column in numeric_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df = df.dropna()

    # ========================================================
    # CREATE TIMEFRAMES
    # ========================================================

    for timeframe_name, rule in TIMEFRAMES.items():

        print()
        print(
            f"Creating {symbol} {timeframe_name}..."
        )

        resampled = (
            df.resample(
                rule,
                label="left",
                closed="left",
            )
            .agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                }
            )
        )

        resampled = resampled.dropna()

        resampled = (
            resampled
            .reset_index()
        )

        # Output
        output_file = (
            DATA_DIR /
            f"{symbol}_{timeframe_name}.csv"
        )

        resampled.to_csv(
            output_file,
            index=False,
        )

        print(
            f"{symbol} {timeframe_name}: "
            f"{len(resampled)} candles"
        )

        print(
            f"Start: "
            f"{resampled['timestamp'].min()}"
        )

        print(
            f"End:   "
            f"{resampled['timestamp'].max()}"
        )

        print(
            f"Saved: {output_file}"
        )


# ============================================================
# RESAMPLE ALL SYMBOLS
# ============================================================

def resample_all_symbols():

    print()
    print("=" * 60)
    print("CREATING MULTI-SYMBOL TIMEFRAME DATA")
    print("=" * 60)

    for symbol in SYMBOLS:

        resample_symbol(symbol)

    print()
    print("=" * 60)
    print("ALL SYMBOL TIMEFRAMES CREATED")
    print("=" * 60)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    resample_all_symbols()