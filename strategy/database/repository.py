from strategy.database.db_connection import get_connection


def save_backtest_run(
    strategy_name,
    trades_df,
    metrics,
    initial_capital,
):
    """Save one backtest summary and its trades to SQLite."""

    total_trades = len(trades_df)

    if total_trades and "pnl" in trades_df.columns:
        wins = int((trades_df["pnl"] > 0).sum())
        net_pnl = float(trades_df["pnl"].sum())
        win_rate = wins / total_trades * 100
    else:
        wins = 0
        net_pnl = 0.0
        win_rate = 0.0

    if (
        total_trades
        and "capital_after" in trades_df.columns
    ):
        final_capital = float(
            trades_df["capital_after"].iloc[-1]
        )
    else:
        final_capital = float(initial_capital)

    def metric_value(*names):
        for name in names:
            if name in metrics:
                value = metrics[name]

                if value is not None:
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        pass

        return None

    profit_factor = metric_value(
        "Profit Factor",
        "profit_factor",
        "profit factor",
    )

    max_drawdown = metric_value(
        "Max Drawdown",
        "max_drawdown",
        "Maximum Drawdown",
    )

    start_date = None
    end_date = None

    if total_trades:
        if "entry_time" in trades_df.columns:
            start_date = str(trades_df["entry_time"].iloc[0])

        if "exit_time" in trades_df.columns:
            end_date = str(trades_df["exit_time"].iloc[-1])

    with get_connection() as conn:

        cursor = conn.execute(
            """
            INSERT INTO backtest_runs (
                strategy_name,
                start_date,
                end_date,
                initial_capital,
                final_capital,
                total_trades,
                win_rate,
                net_pnl,
                profit_factor,
                max_drawdown
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                strategy_name,
                start_date,
                end_date,
                float(initial_capital),
                final_capital,
                total_trades,
                win_rate,
                net_pnl,
                profit_factor,
                max_drawdown,
            ),
        )

        backtest_run_id = cursor.lastrowid

        # Save each trade belonging to this backtest run.
        for _, trade in trades_df.iterrows():

            def value(column):
                item = trade.get(column)

                if item is None:
                    return None

                try:
                    if item != item:  # NaN check
                        return None
                except (TypeError, ValueError):
                    pass

                if hasattr(item, "isoformat"):
                    return item.isoformat()

                if hasattr(item, "item"):
                    item = item.item()

                return item

            conn.execute(
                """
                INSERT INTO trades (
                    backtest_run_id,
                    signal_time,
                    entry_time,
                    exit_time,
                    signal,
                    entry_price,
                    stop_loss,
                    take_profit,
                    exit_price,
                    position_size,
                    leverage,
                    initial_margin,
                    gross_pnl,
                    entry_fee,
                    exit_fee,
                    total_fees,
                    pnl,
                    capital_before,
                    capital_after,
                    exit_reason
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    backtest_run_id,
                    value("signal_time"),
                    value("entry_time"),
                    value("exit_time"),
                    value("signal"),
                    value("entry_price"),
                    value("stop_loss"),
                    value("take_profit"),
                    value("exit_price"),
                    value("position_size"),
                    value("leverage"),
                    value("initial_margin"),
                    value("gross_pnl"),
                    value("entry_fee"),
                    value("exit_fee"),
                    value("total_fees"),
                    value("pnl"),
                    value("capital_before"),
                    value("capital_after"),
                    value("exit_reason"),
                ),
            )

    print(
        f"Saved {total_trades} trades for backtest run ID {backtest_run_id}."
    )
