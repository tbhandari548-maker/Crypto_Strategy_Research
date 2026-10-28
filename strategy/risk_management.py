import pandas as pd

from config.settings import (
    ATR_SL_MULTIPLIER,
    RISK_REWARD_RATIO,
    RISK_PER_TRADE,
    LEVERAGE,
    MAX_MARGIN_FRACTION,
)


def calculate_trade_levels(
    entry_price: float,
    atr: float,
    signal: str,
    risk_reward_ratio: float = RISK_REWARD_RATIO,
):
    """
    Calculate Stop Loss and Take Profit.

    risk_reward_ratio:
        1.0 = RR 1:1
        1.5 = RR 1:1.5
        2.0 = RR 1:2
        3.0 = RR 1:3
        4.0 = RR 1:4
    """

    if (
        pd.isna(atr)
        or pd.isna(entry_price)
        or entry_price <= 0
        or atr <= 0
        or risk_reward_ratio <= 0
    ):
        return None, None

    if signal == "BUY":
        stop_loss = entry_price - atr * ATR_SL_MULTIPLIER
        risk_per_unit = entry_price - stop_loss
        take_profit = entry_price + risk_per_unit * risk_reward_ratio

    elif signal == "SELL":
        stop_loss = entry_price + atr * ATR_SL_MULTIPLIER
        risk_per_unit = stop_loss - entry_price
        take_profit = entry_price - risk_per_unit * risk_reward_ratio

    else:
        return None, None

    if stop_loss <= 0 or take_profit <= 0:
        return None, None

    return stop_loss, take_profit




def calculate_position_size(
    capital: float,
    entry_price: float,
    stop_loss: float,
) -> float:
    """
    Calculate futures position size.

    Risk limit:
        Maximum planned price risk = capital * RISK_PER_TRADE

    Margin limit:
        Estimated initial margin cannot exceed
        capital * MAX_MARGIN_FRACTION.

    LEVERAGE affects the maximum permitted notional value.
    Fees, slippage, funding and liquidation must be handled
    separately by the backtest engine.
    """

    if capital <= 0 or entry_price <= 0:
        return 0.0

    if stop_loss <= 0:
        return 0.0

    if LEVERAGE <= 0:
        raise ValueError("LEVERAGE must be greater than zero.")

    if not 0 < RISK_PER_TRADE <= 1:
        raise ValueError("RISK_PER_TRADE must be between 0 and 1.")

    if not 0 < MAX_MARGIN_FRACTION <= 1:
        raise ValueError(
            "MAX_MARGIN_FRACTION must be between 0 and 1."
        )

    risk_per_unit = abs(entry_price - stop_loss)

    if risk_per_unit <= 0:
        return 0.0

    # Planned price risk for the trade.
    capital_at_risk = capital * RISK_PER_TRADE

    risk_based_size = (
        capital_at_risk / risk_per_unit
    )

    # Maximum margin budget for this position.
    margin_budget = (
        capital * MAX_MARGIN_FRACTION
    )

    # Approximate notional exposure allowed by leverage.
    max_notional = margin_budget * LEVERAGE

    max_margin_based_size = (
        max_notional / entry_price
    )

    # Use the more restrictive of the two limits.
    position_size = min(
        risk_based_size,
        max_margin_based_size,
    )

    return max(0.0, position_size)

