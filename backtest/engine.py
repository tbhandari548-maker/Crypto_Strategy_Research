import pandas as pd

from strategy.risk_management import (
    calculate_trade_levels,
    calculate_position_size,
)

from config.settings import (
    INITIAL_CAPITAL,
    FEE_RATE,
    SLIPPAGE_RATE,
    LEVERAGE,
    MAX_MARGIN_FRACTION,
    MAINTENANCE_MARGIN_RATE,
)


def run_backtest(
    df: pd.DataFrame,
    risk_reward_ratio: float | None = None,
    signal_column: str = "Signal",
) -> pd.DataFrame:
    """Run a simplified historical futures backtest."""

    required = {
        "timestamp", "open", "high", "low",
        "close", "ATR", signal_column,
    }

    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    if df.empty:
        return pd.DataFrame()

    if INITIAL_CAPITAL <= 0 or LEVERAGE <= 0:
        raise ValueError(
            "INITIAL_CAPITAL and LEVERAGE must be positive."
        )

    if not 0 < MAX_MARGIN_FRACTION <= 1:
        raise ValueError(
            "MAX_MARGIN_FRACTION must be between 0 and 1."
        )

    if MAINTENANCE_MARGIN_RATE < 0:
        raise ValueError(
            "MAINTENANCE_MARGIN_RATE cannot be negative."
        )

    if FEE_RATE < 0 or not 0 <= SLIPPAGE_RATE < 1:
        raise ValueError("Invalid fee or slippage settings.")

    df = df.copy()
    df["timestamp"] = pd.to_datetime(
        df["timestamp"], utc=True, errors="raise"
    )
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Convert frequently accessed columns to arrays to reduce
    # the overhead of repeated DataFrame.iloc calls.
    timestamps = df["timestamp"].array
    opens = pd.to_numeric(df["open"], errors="coerce").to_numpy()
    highs = pd.to_numeric(df["high"], errors="coerce").to_numpy()
    lows = pd.to_numeric(df["low"], errors="coerce").to_numpy()
    closes = pd.to_numeric(df["close"], errors="coerce").to_numpy()
    atrs = pd.to_numeric(df["ATR"], errors="coerce").to_numpy()
    signals = df[signal_column].fillna("NONE").to_numpy()

    capital = float(INITIAL_CAPITAL)
    trades = []
    position = None
    i = 0
    n = len(df)

    while i < n:

        # ==============================================
        # ENTRY
        # ==============================================
        if position is None:

            if i >= n - 1 or capital <= 0:
                break

            signal = signals[i]

            if signal not in ("BUY", "SELL"):
                i += 1
                continue

            raw_entry = opens[i + 1]
            atr = atrs[i]

            if (
                not pd.notna(raw_entry)
                or raw_entry <= 0
                or not pd.notna(atr)
                or atr <= 0
            ):
                i += 1
                continue

            entry_price = (
                raw_entry * (1 + SLIPPAGE_RATE)
                if signal == "BUY"
                else raw_entry * (1 - SLIPPAGE_RATE)
            )

            if risk_reward_ratio is None:
              stop_loss, take_profit = calculate_trade_levels(
            entry_price, atr, signal
              )   
            else:
                 stop_loss, take_profit = calculate_trade_levels(
                 entry_price, atr, signal,
                 risk_reward_ratio=risk_reward_ratio
    )

            if stop_loss is None or take_profit is None:
                i += 1
                continue

            size = calculate_position_size(
                capital=capital,
                entry_price=entry_price,
                stop_loss=stop_loss,
            )

            if not pd.notna(size) or size <= 0:
                i += 1
                continue

            notional = entry_price * size
            margin = notional / LEVERAGE
            entry_fee = notional * FEE_RATE

            # Require margin and entry fee to be affordable.
            if margin + entry_fee > capital:
                i += 1
                continue

            if margin > capital * MAX_MARGIN_FRACTION:
                i += 1
                continue

            position = {
                "signal_time": timestamps[i],
                "entry_time": timestamps[i + 1],
                "signal": signal,
                "entry_price": float(entry_price),
                "stop_loss": float(stop_loss),
                "take_profit": float(take_profit),
                "position_size": float(size),
                "initial_margin": float(margin),
                "entry_notional": float(notional),
                "entry_fee": float(entry_fee),
                "capital_before": float(capital),
                "leverage": float(LEVERAGE),
            }

            # Entry occurs at the next candle open.
            # Check that candle for an SL/TP hit.
            i += 1
            continue

        # ==============================================
        # MANAGE OPEN POSITION
        # ==============================================
        signal = position["signal"]
        entry = position["entry_price"]
        size = position["position_size"]
        sl = position["stop_loss"]
        tp = position["take_profit"]

        high = highs[i]
        low = lows[i]
        candle_open = opens[i]

        if (
            not all(pd.notna(x) for x in [high, low, candle_open])
            or high < low
        ):
            i += 1
            continue

        exit_price = None
        exit_reason = None

        # Approximate liquidation level.
        # Not an exchange-accurate liquidation formula.
        if signal == "BUY":
            liquidation_price = entry * (
                1 - 1 / LEVERAGE + MAINTENANCE_MARGIN_RATE
            )

            liquidation_hit = low <= liquidation_price
            stop_hit = low <= sl
            target_hit = high >= tp
        else:
            liquidation_price = entry * (
                1 + 1 / LEVERAGE - MAINTENANCE_MARGIN_RATE
            )

            liquidation_hit = high >= liquidation_price
            stop_hit = high >= sl
            target_hit = low <= tp

        # If the candle opens beyond a stop or liquidation
        # level, use the opening price as a conservative
        # approximation of the available exit price.
        if signal == "BUY" and candle_open < liquidation_price:
            exit_price = candle_open
            exit_reason = "LIQUIDATION"

        elif signal == "SELL" and candle_open > liquidation_price:
            exit_price = candle_open
            exit_reason = "LIQUIDATION"

        elif signal == "BUY" and candle_open < sl:
            exit_price = candle_open
            exit_reason = "STOP_LOSS"

        elif signal == "SELL" and candle_open > sl:
            exit_price = candle_open
            exit_reason = "STOP_LOSS"

        elif liquidation_hit:
            exit_price = liquidation_price
            exit_reason = "LIQUIDATION"

        elif stop_hit:
            exit_price = sl
            exit_reason = "STOP_LOSS"

        elif target_hit:
            exit_price = tp
            exit_reason = "TAKE_PROFIT"

        # Close any remaining position at the final candle.
        if exit_price is None and i == n - 1:
            exit_price = closes[i]
            exit_reason = "END_OF_DATA"

        # ==============================================
        # SETTLE TRADE
        # ==============================================
        if exit_price is not None:

            raw_exit = float(exit_price)

            # Adverse exit slippage.
            if signal == "BUY":
                exit_price = raw_exit * (1 - SLIPPAGE_RATE)
                gross_pnl = (exit_price - entry) * size
            else:
                exit_price = raw_exit * (1 + SLIPPAGE_RATE)
                gross_pnl = (entry - exit_price) * size

            exit_fee = exit_price * size * FEE_RATE
            entry_fee = position["entry_fee"]
            total_fees = entry_fee + exit_fee
            net_pnl = gross_pnl - total_fees

            capital_before = position["capital_before"]
            capital = capital_before + net_pnl

            # Simplified assumption: cap account losses at zero
            # on liquidation. Real exchanges can differ.
            if exit_reason == "LIQUIDATION":
                capital = max(0.0, capital)

            trades.append({
                "signal_time": position["signal_time"],
                "entry_time": position["entry_time"],
                "exit_time": timestamps[i],
                "signal": signal,
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit": tp,
                "exit_price": exit_price,
                "position_size": size,
                "leverage": position["leverage"],
                "initial_margin": position["initial_margin"],
                "entry_notional": position["entry_notional"],
                "gross_pnl": gross_pnl,
                "entry_fee": entry_fee,
                "exit_fee": exit_fee,
                "total_fees": total_fees,
                "pnl": net_pnl,
                "capital_before": capital_before,
                "capital_after": capital,
                "exit_reason": exit_reason,
            })

            position = None

            if capital <= 0:
                break

        i += 1

    return pd.DataFrame(trades)

