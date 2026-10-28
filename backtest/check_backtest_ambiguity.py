import pandas as pd

from strategy.signals import generate_signals


def check_ambiguous_exits(df, symbol, timeframe):
    df = df.copy()

    df["timestamp"] = pd.to_datetime(
        df["timestamp"], utc=True
    )

    df = df.sort_values("timestamp").reset_index(drop=True)

    both_hit_count = 0
    total_signal_count = 0

    # Check BUY/SELL signals with the existing ATR-based levels.
    from strategy.risk_management import calculate_trade_levels

    for i in range(len(df) - 1):
        signal = df.loc[i, "Signal"]

        if signal not in ("BUY", "SELL"):
            continue

        atr = df.loc[i, "ATR"]
        next_open = df.loc[i + 1, "open"]

        if pd.isna(atr) or pd.isna(next_open) or atr <= 0:
            continue

        sl, tp = calculate_trade_levels(
            entry_price=float(next_open),
            atr=float(atr),
            signal=signal,
        )

        if sl is None or tp is None:
            continue

        high = float(df.loc[i + 1, "high"])
        low = float(df.loc[i + 1, "low"])

        if signal == "BUY":
            stop_hit = low <= sl
            target_hit = high >= tp
        else:
            stop_hit = high >= sl
            target_hit = low <= tp

        total_signal_count += 1

        if stop_hit and target_hit:
            both_hit_count += 1

    print(f"\n{symbol} {timeframe}")
    print(f"Signals checked: {total_signal_count}")
    print(f"Same-candle SL and TP hits: {both_hit_count}")


if __name__ == "__main__":
    print(
        "Diagnostic script created. "
        "We will connect the signal generation next."
    )