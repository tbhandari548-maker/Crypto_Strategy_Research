from pathlib import Path
import pandas as pd

from config.settings import INITIAL_CAPITAL
from strategy.signals import generate_signals
from backtest.engine import run_backtest

DATA_DIR = Path("data")
REPORT_DIR = Path("reports")
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


def load_csv(symbol, timeframe):
    path = DATA_DIR / f"{symbol}_{timeframe}.csv"
    if not path.exists():
        print(f"Missing file: {path}")
        return None

    df = pd.read_csv(path)
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        print(f"Invalid columns in {path}: missing {sorted(missing)}")
        return None

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return (
        df.dropna(subset=["timestamp", "open", "high", "low", "close", "volume"])
        .sort_values("timestamp")
        .drop_duplicates(subset="timestamp")
        .reset_index(drop=True)
    )


def make_summary(symbol, strategy_name, candles, trades, initial_capital):
    market_days = 0.0
    if candles is not None and len(candles) >= 2:
        timestamps = pd.to_datetime(candles["timestamp"], utc=True)
        market_days = max((timestamps.max() - timestamps.min()).total_seconds() / 86400, 0.0)

    if trades is None or trades.empty:
        return {
            "symbol": symbol, "strategy": strategy_name,
            "timeframe": "5m entry / 15m confirmation",
            "candles": len(candles) if candles is not None else 0,
            "trades": 0, "win_rate_pct": 0.0, "net_pnl": 0.0,
            "final_capital": round(float(initial_capital), 2),
            "profit_factor": 0.0, "max_drawdown_pct": 0.0,
            "trades_per_day": 0.0, "status": "No trades",
        }

    if "pnl" not in trades.columns:
        raise ValueError(f"Trades missing 'pnl' column. Columns: {list(trades.columns)}")

    pnl = pd.to_numeric(trades["pnl"], errors="coerce").fillna(0.0)
    wins, losses = pnl[pnl > 0], pnl[pnl < 0]
    gross_profit, gross_loss = float(wins.sum()), abs(float(losses.sum()))

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    if "capital_after" in trades.columns:
        capital_after = pd.to_numeric(trades["capital_after"], errors="coerce").dropna()
        final_capital = float(capital_after.iloc[-1]) if not capital_after.empty else float(initial_capital + pnl.sum())
        equity = pd.concat([pd.Series([float(initial_capital)]), capital_after.reset_index(drop=True)], ignore_index=True)
    else:
        final_capital = float(initial_capital + pnl.sum())
        equity = pd.concat([pd.Series([float(initial_capital)]), float(initial_capital) + pnl.cumsum().reset_index(drop=True)], ignore_index=True)

    peak = equity.cummax()
    drawdown = (equity - peak) / peak.where(peak != 0)
    max_drawdown_pct = abs(float(drawdown.min())) * 100 if not drawdown.empty else 0.0
    trades_per_day = len(trades) / market_days if market_days > 0 else 0.0

    return {
        "symbol": symbol, "strategy": strategy_name,
        "timeframe": "5m entry / 15m confirmation",
        "candles": len(candles) if candles is not None else 0,
        "trades": int(len(trades)),
        "win_rate_pct": round(len(wins) / len(trades) * 100, 2),
        "net_pnl": round(float(pnl.sum()), 2),
        "final_capital": round(final_capital, 2),
        "profit_factor": round(profit_factor, 3) if profit_factor != float("inf") else "inf",
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "trades_per_day": round(trades_per_day, 2),
        "status": "OK",
    }


def run_one_strategy(symbol, strategy_name, signal_df, signal_column):
    df = signal_df.copy()
    df["Signal"] = df[signal_column].fillna("NONE")
    trades = run_backtest(df)
    if trades is None:
        trades = pd.DataFrame()

    if not trades.empty:
        trades.insert(0, "strategy", strategy_name)
        trades.insert(0, "timeframe", "5m")
        trades.insert(0, "symbol", symbol)
    return trades


def run_multi_backtests():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    summaries, all_trades = [], []

    for symbol in SYMBOLS:
        print(f"\nLoading {symbol} data...")
        df_5m = load_csv(symbol, "5m")
        df_15m = load_csv(symbol, "15m")

        if df_5m is None or df_15m is None:
            print(f"Skipping {symbol}: both 5m and 15m data are required.")
            continue
        if len(df_5m) < 250 or len(df_15m) < 250:
            print(f"Skipping {symbol}: insufficient EMA 200 history (5m={len(df_5m)}, 15m={len(df_15m)}).")
            continue

        try:
            # This strategy is specifically 5m entries with completed 15m confirmation.
            signaled = generate_signals(df_5m.copy(), df_15m.copy())
            if signaled is None or signaled.empty:
                print(f"No signal data returned for {symbol}.")
                continue
            if "Signal" not in signaled.columns or "Signal_FVG" not in signaled.columns:
                raise ValueError("Expected both 'Signal' and 'Signal_FVG' columns.")

            for strategy_name, signal_column in [
                ("EMA_RSI_VOLUME", "Signal"),
                ("EMA_RSI_VOLUME_FVG", "Signal_FVG"),
            ]:
                print(f"Running {symbol} | {strategy_name}...")
                trades = run_one_strategy(symbol, strategy_name, signaled, signal_column)
                summary = make_summary(symbol, strategy_name, signaled, trades, INITIAL_CAPITAL)
                summaries.append(summary)

                if not trades.empty:
                    trades.to_csv(REPORT_DIR / f"{symbol}_{strategy_name.lower()}_trades.csv", index=False)
                    all_trades.append(trades)

                print(
                    f"Trades: {summary['trades']} | Win rate: {summary['win_rate_pct']}% | "
                    f"Net PnL: {summary['net_pnl']} | Profit factor: {summary['profit_factor']}"
                )
        except Exception as exc:
            print(f"ERROR for {symbol}: {exc}")
            for strategy_name in ["EMA_RSI_VOLUME", "EMA_RSI_VOLUME_FVG"]:
                summaries.append({
                    "symbol": symbol, "strategy": strategy_name,
                    "timeframe": "5m entry / 15m confirmation",
                    "candles": len(df_5m), "trades": 0, "win_rate_pct": 0.0,
                    "net_pnl": 0.0, "final_capital": round(float(INITIAL_CAPITAL), 2),
                    "profit_factor": 0.0, "max_drawdown_pct": 0.0,
                    "trades_per_day": 0.0, "status": f"ERROR: {exc}",
                })

    summary_df = pd.DataFrame(summaries)
    summary_path = REPORT_DIR / "strategy_comparison_summary.csv"
    summary_df.to_csv(summary_path, index=False)

    if all_trades:
        combined_path = REPORT_DIR / "strategy_comparison_all_trades.csv"
        pd.concat(all_trades, ignore_index=True).to_csv(combined_path, index=False)
        print(f"Combined trades saved to: {combined_path}")
    else:
        print("\nNo trades were generated by either strategy.")

    print("\n========== STRATEGY COMPARISON COMPLETE ==========")
    if not summary_df.empty:
        print(summary_df.to_string(index=False))
    print(f"\nSummary saved to: {summary_path}")


if __name__ == "__main__":
    run_multi_backtests()