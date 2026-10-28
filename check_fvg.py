from pathlib import Path
import pandas as pd
from strategy.signals import generate_signals

DATA_DIR = Path(__file__).parent / "data"

file_5m = DATA_DIR / "BTCUSDT_5m.csv"
file_15m = DATA_DIR / "BTCUSDT_15m.csv"

print("=" * 60)
print("FVG STRATEGY DIAGNOSTIC")
print("=" * 60)

if not file_5m.exists() or not file_15m.exists():
    raise FileNotFoundError("BTCUSDT 5m or 15m CSV file not found.")

df_5m = pd.read_csv(file_5m)
df_15m = pd.read_csv(file_15m)

print(f"\n5m candles: {len(df_5m)}")
print(f"15m candles: {len(df_15m)}")

result = generate_signals(df_5m, df_15m)

for col in ["Signal", "Signal_FVG", "FVG_Type",
            "FVG_Retest", "FVG_Retest_Type", "Trading_Session"]:
    if col in result.columns:
        print(f"\n{'=' * 50}")
        print(f"{col} COUNTS")
        print("=" * 50)
        print(result[col].value_counts(dropna=False).to_string())

print(f"\n{'=' * 50}")
print("ORIGINAL VS FVG SIGNALS")
print("=" * 50)

for signal in ["BUY", "SELL", "NONE"]:
    original = (result["Signal"] == signal).sum()
    filtered = (result["Signal_FVG"] == signal).sum()
    print(f"{signal}: Original={original}, After FVG={filtered}")

columns = [
    c for c in [
        "timestamp", "close", "RSI", "Volume_Ratio",
        "Trading_Session", "Signal", "FVG_Type",
        "FVG_Retest", "FVG_Retest_Type", "Signal_FVG"
    ] if c in result.columns
]

print("\nLAST 15 CANDLES")
print(result[columns].tail(15).to_string(index=False))
print("\nDiagnostic completed.")
