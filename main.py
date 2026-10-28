import subprocess
import sys
import pandas as pd
from strategy.database.repository import save_backtest_run
from backtest.metrics import calculate_metrics
from backtest.engine import run_backtest
from strategy.signals import generate_signals
from config.settings import INITIAL_CAPITAL
from backtest.trade_analysis import analyze_trades

from visualization.charts import (
    generate_tradingview_style_dashboard,
)
print()
print("=" * 60)
print("UPDATING LATEST MARKET DATA")
print("=" * 60)

# Update latest 1m Binance data
subprocess.run(
    [
        sys.executable,
        "data/download_data.py"
    ],
    check=True
)

# Build all chart timeframes
subprocess.run(
    [
        sys.executable,
        "data/resample_data.py"
    ],
    check=True
)

print()
print("Latest market data updated successfully.")


DATA_5M = "data/BTCUSDT_5m.csv"
DATA_15M = "data/BTCUSDT_15m.csv"


def main():

    print("=" * 60)
    print("CRYPTO STRATEGY - SIGNAL TEST")
    print("=" * 60)

    # ==========================================
    # LOAD DATA
    # ==========================================

    df_5m = pd.read_csv(DATA_5M)
    df_15m = pd.read_csv(DATA_15M)

    print(f"\n5m candles : {len(df_5m)}")
    print(f"15m candles: {len(df_15m)}")

    # ==========================================
    # GENERATE SIGNALS
    # ==========================================

    df = generate_signals(
        df_5m,
        df_15m,
    )

    # ==========================================
    # SIGNAL COUNTS
    # ==========================================

    signal_counts = (
        df["Signal"]
        .value_counts()
    )

    print("\nSIGNAL COUNTS")
    print("-" * 40)

    print(
        f"BUY  : {signal_counts.get('BUY', 0)}"
    )

    print(
        f"SELL : {signal_counts.get('SELL', 0)}"
    )

    print(
        f"NONE : {signal_counts.get('NONE', 0)}"
    )

    # ==========================================
    # LATEST SIGNALS
    # ==========================================

    signals = df[
        df["Signal"] != "NONE"
    ].copy()

    print("\nLATEST SIGNALS")
    print("-" * 60)

    if len(signals) == 0:

        print("No BUY/SELL signals found.")

    else:

        columns = [
            "timestamp",
            "close",
            "EMA_20",
            "EMA_50",
            "EMA_200",
            "RSI",
            "ATR",
            "Volume_Ratio",
            "Trend_15m",
            "Signal",
        ]

        print(
            signals[columns]
            .tail(20)
            .to_string(index=False)
        )

    # ==========================================
    # BASELINE VS FVG BACKTEST
    # ==========================================

    import os

    os.makedirs("reports", exist_ok=True)

    print("\n")
    print("=" * 65)
    print("BASELINE STRATEGY VS FVG STRATEGY")
    print("=" * 65)

    # ------------------------------------------
    # 1. BASELINE STRATEGY
    # ------------------------------------------

    print("\nRunning baseline strategy...")

    baseline_df = df.copy()

    baseline_df["Signal"] = baseline_df["Signal"].fillna("NONE")

    baseline_trades = run_backtest(baseline_df)

    baseline_metrics = calculate_metrics(
        baseline_trades,
        initial_capital=INITIAL_CAPITAL,
    )
    
    baseline_run_id = save_backtest_run(
    strategy_name="Baseline",
    trades_df=baseline_trades,
    metrics=baseline_metrics,
    initial_capital=INITIAL_CAPITAL,
)

    # ------------------------------------------
    # 2. FVG-ENHANCED STRATEGY
    # ------------------------------------------

    print("Running FVG-enhanced strategy...")

    fvg_df = df.copy()

    fvg_df["Signal"] = fvg_df["Signal_FVG"].fillna("NONE")

    fvg_trades = run_backtest(fvg_df)

    fvg_metrics = calculate_metrics(
        fvg_trades,
        initial_capital=INITIAL_CAPITAL,
    )
    
    fvg_run_id = save_backtest_run(
    strategy_name="FVG",
    trades_df=fvg_trades,
    metrics=fvg_metrics,
    initial_capital=INITIAL_CAPITAL,
)

    # ------------------------------------------
    # 3. COMPARE PERFORMANCE
    # ------------------------------------------

    def get_metric(metrics, *possible_names):
        """Find a metric without assuming its exact key name."""

        for name in possible_names:
            if name in metrics:
                return metrics[name]

        return None

    comparison_rows = []

    strategies = [
        ("Baseline", baseline_trades, baseline_metrics),
        ("FVG", fvg_trades, fvg_metrics),
    ]

    for strategy_name, trades, metrics in strategies:

        total_pnl = (
            float(trades["pnl"].sum())
            if not trades.empty and "pnl" in trades.columns
            else 0.0
        )

        total_trades = len(trades)

        wins = (
            int((trades["pnl"] > 0).sum())
            if total_trades > 0 and "pnl" in trades.columns
            else 0
        )

        win_rate = (
            wins / total_trades * 100
            if total_trades > 0
            else 0.0
        )

        final_capital = (
            float(trades["capital_after"].iloc[-1])
            if total_trades > 0 and "capital_after" in trades.columns
            else float(INITIAL_CAPITAL)
        )

        profit_factor = get_metric(
            metrics,
            "Profit Factor",
            "profit_factor",
            "profit factor",
        )

        max_drawdown = get_metric(
            metrics,
            "Max Drawdown",
            "max_drawdown",
            "Maximum Drawdown",
        )

        comparison_rows.append({
            "Strategy": strategy_name,
            "Total Trades": total_trades,
            "Winning Trades": wins,
            "Win Rate (%)": round(win_rate, 2),
            "Net PnL": round(total_pnl, 2),
            "Final Capital": round(final_capital, 2),
            "Profit Factor": profit_factor,
            "Max Drawdown": max_drawdown,
        })

    comparison_df = pd.DataFrame(comparison_rows)

    print("\nSTRATEGY COMPARISON")
    print("-" * 100)
    print(comparison_df.to_string(index=False))

    # ------------------------------------------
    # 4. SAVE COMPARISON REPORT
    # ------------------------------------------

    comparison_path = "reports/strategy_comparison.csv"

    comparison_df.to_csv(
        comparison_path,
        index=False,
    )

    print(f"\nComparison report saved: {comparison_path}")

    # ------------------------------------------
    # 5. SAVE INDIVIDUAL TRADE REPORTS
    # ------------------------------------------

    baseline_trades.to_csv(
        "reports/baseline_trades.csv",
        index=False,
    )

    fvg_trades.to_csv(
        "reports/fvg_trades.csv",
        index=False,
    )

    print("Baseline trades saved: reports/baseline_trades.csv")
    print("FVG trades saved: reports/fvg_trades.csv")

    # ------------------------------------------
    # 6. SHOW FVG SIGNAL COUNTS
    # ------------------------------------------

    fvg_signal_counts = (
        df["Signal_FVG"]
        .value_counts()
    )

    print("\nFVG SIGNAL COUNTS")
    print("-" * 40)

    print(f"BUY  : {fvg_signal_counts.get('BUY', 0)}")
    print(f"SELL : {fvg_signal_counts.get('SELL', 0)}")
    print(f"NONE : {fvg_signal_counts.get('NONE', 0)}")

    # ------------------------------------------
    # 7. SESSION-WISE SIGNAL ANALYSIS
    # ------------------------------------------

    session_summary = (
        df.groupby("Trading_Session")
        .agg(
            Candles=("timestamp", "count"),
            Baseline_Buys=("Signal", lambda s: (s == "BUY").sum()),
            Baseline_Sells=("Signal", lambda s: (s == "SELL").sum()),
            FVG_Buys=("Signal_FVG", lambda s: (s == "BUY").sum()),
            FVG_Sells=("Signal_FVG", lambda s: (s == "SELL").sum()),
        )
        .reset_index()
    )

    session_summary.to_csv(
        "reports/session_signal_analysis.csv",
        index=False,
    )

    print("\nSESSION-WISE SIGNAL ANALYSIS")
    print("-" * 70)
    print(session_summary.to_string(index=False))

    print(
        "\nSession signal report saved: "
        "reports/session_signal_analysis.csv"
    )

    # ------------------------------------------
    # 8. RUN THE EXISTING DASHBOARD
    # ------------------------------------------

    generate_tradingview_style_dashboard(
        df,
        baseline_trades,
        lookback_candles=3000,
    )
if __name__ == "__main__":
    main()