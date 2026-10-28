import pandas as pd
import numpy as np


def calculate_metrics(
    trades_df: pd.DataFrame,
    initial_capital: float,
):
    """
    Calculate overall backtest performance metrics.
    """

    if trades_df.empty:
        return {}

    pnl = trades_df["pnl"]

    # -----------------------------------------
    # BASIC TRADE STATISTICS
    # -----------------------------------------

    total_trades = len(trades_df)

    winning_trades = (
        pnl > 0
    ).sum()

    losing_trades = (
        pnl < 0
    ).sum()

    win_rate = (
        winning_trades
        / total_trades
        * 100
    )

    # -----------------------------------------
    # PROFIT / LOSS
    # -----------------------------------------

    gross_profit = pnl[
        pnl > 0
    ].sum()

    gross_loss = abs(
        pnl[pnl < 0].sum()
    )

    net_profit = pnl.sum()

    # -----------------------------------------
    # PROFIT FACTOR
    # -----------------------------------------

    if gross_loss > 0:

        profit_factor = (
            gross_profit
            / gross_loss
        )

    else:

        profit_factor = np.inf

    # -----------------------------------------
    # AVERAGE WIN / LOSS
    # -----------------------------------------

    average_win = (
        pnl[pnl > 0].mean()
        if winning_trades > 0
        else 0
    )

    average_loss = (
        pnl[pnl < 0].mean()
        if losing_trades > 0
        else 0
    )

    # -----------------------------------------
    # EXPECTANCY
    # -----------------------------------------

    expectancy = pnl.mean()

    # -----------------------------------------
    # RETURN
    # -----------------------------------------

    final_capital = (
        trades_df[
            "capital_after"
        ].iloc[-1]
    )

    total_return_pct = (
        (
            final_capital
            - initial_capital
        )
        / initial_capital
        * 100
    )

    # -----------------------------------------
    # EQUITY CURVE
    # -----------------------------------------

    equity = pd.Series(
        [initial_capital]
        + trades_df[
            "capital_after"
        ].tolist()
    )

    running_peak = (
        equity.cummax()
    )

    drawdown = (
        equity
        - running_peak
    )

    drawdown_pct = (
        drawdown
        / running_peak
        * 100
    )

    max_drawdown = drawdown.min()

    max_drawdown_pct = (
        drawdown_pct.min()
    )

    # -----------------------------------------
    # BEST / WORST TRADE
    # -----------------------------------------

    best_trade = pnl.max()

    worst_trade = pnl.min()

    # -----------------------------------------
    # AVERAGE R
    # -----------------------------------------

    risk_amount = (
        trades_df["entry_price"]
        - trades_df["stop_loss"]
    ).abs() * trades_df[
        "position_size"
    ]

    valid_risk = (
        risk_amount > 0
    )

    if valid_risk.any():

        r_values = (
            pnl[valid_risk]
            / risk_amount[valid_risk]
        )

        average_r = (
            r_values.mean()
        )

    else:

        average_r = 0

    # -----------------------------------------
    # LONG / SHORT PERFORMANCE
    # -----------------------------------------

    buy_trades = trades_df[
        trades_df["signal"] == "BUY"
    ]

    sell_trades = trades_df[
        trades_df["signal"] == "SELL"
    ]

    buy_pnl = (
        buy_trades["pnl"].sum()
        if not buy_trades.empty
        else 0
    )

    sell_pnl = (
        sell_trades["pnl"].sum()
        if not sell_trades.empty
        else 0
    )

    # -----------------------------------------
    # RESULT
    # -----------------------------------------

    metrics = {

        "Total Trades":
            total_trades,

        "Winning Trades":
            winning_trades,

        "Losing Trades":
            losing_trades,

        "Win Rate %":
            win_rate,

        "Gross Profit":
            gross_profit,

        "Gross Loss":
            gross_loss,

        "Net Profit":
            net_profit,

        "Profit Factor":
            profit_factor,

        "Average Win":
            average_win,

        "Average Loss":
            average_loss,

        "Expectancy":
            expectancy,

        "Initial Capital":
            initial_capital,

        "Final Capital":
            final_capital,

        "Total Return %":
            total_return_pct,

        "Max Drawdown":
            max_drawdown,

        "Max Drawdown %":
            max_drawdown_pct,

        "Best Trade":
            best_trade,

        "Worst Trade":
            worst_trade,

        "Average R":
            average_r,

        "BUY P&L":
            buy_pnl,

        "SELL P&L":
            sell_pnl,
    }

    return metrics