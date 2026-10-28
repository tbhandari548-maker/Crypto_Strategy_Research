from pathlib import Path

import pandas as pd

REPORTS_DIR = Path("reports")

SUMMARY_FILE = REPORTS_DIR / "trade_analysis_summary.csv"
SIDE_FILE = REPORTS_DIR / "trade_analysis_buy_sell.csv"


def main():
    if not SUMMARY_FILE.exists():
        print(f"File nahi mili: {SUMMARY_FILE}")
        print("Pehle trade analysis script run karo.")
        return

    summary = pd.read_csv(SUMMARY_FILE)

    print("\n========== STRATEGY DIAGNOSTIC ==========\n")

    required = {
        "symbol",
        "strategy",
        "trades",
        "net_pnl",
        "gross_pnl_before_fees",
        "total_fees",
        "profit_factor",
        "win_rate_pct",
    }

    missing = required - set(summary.columns)

    if missing:
        print("CSV mein required columns missing hain:", missing)
        print("Available columns:", list(summary.columns))
        return

    summary["hypothetical_pnl_without_fees"] = (
        summary["net_pnl"] + summary["total_fees"]
    )

    columns = [
        "symbol",
        "strategy",
        "trades",
        "win_rate_pct",
        "gross_pnl_before_fees",
        "total_fees",
        "net_pnl",
        "hypothetical_pnl_without_fees",
        "profit_factor",
    ]

    print(summary[columns].round(2).to_string(index=False))

    print("\n========== DIAGNOSTIC FINDINGS ==========\n")

    for _, row in summary.iterrows():
        print(f"\n{row['symbol']} | {row['strategy']}")
        print(f"Trades: {int(row['trades'])}")
        print(f"Win rate: {row['win_rate_pct']:.2f}%")
        print(f"Gross PnL before fees: {row['gross_pnl_before_fees']:.2f}")
        print(f"Total fees: {row['total_fees']:.2f}")
        print(f"Net PnL: {row['net_pnl']:.2f}")
        print(f"Profit factor: {row['profit_factor']:.3f}")

        if row["net_pnl"] < 0:
            print("Result: Current tested configuration loss mein hai.")
        else:
            print("Result: Current tested configuration profitable raha.")

        if row["gross_pnl_before_fees"] > 0 and row["net_pnl"] < 0:
            print(
                "Warning: Fees ke baad profit loss mein badal gaya. "
                "Lower-cost execution aur strategy validation test karo."
            )

        if row["profit_factor"] < 1:
            print(
                "Warning: Gross winning trades ka total, gross losing "
                "trades ke total se kam hai."
            )

    if SIDE_FILE.exists():
        side = pd.read_csv(SIDE_FILE)

        print("\n========== BUY / SELL ANALYSIS ==========\n")
        print(side.to_string(index=False))
    else:
        print(f"\nBUY/SELL report nahi mili: {SIDE_FILE}")

    print("\n========================================")
    print("Diagnostic complete.")
    print("Original strategy ya backtest engine change nahi kiya.")
    print("========================================")


if __name__ == "__main__":
    main()

