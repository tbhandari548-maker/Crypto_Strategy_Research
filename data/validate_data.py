from pathlib import Path

import pandas as pd


DATA_FILE = Path(__file__).parent / "BTCUSDT_5m.csv"


def validate_data():

    print("=" * 50)
    print("BTCUSDT DATA VALIDATION")
    print("=" * 50)

    df = pd.read_csv(DATA_FILE)

    # -----------------------------
    # Basic information
    # -----------------------------

    print("\n1. BASIC INFORMATION")

    print(f"Rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")

    # -----------------------------
    # Timestamp
    # -----------------------------

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        utc=True
    )

    print("\n2. DATE RANGE")

    print(f"Start: {df['timestamp'].min()}")
    print(f"End:   {df['timestamp'].max()}")

    # -----------------------------
    # Duplicate timestamps
    # -----------------------------

    duplicate_count = df["timestamp"].duplicated().sum()

    print("\n3. DUPLICATE CANDLES")

    print(f"Duplicates: {duplicate_count}")

    # -----------------------------
    # Missing values
    # -----------------------------

    missing_values = df.isna().sum().sum()

    print("\n4. MISSING VALUES")

    print(f"Missing values: {missing_values}")

    # -----------------------------
    # OHLC validation
    # -----------------------------

    invalid_ohlc = (
        (df["high"] < df["open"])
        | (df["high"] < df["close"])
        | (df["low"] > df["open"])
        | (df["low"] > df["close"])
        | (df["high"] < df["low"])
    )

    print("\n5. OHLC VALIDATION")

    print(
        f"Invalid OHLC rows: "
        f"{invalid_ohlc.sum()}"
    )

    # -----------------------------
    # Negative / zero values
    # -----------------------------

    invalid_price = (
        (df["open"] <= 0)
        | (df["high"] <= 0)
        | (df["low"] <= 0)
        | (df["close"] <= 0)
    )

    invalid_volume = df["volume"] < 0

    print("\n6. PRICE / VOLUME VALIDATION")

    print(
        f"Invalid price rows: "
        f"{invalid_price.sum()}"
    )

    print(
        f"Invalid volume rows: "
        f"{invalid_volume.sum()}"
    )

    # -----------------------------
    # Candle gaps
    # -----------------------------

    time_diff = (
        df["timestamp"]
        .sort_values()
        .diff()
    )

    expected_interval = pd.Timedelta(minutes=5)

    gaps = time_diff[
        time_diff > expected_interval
    ]

    print("\n7. CANDLE GAP CHECK")

    print(f"Unexpected gaps: {len(gaps)}")

    if len(gaps) > 0:

        print("\nFirst few gaps:")

        print(gaps.head())

    # -----------------------------
    # Final result
    # -----------------------------

    total_problems = (
        duplicate_count
        + missing_values
        + invalid_ohlc.sum()
        + invalid_price.sum()
        + invalid_volume.sum()
    )

    print("\n" + "=" * 50)

    if total_problems == 0:

        print("DATA QUALITY: PASSED")

    else:

        print("DATA QUALITY: CHECK REQUIRED")

    print("=" * 50)


if __name__ == "__main__":
    validate_data()