import pandas as pd

from config.settings import (
    RSI_LONG_MIN,
    RSI_LONG_MAX,
    RSI_SHORT_MIN,
    RSI_SHORT_MAX,
    VOLUME_MULTIPLIER,
)

# Optional settings have defaults so this module can still be imported
# if an older settings.py does not define them.
try:
    from config.settings import (
        ALLOW_LONG,
        ALLOW_SHORT,
        ENABLE_FVG_FILTER,
        ENABLE_SESSION_FILTER,
    )
except ImportError:
    ALLOW_LONG = True
    ALLOW_SHORT = True
    ENABLE_FVG_FILTER = True
    ENABLE_SESSION_FILTER = False

try:
    from config.settings import FVG_MIN_GAP_PERCENT
except ImportError:
    FVG_MIN_GAP_PERCENT = 0.05

try:
    from config.settings import (
        ASIA_SESSION,
        LONDON_SESSION,
        NEW_YORK_SESSION,
    )
except ImportError:
    ASIA_SESSION = ("00:00", "09:00")
    LONDON_SESSION = ("07:00", "16:00")
    NEW_YORK_SESSION = ("13:00", "22:00")


# ============================================================
# 1. FAIR VALUE GAP (FVG) DETECTION
# ============================================================

def add_fvg_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect bullish and bearish Fair Value Gaps (FVGs).

    Bullish FVG:
        Low of the current candle > High of candle i-2.

    Bearish FVG:
        High of the current candle < Low of candle i-2.

    A zone is created only after the third candle is present.
    A retest is recorded only for a zone created on an earlier
    candle, avoiding same-candle formation/retest look-ahead.
    """
    required = {"high", "low", "close"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(
            f"FVG detection is missing columns: {sorted(missing)}"
        )

    df = df.copy()

    df["FVG_Type"] = "NONE"
    df["FVG_Upper"] = float("nan")
    df["FVG_Lower"] = float("nan")
    df["FVG_Gap_Percent"] = float("nan")
    df["FVG_Retest"] = False
    df["FVG_Retest_Type"] = "NONE"

    active_zones = []
    latest_zone = None

    for i in range(len(df)):
        current_high = df["high"].iloc[i]
        current_low = df["low"].iloc[i]
        current_close = df["close"].iloc[i]

        if (
            pd.isna(current_high)
            or pd.isna(current_low)
            or pd.isna(current_close)
        ):
            continue

        # A. Check zones formed on previous candles.
        retested_types = []
        remaining_zones = []

        for zone in active_zones:
            age = i - zone["formation_index"]

            if age > 500:
                continue

            # Invalidate a bullish zone if price closes below it.
            if (
                zone["type"] == "BULLISH"
                and current_close < zone["lower"]
            ):
                continue

            # Invalidate a bearish zone if price closes above it.
            if (
                zone["type"] == "BEARISH"
                and current_close > zone["upper"]
            ):
                continue

            overlaps = (
                current_low <= zone["upper"]
                and current_high >= zone["lower"]
            )

            if overlaps:
                retested_types.append(zone["type"])
                # Record the first retest only.
                continue

            remaining_zones.append(zone)

        active_zones = remaining_zones

        if retested_types:
            df.loc[df.index[i], "FVG_Retest"] = True
            # If multiple zones are retested, use the most recently
            # encountered zone type.
            df.loc[df.index[i], "FVG_Retest_Type"] = retested_types[-1]

        # B. Detect a new FVG using the current and i-2 candles.
        # New zones are added after retest checking, so they cannot
        # be retested by the same candle that formed them.
        if i >= 2 and current_close != 0:
            candle_1_high = df["high"].iloc[i - 2]
            candle_1_low = df["low"].iloc[i - 2]

            if not pd.isna(candle_1_high) and not pd.isna(candle_1_low):
                bullish_gap = current_low - candle_1_high

                if bullish_gap > 0:
                    gap_percent = bullish_gap / abs(current_close) * 100

                    if gap_percent >= FVG_MIN_GAP_PERCENT:
                        new_zone = {
                            "type": "BULLISH",
                            "upper": current_low,
                            "lower": candle_1_high,
                            "formation_index": i,
                        }
                        active_zones.append(new_zone)
                        latest_zone = new_zone

                bearish_gap = candle_1_low - current_high

                if bearish_gap > 0:
                    gap_percent = bearish_gap / abs(current_close) * 100

                    if gap_percent >= FVG_MIN_GAP_PERCENT:
                        new_zone = {
                            "type": "BEARISH",
                            "upper": candle_1_low,
                            "lower": current_high,
                            "formation_index": i,
                        }
                        active_zones.append(new_zone)
                        latest_zone = new_zone

        # Limit active zones to control memory and processing time.
        if len(active_zones) > 100:
            active_zones = active_zones[-100:]

        # C. Store the latest known zone for charting.
        if latest_zone is not None:
            df.loc[df.index[i], "FVG_Type"] = latest_zone["type"]
            df.loc[df.index[i], "FVG_Upper"] = latest_zone["upper"]
            df.loc[df.index[i], "FVG_Lower"] = latest_zone["lower"]

            if current_close != 0:
                df.loc[df.index[i], "FVG_Gap_Percent"] = (
                    (latest_zone["upper"] - latest_zone["lower"])
                    / abs(current_close)
                    * 100
                )

    return df


# ============================================================
# 2. TRADING SESSION CLASSIFICATION
# ============================================================

def get_trading_sessions(timestamp) -> str:
    """
    Classify a timestamp into UTC trading sessions.

    Sessions can overlap. For example, a timestamp can be labelled
    'ASIA+LONDON'. Timestamps are assumed to be UTC if timezone-naive.
    """
    timestamp = pd.Timestamp(timestamp)

    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")

    current_time = timestamp.strftime("%H:%M")
    sessions = []

    def is_inside_session(start, end):
        if start <= end:
            return start <= current_time < end
        # Support sessions crossing midnight.
        return current_time >= start or current_time < end

    if is_inside_session(*ASIA_SESSION):
        sessions.append("ASIA")

    if is_inside_session(*LONDON_SESSION):
        sessions.append("LONDON")

    if is_inside_session(*NEW_YORK_SESSION):
        sessions.append("NEW_YORK")

    return "+".join(sessions) if sessions else "OTHER"


# ============================================================
# 3. MAIN SIGNAL GENERATION
# ============================================================

def generate_signals(
    df_5m: pd.DataFrame,
    df_15m: pd.DataFrame,
) -> pd.DataFrame:
    """
    Generate original and FVG-enhanced signals.

    Required input columns for both dataframes:
        timestamp, open, high, low, close, volume

    Output includes:
        Signal, Signal_FVG, trend confirmation, FVG fields,
        and Trading_Session.

    Assumption:
        Input timestamps represent candle OPEN times. The backtest
        should enter no earlier than the next candle after a signal.
    """
    df_5m = df_5m.copy()
    df_15m = df_15m.copy()

    required_columns = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    for column in required_columns:
        if column not in df_5m.columns:
            raise ValueError(
                f"5-minute data is missing column: {column}"
            )
        if column not in df_15m.columns:
            raise ValueError(
                f"15-minute data is missing column: {column}"
            )

    if df_5m.empty:
        raise ValueError("5-minute data is empty.")
    if df_15m.empty:
        raise ValueError("15-minute data is empty.")

    # Normalize timestamps and sort chronologically.
    df_5m["timestamp"] = pd.to_datetime(df_5m["timestamp"], utc=True)
    df_15m["timestamp"] = pd.to_datetime(df_15m["timestamp"], utc=True)

    df_5m = (
        df_5m.sort_values("timestamp")
        .drop_duplicates(subset="timestamp")
        .reset_index(drop=True)
    )
    df_15m = (
        df_15m.sort_values("timestamp")
        .drop_duplicates(subset="timestamp")
        .reset_index(drop=True)
    )

    # Calculate indicators.
    from strategy.indicators import add_all_indicators

    df_5m = add_all_indicators(df_5m)
    df_15m = add_all_indicators(df_15m)

    # --------------------------------------------------------
    # A. 15-MINUTE CONFIRMATION (completed candles only)
    # --------------------------------------------------------
    confirmation_columns = ["EMA_20", "EMA_50", "EMA_200"]
    missing_indicators = [
        col for col in confirmation_columns if col not in df_15m.columns
    ]
    if missing_indicators:
        raise ValueError(
            "15-minute indicators missing: "
            f"{missing_indicators}. Check strategy/indicators.py."
        )

    df_15m_confirmation = df_15m[
        ["timestamp"] + confirmation_columns
    ].copy()

    df_15m_confirmation = df_15m_confirmation.rename(
        columns={
            "EMA_20": "EMA_20_15m",
            "EMA_50": "EMA_50_15m",
            "EMA_200": "EMA_200_15m",
        }
    )

    # Timestamps are candle OPEN times; confirmation is available
    # only at the 15-minute candle close.
    df_15m_confirmation["confirmation_time"] = (
        df_15m_confirmation["timestamp"] + pd.Timedelta(minutes=15)
    )

    df_15m_confirmation = df_15m_confirmation[
        [
            "confirmation_time",
            "EMA_20_15m",
            "EMA_50_15m",
            "EMA_200_15m",
        ]
    ].sort_values("confirmation_time")

    df_5m = pd.merge_asof(
        df_5m.sort_values("timestamp"),
        df_15m_confirmation,
        left_on="timestamp",
        right_on="confirmation_time",
        direction="backward",
    )

    # --------------------------------------------------------
    # B. TREND CONDITIONS
    # --------------------------------------------------------
    df_5m["Trend_15m"] = "NEUTRAL"

    long_trend = (
        (df_5m["EMA_20_15m"] > df_5m["EMA_50_15m"])
        & (df_5m["EMA_50_15m"] > df_5m["EMA_200_15m"])
    )
    short_trend = (
        (df_5m["EMA_20_15m"] < df_5m["EMA_50_15m"])
        & (df_5m["EMA_50_15m"] < df_5m["EMA_200_15m"])
    )

    df_5m.loc[long_trend, "Trend_15m"] = "BULLISH"
    df_5m.loc[short_trend, "Trend_15m"] = "BEARISH"

    required_5m_indicators = ["EMA_20", "EMA_50", "EMA_200", "RSI", "Volume_Ratio"]
    missing_5m_indicators = [
        col for col in required_5m_indicators if col not in df_5m.columns
    ]
    if missing_5m_indicators:
        raise ValueError(
            "5-minute indicators missing: "
            f"{missing_5m_indicators}. Check strategy/indicators.py."
        )

    five_min_long = (
        (df_5m["EMA_20"] > df_5m["EMA_50"])
        & (df_5m["EMA_50"] > df_5m["EMA_200"])
    )
    five_min_short = (
        (df_5m["EMA_20"] < df_5m["EMA_50"])
        & (df_5m["EMA_50"] < df_5m["EMA_200"])
    )

    volume_confirmation = df_5m["Volume_Ratio"] >= VOLUME_MULTIPLIER

    # --------------------------------------------------------
    # C. ORIGINAL STRATEGY SIGNALS
    # --------------------------------------------------------
    buy_condition = (
        five_min_long
        & long_trend
        & df_5m["RSI"].between(RSI_LONG_MIN, RSI_LONG_MAX)
        & volume_confirmation
    )
    sell_condition = (
        five_min_short
        & short_trend
        & df_5m["RSI"].between(RSI_SHORT_MIN, RSI_SHORT_MAX)
        & volume_confirmation
    )

    # Apply direction settings.
    if not ALLOW_LONG:
        buy_condition = buy_condition & False
    if not ALLOW_SHORT:
        sell_condition = sell_condition & False

    # Add session labels before applying the optional session filter.
    df_5m["Trading_Session"] = df_5m["timestamp"].apply(
        get_trading_sessions
    )

    if ENABLE_SESSION_FILTER:
        # Only allow candles that fall inside at least one configured
        # session. Overlapping sessions are allowed.
        allowed_session = df_5m["Trading_Session"] != "OTHER"
        buy_condition = buy_condition & allowed_session
        sell_condition = sell_condition & allowed_session

    df_5m["Signal"] = "NONE"
    df_5m.loc[buy_condition, "Signal"] = "BUY"
    df_5m.loc[sell_condition, "Signal"] = "SELL"

    # --------------------------------------------------------
    # D. FVG DETECTION AND FVG-ENHANCED SIGNALS
    # --------------------------------------------------------
    df_5m = add_fvg_indicators(df_5m)

    bullish_fvg_confirmation = (
        df_5m["FVG_Retest"]
        & (df_5m["FVG_Retest_Type"] == "BULLISH")
    )
    bearish_fvg_confirmation = (
        df_5m["FVG_Retest"]
        & (df_5m["FVG_Retest_Type"] == "BEARISH")
    )

    df_5m["Signal_FVG"] = "NONE"

    if ENABLE_FVG_FILTER:
        df_5m.loc[
            (df_5m["Signal"] == "BUY") & bullish_fvg_confirmation,
            "Signal_FVG",
        ] = "BUY"
        df_5m.loc[
            (df_5m["Signal"] == "SELL") & bearish_fvg_confirmation,
            "Signal_FVG",
        ] = "SELL"
    else:
        # When FVG filtering is disabled, the comparison signal mirrors
        # the original signal. The separate Signal column stays intact.
        df_5m["Signal_FVG"] = df_5m["Signal"]

    # Return rows in chronological order.
    df_5m = df_5m.sort_values("timestamp").reset_index(drop=True)

    return df_5m
