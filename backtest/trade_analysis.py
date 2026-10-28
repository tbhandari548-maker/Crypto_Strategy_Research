import pandas as pd


def analyze_trades(trades_df: pd.DataFrame):
    """
    Analyze BUY and SELL trade performance.
    """

    if trades_df.empty:
        return {}

    results = {}

    # ==========================================
    # BUY TRADES
    # ==========================================

    buy_trades = trades_df[
        trades_df["signal"] == "BUY"
    ]

    buy_total = len(buy_trades)

    buy_wins = (
        (buy_trades["pnl"] > 0).sum()
        if buy_total > 0
        else 0
    )

    buy_losses = (
        (buy_trades["pnl"] < 0).sum()
        if buy_total > 0
        else 0
    )

    buy_win_rate = (
        buy_wins / buy_total * 100
        if buy_total > 0
        else 0
    )

    buy_pnl = (
        buy_trades["pnl"].sum()
        if buy_total > 0
        else 0
    )

    buy_average = (
        buy_trades["pnl"].mean()
        if buy_total > 0
        else 0
    )

    # BUY profit factor
    buy_gross_profit = (
        buy_trades.loc[
            buy_trades["pnl"] > 0,
            "pnl"
        ].sum()
        if buy_total > 0
        else 0
    )

    buy_gross_loss = (
        buy_trades.loc[
            buy_trades["pnl"] < 0,
            "pnl"
        ].sum()
        if buy_total > 0
        else 0
    )

    buy_profit_factor = (
        buy_gross_profit / abs(buy_gross_loss)
        if buy_gross_loss != 0
        else 0
    )

    # ==========================================
    # SELL TRADES
    # ==========================================

    sell_trades = trades_df[
        trades_df["signal"] == "SELL"
    ]

    sell_total = len(sell_trades)

    sell_wins = (
        (sell_trades["pnl"] > 0).sum()
        if sell_total > 0
        else 0
    )

    sell_losses = (
        (sell_trades["pnl"] < 0).sum()
        if sell_total > 0
        else 0
    )

    sell_win_rate = (
        sell_wins / sell_total * 100
        if sell_total > 0
        else 0
    )

    sell_pnl = (
        sell_trades["pnl"].sum()
        if sell_total > 0
        else 0
    )

    sell_average = (
        sell_trades["pnl"].mean()
        if sell_total > 0
        else 0
    )

    # SELL profit factor
    sell_gross_profit = (
        sell_trades.loc[
            sell_trades["pnl"] > 0,
            "pnl"
        ].sum()
        if sell_total > 0
        else 0
    )

    sell_gross_loss = (
        sell_trades.loc[
            sell_trades["pnl"] < 0,
            "pnl"
        ].sum()
        if sell_total > 0
        else 0
    )

    sell_profit_factor = (
        sell_gross_profit / abs(sell_gross_loss)
        if sell_gross_loss != 0
        else 0
    )

    # ==========================================
    # EXIT ANALYSIS
    # ==========================================

    stop_loss_count = (
        (trades_df["exit_reason"] == "STOP_LOSS").sum()
    )

    take_profit_count = (
        (trades_df["exit_reason"] == "TAKE_PROFIT").sum()
    )

    total_trades = len(trades_df)

    stop_loss_rate = (
        stop_loss_count / total_trades * 100
        if total_trades > 0
        else 0
    )

    take_profit_rate = (
        take_profit_count / total_trades * 100
        if total_trades > 0
        else 0
    )

    # ==========================================
    # STORE RESULTS
    # ==========================================

    results = {

        # BUY
        "BUY Trades": buy_total,
        "BUY Wins": buy_wins,
        "BUY Losses": buy_losses,
        "BUY Win Rate %": buy_win_rate,
        "BUY P&L": buy_pnl,
        "BUY Average P&L": buy_average,
        "BUY Profit Factor": buy_profit_factor,

        # SELL
        "SELL Trades": sell_total,
        "SELL Wins": sell_wins,
        "SELL Losses": sell_losses,
        "SELL Win Rate %": sell_win_rate,
        "SELL P&L": sell_pnl,
        "SELL Average P&L": sell_average,
        "SELL Profit Factor": sell_profit_factor,

        # EXIT
        "STOP LOSS Trades": stop_loss_count,
        "STOP LOSS %": stop_loss_rate,
        "TAKE PROFIT Trades": take_profit_count,
        "TAKE PROFIT %": take_profit_rate,
    }

    return results