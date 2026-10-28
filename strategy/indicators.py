import pandas as pd
import numpy as np

from config.settings import (
    EMA_FAST,
    EMA_MEDIUM,
    EMA_SLOW,
    RSI_PERIOD,
    ATR_PERIOD,
    VOLUME_LOOKBACK,
)


def add_ema_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add EMA indicators to the dataframe.
    """

    df = df.copy()

    df[f"EMA_{EMA_FAST}"] = (
        df["close"]
        .ewm(span=EMA_FAST, adjust=False)
        .mean()
    )

    df[f"EMA_{EMA_MEDIUM}"] = (
        df["close"]
        .ewm(span=EMA_MEDIUM, adjust=False)
        .mean()
    )

    df[f"EMA_{EMA_SLOW}"] = (
        df["close"]
        .ewm(span=EMA_SLOW, adjust=False)
        .mean()
    )

    return df


def add_rsi(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate RSI using closing prices.
    """

    df = df.copy()

    delta = df["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / RSI_PERIOD,
        min_periods=RSI_PERIOD,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / RSI_PERIOD,
        min_periods=RSI_PERIOD,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    df["RSI"] = 100 - (100 / (1 + rs))

    return df


def add_atr(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Average True Range (ATR).
    """

    df = df.copy()

    previous_close = df["close"].shift(1)

    high_low = df["high"] - df["low"]

    high_previous_close = (
        df["high"] - previous_close
    ).abs()

    low_previous_close = (
        df["low"] - previous_close
    ).abs()

    true_range = pd.concat(
        [
            high_low,
            high_previous_close,
            low_previous_close,
        ],
        axis=1,
    ).max(axis=1)

    df["ATR"] = (
        true_range
        .ewm(
            alpha=1 / ATR_PERIOD,
            min_periods=ATR_PERIOD,
            adjust=False,
        )
        .mean()
    )

    return df


def add_volume_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add volume moving average and volume confirmation.
    """

    df = df.copy()

    df["Volume_MA"] = (
        df["volume"]
        .rolling(VOLUME_LOOKBACK)
        .mean()
    )

    df["Volume_Ratio"] = (
        df["volume"] / df["Volume_MA"]
    )

    return df


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all strategy indicators.
    """

    df = add_ema_indicators(df)
    df = add_rsi(df)
    df = add_atr(df)
    df = add_volume_indicators(df)

    return df