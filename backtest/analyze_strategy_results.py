from pathlib import Path
import pandas as pd

REPORT_DIR = Path("reports")
INPUT_FILE = REPORT_DIR / "strategy_comparison_all_trades.csv"


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Could not find {INPUT_FILE}. Run the multi-backtest first.")

    df = pd.read_csv(INPUT_FILE)
    required = {
        "symbol", "strategy", "signal", "pnl", "gross_pnl",
        "entry_fee", "exit_fee", "total_fees", "exit_reason", "entry_time"
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Trade report is missing columns: {sorted(missing)}")

    for col in ["pnl", "gross_pnl", "entry_fee", "exit_fee", "total_fees"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["is_win"] = df["pnl"] > 0

    # Summary grouped by coin and strategy
    rows = []
    for (symbol, strategy), group in df.groupby(["symbol", "strategy"], sort=True):
        pnl = group["pnl"]
        winners, losers = pnl[pnl > 0], pnl[pnl < 0]
        gross_profit, gross_loss = float(winners.sum()), abs(float(losers.sum()))
        pf = gross_profit / gross_loss if gross_loss else (float("inf") if gross_profit else 0.0)
        rows.append({
            "symbol": symbol,
            "strategy": strategy,
            "trades": len(group),
            "wins": int((pnl > 0).sum()),
            "losses": int((pnl < 0).sum()),
            "win_rate_pct": round((pnl > 0).mean() * 100, 2),
            "net_pnl": round(float(pnl.sum()), 2),
            "gross_pnl_before_fees": round(float(group["gross_pnl"].sum()), 2),
            "total_fees": round(float(group["total_fees"].sum()), 2),
            "avg_win": round(float(winners.mean()), 2) if len(winners) else 0.0,
            "avg_loss": round(float(losers.mean()), 2) if len(losers) else 0.0,
            "profit_factor": round(pf, 3) if pf != float("inf") else "inf",
            "stop_loss_count": int((group["exit_reason"] == "STOP_LOSS").sum()),
            "take_profit_count": int((group["exit_reason"] == "TAKE_PROFIT").sum()),
            "end_of_data_count": int((group["exit_reason"] == "END_OF_DATA").sum()),
            "liquidation_count": int((group["exit_reason"] == "LIQUIDATION").sum()),
        })

    summary = pd.DataFrame(rows)
    summary_path = REPORT_DIR / "trade_analysis_summary.csv"
    summary.to_csv(summary_path, index=False)

    # BUY vs SELL performance
    side = (
        df.groupby(["symbol", "strategy", "signal"], dropna=False)
        .agg(
            trades=("pnl", "size"),
            win_rate_pct=("is_win", lambda x: round(x.mean() * 100, 2)),
            net_pnl=("pnl", "sum"),
            avg_pnl=("pnl", "mean"),
            total_fees=("total_fees", "sum"),
            stop_loss_count=("exit_reason", lambda x: int((x == "STOP_LOSS").sum())),
            take_profit_count=("exit_reason", lambda x: int((x == "TAKE_PROFIT").sum())),
        )
        .reset_index()
    )
    for col in ["net_pnl", "avg_pnl", "total_fees"]:
        side[col] = side[col].round(2)
    side_path = REPORT_DIR / "trade_analysis_buy_sell.csv"
    side.to_csv(side_path, index=False)

    # Exit reason performance
    exits = (
        df.groupby(["symbol", "strategy", "exit_reason"], dropna=False)
        .agg(
            trades=("pnl", "size"),
            net_pnl=("pnl", "sum"),
            avg_pnl=("pnl", "mean"),
            total_fees=("total_fees", "sum"),
        )
        .reset_index()
    )
    for col in ["net_pnl", "avg_pnl", "total_fees"]:
        exits[col] = exits[col].round(2)
    exits_path = REPORT_DIR / "trade_analysis_exit_reasons.csv"
    exits.to_csv(exits_path, index=False)

    print("\n========== STRATEGY TRADE ANALYSIS ==========")
    print("\n--- Summary by coin and strategy ---")
    print(summary.to_string(index=False))
    print("\n--- BUY vs SELL performance ---")
    print(side.to_string(index=False))
    print("\n--- Exit reasons ---")
    print(exits.to_string(index=False))
    print("\nSaved reports:")
    print(f"  {summary_path}")
    print(f"  {side_path}")
    print(f"  {exits_path}")
    print("\nNote: historical backtest results do not predict future performance.")


if __name__ == "__main__":
    main()
