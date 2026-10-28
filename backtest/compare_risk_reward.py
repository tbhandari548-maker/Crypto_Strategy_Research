from pathlib import Path

import pandas as pd

from config.settings import INITIAL_CAPITAL
from strategy.signals import generate_signals
from backtest.engine import run_backtest


DATA_DIR = Path("data")
REPORT_DIR = Path("reports")

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

RISK_REWARD_RATIOS = [1.0, 1.5, 2.0, 3.0, 4.0]

STRATEGIES = {
    "EMA_RSI_VOLUME": "Signal",
    "EMA_RSI_VOLUME_FVG": "Signal_FVG",
}


def load_csv(symbol, timeframe):
    """Load and clean market candle data."""

    path = DATA_DIR / f"{symbol}_{timeframe}.csv"

    if not path.exists():
        print(f"Missing file: {path}")
        return None

    df = pd.read_csv(path)

    required = {
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    }

    missing = required - set(df.columns)

    if missing:
        print(f"Missing columns in {path}: {sorted(missing)}")
        return None

    df["timestamp"] = pd.to_datetime(
        df["timestamp"], utc=True, errors="coerce"
    )

    for column in ["open", "high", "low", "close", "volume"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = (
        df.dropna(
            subset=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]
        )
        .sort_values("timestamp")
        .drop_duplicates(subset="timestamp")
        .reset_index(drop=True)
    )

    return df


def calculate_metrics(trades, initial_capital):
    """Calculate performance metrics from completed trades."""

    if trades is None or trades.empty:
        return {
            "trades": 0,
            "win_rate_pct": 0.0,
            "net_pnl": 0.0,
            "final_capital": round(float(initial_capital), 2),
            "profit_factor": 0.0,
            "max_drawdown_pct": 0.0,
            "total_fees": 0.0,
        }

    pnl = pd.to_numeric(
        trades["pnl"], errors="coerce"
    ).fillna(0.0)

    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]

    gross_profit = float(wins.sum())
    gross_loss = abs(float(losses.sum()))

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    if "capital_after" in trades.columns:
        equity = pd.concat(
            [
                pd.Series([float(initial_capital)]),
                pd.to_numeric(
                    trades["capital_after"], errors="coerce"
                ).dropna().reset_index(drop=True),
            ],
            ignore_index=True,
        )
    else:
        equity = pd.concat(
            [
                pd.Series([float(initial_capital)]),
                float(initial_capital) + pnl.cumsum(),
            ],
            ignore_index=True,
        )

    peak = equity.cummax()

    drawdown = (
        (equity - peak) / peak.where(peak != 0)
    )

    max_drawdown_pct = (
        abs(float(drawdown.min())) * 100
        if not drawdown.empty
        else 0.0
    )

    total_fees = (
        pd.to_numeric(
            trades["total_fees"], errors="coerce"
        ).fillna(0.0).sum()
        if "total_fees" in trades.columns
        else 0.0
    )

    final_capital = (
        float(equity.iloc[-1])
        if not equity.empty
        else float(initial_capital)
    )

    return {
        "trades": int(len(trades)),
        "win_rate_pct": round(
            len(wins) / len(trades) * 100, 2
        ),
        "net_pnl": round(float(pnl.sum()), 2),
        "final_capital": round(final_capital, 2),
        "profit_factor": (
            round(profit_factor, 3)
            if profit_factor != float("inf")
            else "inf"
        ),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "total_fees": round(float(total_fees), 2),
    }


def run_comparison():
    """Compare multiple RR ratios across symbols and strategies."""

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    all_summaries = []
    all_trades = []

    for symbol in SYMBOLS:
        print(f"\n{'=' * 65}")
        print(f"Loading data for {symbol}")
        print("=" * 65)

        df_5m = load_csv(symbol, "5m")
        df_15m = load_csv(symbol, "15m")

        if df_5m is None or df_15m is None:
            print(f"Skipping {symbol}: missing candle data.")
            continue

        if len(df_5m) < 250 or len(df_15m) < 250:
            print(f"Skipping {symbol}: insufficient candle history.")
            continue

        try:
            signaled = generate_signals(
                df_5m.copy(),
                df_15m.copy(),
            )

            if signaled is None or signaled.empty:
                print(f"No signals generated for {symbol}.")
                continue

            for strategy_name, signal_column in STRATEGIES.items():

                if signal_column not in signaled.columns:
                    print(
                        f"Skipping {strategy_name}: "
                        f"missing column {signal_column}"
                    )
                    continue

                print(f"\nStrategy: {strategy_name}")

                for rr in RISK_REWARD_RATIOS:
                    test_df = signaled.copy()

                    test_df["Signal"] = (
                        test_df[signal_column].fillna("NONE")
                    )

                    print(f"Testing RR 1:{rr:g} ...")

                    trades = run_backtest(
                        test_df,
                        risk_reward_ratio=rr,
                    )

                    if trades is None:
                        trades = pd.DataFrame()

                    metrics = calculate_metrics(
                        trades,
                        INITIAL_CAPITAL,
                    )

                    row = {
                        "symbol": symbol,
                        "strategy": strategy_name,
                        "risk_reward_ratio": f"1:{rr:g}",
                        **metrics,
                    }

                    all_summaries.append(row)

                    if not trades.empty:
                        saved_trades = trades.copy()

                        saved_trades.insert(
                            0, "risk_reward_ratio", f"1:{rr:g}"
                        )
                        saved_trades.insert(
                            0, "strategy", strategy_name
                        )
                        saved_trades.insert(
                            0, "symbol", symbol
                        )

                        all_trades.append(saved_trades)

                    print(
                        f"Trades: {metrics['trades']} | "
                        f"Win rate: {metrics['win_rate_pct']}% | "
                        f"Net PnL: {metrics['net_pnl']} | "
                        f"PF: {metrics['profit_factor']} | "
                        f"Max DD: {metrics['max_drawdown_pct']}%"
                    )

        except Exception as exc:
            print(f"ERROR for {symbol}: {exc}")
            raise

    if not all_summaries:
        print("\nNo results generated. Check data and signal generation.")
        return

    summary_df = pd.DataFrame(all_summaries)

    summary_path = REPORT_DIR / "risk_reward_comparison.csv"

    summary_df.to_csv(summary_path, index=False)

    if all_trades:
        trades_path = REPORT_DIR / "risk_reward_all_trades.csv"

        pd.concat(
            all_trades,
            ignore_index=True,
        ).to_csv(trades_path, index=False)

        print(f"\nAll trades saved to: {trades_path}")

    print("\n" + "=" * 80)
    print("RISK-REWARD COMPARISON COMPLETE")
    print("=" * 80)

    print(
        summary_df.to_string(index=False)
    )

    print(f"\nSummary saved to: {summary_path}")


if __name__ == "__main__":
    run_comparison()
