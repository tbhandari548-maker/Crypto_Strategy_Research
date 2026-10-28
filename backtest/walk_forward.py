from pathlib import Path

import pandas as pd

from config.settings import INITIAL_CAPITAL
from strategy.signals import generate_signals
from backtest.engine import run_backtest


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports"

SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
]

STRATEGIES = {
    "EMA_RSI_VOLUME": "Signal",
    "EMA_RSI_VOLUME_FVG": "Signal_FVG",
}

RISK_REWARD_RATIOS = [2.0, 3.0, 4.0]

INITIAL_TRAIN_FRACTION = 0.60
TEST_FRACTION = 0.10

REQUIRED_COLUMNS = [
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
]


# ============================================================
# LOAD MARKET DATA
# ============================================================

def load_csv(file_path):
    """Load and validate historical candle data."""

    if not file_path.exists():
        raise FileNotFoundError(
            f"Data file not found: {file_path}"
        )

    df = pd.read_csv(file_path)

    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{file_path.name} is missing columns: {missing}"
        )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        utc=True,
        errors="coerce",
    )

    for column in [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df = df.dropna(
        subset=REQUIRED_COLUMNS
    )

    df = (
        df.sort_values("timestamp")
        .drop_duplicates(subset="timestamp")
        .reset_index(drop=True)
    )

    if df.empty:
        raise ValueError(
            f"No valid candle data in {file_path.name}"
        )

    return df


# ============================================================
# CREATE WALK-FORWARD TEST FOLDS
# ============================================================

def create_walk_forward_folds(number_of_rows):
    """
    Use the first 60% as initial history.

    Evaluate subsequent, non-overlapping 10% test windows.
    Each new fold has a later test period.

    The historical window is retained as context.
    This function does not optimize strategy parameters.
    """

    if number_of_rows < 100:
        return []

    initial_train_end = int(
        number_of_rows * INITIAL_TRAIN_FRACTION
    )

    test_size = max(
        1,
        int(number_of_rows * TEST_FRACTION),
    )

    folds = []

    test_start = initial_train_end
    fold_number = 1

    while test_start < number_of_rows:
        test_end = min(
            test_start + test_size,
            number_of_rows,
        )

        folds.append({
            "fold": fold_number,
            "train_start": 0,
            "train_end": test_start,
            "test_start": test_start,
            "test_end": test_end,
        })

        test_start = test_end
        fold_number += 1

    return folds


# ============================================================
# PERFORMANCE METRICS
# ============================================================

def calculate_metrics(trades, initial_capital):
    """Calculate performance metrics from completed trades."""

    if trades is None:
        trades = pd.DataFrame()

    trades = trades.copy()

    if "pnl" in trades.columns:
        pnl = pd.to_numeric(
            trades["pnl"],
            errors="coerce",
        ).fillna(0.0)
    else:
        pnl = pd.Series(dtype=float)

    trade_count = len(trades)

    wins = int((pnl > 0).sum())
    losses = int((pnl < 0).sum())

    win_rate = (
        wins / trade_count * 100
        if trade_count > 0
        else 0.0
    )

    net_pnl = float(pnl.sum())

    gross_profit = float(pnl[pnl > 0].sum())
    gross_loss = abs(float(pnl[pnl < 0].sum()))

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    # Calculate equity and maximum drawdown.
    if "capital_after" in trades.columns and not trades.empty:
        capital_after = pd.to_numeric(
            trades["capital_after"],
            errors="coerce",
        ).dropna()

        equity = pd.concat(
            [
                pd.Series([float(initial_capital)]),
                capital_after.reset_index(drop=True),
            ],
            ignore_index=True,
        )
    else:
        equity = pd.Series(
            [float(initial_capital)]
            + (
                float(initial_capital) + pnl.cumsum()
            ).tolist()
        )

    running_peak = equity.cummax()

    drawdown = (
        (equity - running_peak)
        / running_peak.replace(0, float("nan"))
        * 100
    )

    max_drawdown = (
        abs(float(drawdown.min()))
        if not drawdown.dropna().empty
        else 0.0
    )

    # Total fees.
    if "total_fees" in trades.columns:
        total_fees = float(
            pd.to_numeric(
                trades["total_fees"],
                errors="coerce",
            ).fillna(0).sum()
        )
    else:
        total_fees = 0.0

    # Final capital.
    if "capital_after" in trades.columns and not trades.empty:
        capital_values = pd.to_numeric(
            trades["capital_after"],
            errors="coerce",
        ).dropna()

        final_capital = (
            float(capital_values.iloc[-1])
            if not capital_values.empty
            else float(initial_capital) + net_pnl
        )
    else:
        final_capital = float(initial_capital) + net_pnl

    return {
        "Trades": trade_count,
        "Wins": wins,
        "Losses": losses,
        "Win_Rate_Pct": round(win_rate, 2),
        "Net_PnL": round(net_pnl, 2),
        "Final_Capital": round(final_capital, 2),
        "Profit_Factor": (
            round(profit_factor, 3)
            if pd.notna(profit_factor)
            and profit_factor != float("inf")
            else profit_factor
        ),
        "Max_Drawdown_Pct": round(max_drawdown, 2),
        "Total_Fees": round(total_fees, 2),
    }


# ============================================================
# RUN ONE BACKTEST
# ============================================================

def run_one_test(
    test_df,
    signal_column,
    risk_reward_ratio,
):
    """
    Run one strategy on one test window.

    The selected strategy's signals are copied into the
    Signal column expected by the existing backtest engine.
    """

    if signal_column not in test_df.columns:
        raise ValueError(
            f"Signal column '{signal_column}' not found."
        )

    # The engine expects a column named Signal.
    test_data = test_df.copy()
    test_data["Signal"] = test_data[signal_column]

    result = run_backtest(
        test_data,
        risk_reward_ratio=risk_reward_ratio,
    )

    if result is None:
        return pd.DataFrame()

    if not isinstance(result, pd.DataFrame):
        raise TypeError(
            "run_backtest() must return a pandas DataFrame."
        )

    return result.copy()


# ============================================================
# MAIN WALK-FORWARD PROCESS
# ============================================================

def run_walk_forward():
    """Run walk-forward evaluation and save all CSV reports."""

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary_rows = []
    all_trade_rows = []

    print("=" * 70)
    print("WALK-FORWARD STRATEGY TEST")
    print("=" * 70)

    print(f"Data folder: {DATA_DIR}")
    print(f"Reports folder: {REPORT_DIR}")
    print(f"Initial capital per test: {INITIAL_CAPITAL:,.2f}")
    print(f"Risk-reward ratios: {RISK_REWARD_RATIOS}")

    for symbol in SYMBOLS:
        print("\n" + "=" * 70)
        print(f"PROCESSING: {symbol}")
        print("=" * 70)

        try:
            df_5m = load_csv(
                DATA_DIR / f"{symbol}_5m.csv"
            )

            df_15m = load_csv(
                DATA_DIR / f"{symbol}_15m.csv"
            )

            print(f"5m candles: {len(df_5m):,}")
            print(f"15m candles: {len(df_15m):,}")

            # Signals and indicators are calculated in chronological
            # order using the signal-generation module.
            signal_df = generate_signals(
                df_5m.copy(),
                df_15m.copy(),
            )

            signal_df = (
                signal_df.sort_values("timestamp")
                .reset_index(drop=True)
            )

            folds = create_walk_forward_folds(
                len(signal_df)
            )

            if not folds:
                print(
                    f"Skipping {symbol}: not enough candles."
                )
                continue

            print(f"Test folds: {len(folds)}")

            for fold_info in folds:
                fold_number = fold_info["fold"]

                start = fold_info["test_start"]
                end = fold_info["test_end"]

                test_df = signal_df.iloc[
                    start:end
                ].copy()

                if test_df.empty:
                    continue

                start_time = test_df["timestamp"].iloc[0]
                end_time = test_df["timestamp"].iloc[-1]

                print(
                    f"\nFold {fold_number} | "
                    f"Test: {start_time} to {end_time}"
                )

                for strategy_name, signal_column in STRATEGIES.items():

                    if signal_column not in test_df.columns:
                        print(
                            f"Skipping {strategy_name}: "
                            f"missing {signal_column}"
                        )
                        continue

                    for rr in RISK_REWARD_RATIOS:

                        try:
                            trades = run_one_test(
                                test_df=test_df,
                                signal_column=signal_column,
                                risk_reward_ratio=rr,
                            )

                            metrics = calculate_metrics(
                                trades,
                                INITIAL_CAPITAL,
                            )

                            row = {
                                "Symbol": symbol,
                                "Fold": fold_number,
                                "Strategy": strategy_name,
                                "Signal_Column": signal_column,
                                "Risk_Reward": f"1:{rr:g}",
                                "Test_Start": start_time,
                                "Test_End": end_time,
                                **metrics,
                            }

                            summary_rows.append(row)

                            if not trades.empty:
                                trades["Symbol"] = symbol
                                trades["Fold"] = fold_number
                                trades["Strategy"] = strategy_name
                                trades["Signal_Column"] = signal_column
                                trades["Risk_Reward"] = f"1:{rr:g}"

                                all_trade_rows.append(trades)

                            print(
                                f"  {strategy_name} | RR 1:{rr:g} | "
                                f"Trades: {metrics['Trades']} | "
                                f"PnL: {metrics['Net_PnL']:.2f} | "
                                f"Win rate: "
                                f"{metrics['Win_Rate_Pct']:.2f}%"
                            )

                        except Exception as exc:
                            print(
                                f"  ERROR | {symbol} | "
                                f"Fold {fold_number} | "
                                f"{strategy_name} | RR 1:{rr:g}: "
                                f"{exc}"
                            )

        except Exception as exc:
            print(
                f"ERROR processing {symbol}: {exc}"
            )

    # ========================================================
    # SAVE FOLD-BY-FOLD SUMMARY
    # ========================================================

    summary_df = pd.DataFrame(summary_rows)

    summary_path = (
        REPORT_DIR / "walk_forward_summary.csv"
    )

    summary_df.to_csv(
        summary_path,
        index=False,
    )

    print(f"\nSaved: {summary_path}")

    # ========================================================
    # SAVE AGGREGATE RESULTS
    # ========================================================

    aggregate_path = (
        REPORT_DIR / "walk_forward_aggregate.csv"
    )

    if not summary_df.empty:

        aggregate_df = (
            summary_df.groupby(
                ["Symbol", "Strategy", "Risk_Reward"],
                dropna=False,
            )
            .agg(
                Folds=("Fold", "nunique"),
                Total_Trades=("Trades", "sum"),
                Total_Wins=("Wins", "sum"),
                Total_Losses=("Losses", "sum"),
                Total_Net_PnL=("Net_PnL", "sum"),
                Average_Fold_PnL=("Net_PnL", "mean"),
                Average_Win_Rate_Pct=("Win_Rate_Pct", "mean"),
                Average_Profit_Factor=("Profit_Factor", "mean"),
                Worst_Fold_Drawdown_Pct=(
                    "Max_Drawdown_Pct",
                    "max",
                ),
                Total_Fees=("Total_Fees", "sum"),
            )
            .reset_index()
        )

        aggregate_df["Overall_Win_Rate_Pct"] = (
            aggregate_df["Total_Wins"]
            / aggregate_df["Total_Trades"].replace(0, pd.NA)
            * 100
        ).fillna(0).round(2)

        aggregate_df["Average_Fold_PnL"] = (
            aggregate_df["Average_Fold_PnL"].round(2)
        )

        aggregate_df["Total_Net_PnL"] = (
            aggregate_df["Total_Net_PnL"].round(2)
        )

        aggregate_df["Average_Win_Rate_Pct"] = (
            aggregate_df["Average_Win_Rate_Pct"].round(2)
        )

        aggregate_df["Average_Profit_Factor"] = (
            aggregate_df["Average_Profit_Factor"].round(3)
        )

        aggregate_df["Worst_Fold_Drawdown_Pct"] = (
            aggregate_df["Worst_Fold_Drawdown_Pct"].round(2)
        )

        aggregate_df["Total_Fees"] = (
            aggregate_df["Total_Fees"].round(2)
        )

    else:
        aggregate_df = pd.DataFrame(
            columns=[
                "Symbol",
                "Strategy",
                "Risk_Reward",
                "Folds",
                "Total_Trades",
                "Total_Wins",
                "Total_Losses",
                "Total_Net_PnL",
                "Average_Fold_PnL",
                "Average_Win_Rate_Pct",
                "Average_Profit_Factor",
                "Worst_Fold_Drawdown_Pct",
                "Total_Fees",
                "Overall_Win_Rate_Pct",
            ]
        )

    aggregate_df.to_csv(
        aggregate_path,
        index=False,
    )

    print(f"Saved: {aggregate_path}")

    # ========================================================
    # SAVE ALL TRADE RECORDS
    # ========================================================

    trades_path = (
        REPORT_DIR / "walk_forward_test_trades.csv"
    )

    if all_trade_rows:
        all_trades_df = pd.concat(
            all_trade_rows,
            ignore_index=True,
        )
    else:
        all_trades_df = pd.DataFrame()

    all_trades_df.to_csv(
        trades_path,
        index=False,
    )

    print(f"Saved: {trades_path}")

    # ========================================================
    # FINAL STATUS
    # ========================================================

    print("\n" + "=" * 70)
    print("WALK-FORWARD TEST COMPLETED")
    print("=" * 70)

    print(f"Summary rows: {len(summary_df)}")
    print(f"Aggregate rows: {len(aggregate_df)}")
    print(f"Trade rows: {len(all_trades_df)}")

    print("\nReports created:")
    print(f"1. {summary_path}")
    print(f"2. {aggregate_path}")
    print(f"3. {trades_path}")

    if summary_df.empty:
        print(
            "\nWARNING: No summary results were generated. "
            "Check the errors printed above."
        )


if __name__ == "__main__":
    run_walk_forward()

