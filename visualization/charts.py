import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots



def plot_price_signals(df, trades_df=None, symbol="BTCUSDT"):
    """
    Interactive trading chart:
    Candlesticks, EMA 20/50/200, BUY/SELL signals,
    trade entries/exits and volume.
    """

    df = df.copy()

    required = {
        "timestamp", "open", "high", "low",
        "close", "volume", "EMA_20", "EMA_50",
        "EMA_200", "Signal"
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing chart columns: {sorted(missing)}"
        )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"], utc=True, errors="coerce"
    )

    df = (
        df.dropna(subset=["timestamp", "open", "high", "low", "close"])
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.75, 0.25],
        subplot_titles=(
            f"{symbol} Price, EMA & Trading Signals",
            "Trading Volume"
        )
    )

    # Candlestick price chart
    fig.add_trace(
        go.Candlestick(
            x=df["timestamp"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price"
        ),
        row=1,
        col=1
    )

    # EMA indicators
    for column, label in [
        ("EMA_20", "EMA 20"),
        ("EMA_50", "EMA 50"),
        ("EMA_200", "EMA 200"),
    ]:
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=df[column],
                mode="lines",
                name=label,
                line={"width": 1.3}
            ),
            row=1,
            col=1
        )

    # BUY signals
    buy = df[df["Signal"] == "BUY"]

    fig.add_trace(
        go.Scatter(
            x=buy["timestamp"],
            y=buy["low"],
            mode="markers",
            name="BUY Signal",
            marker={
                "symbol": "triangle-up",
                "size": 11,
                "color": "green"
            },
            hovertemplate=(
                "BUY<br>%{x}<br>"
                "Price: %{y:.4f}<extra></extra>"
            )
        ),
        row=1,
        col=1
    )

    # SELL signals
    sell = df[df["Signal"] == "SELL"]

    fig.add_trace(
        go.Scatter(
            x=sell["timestamp"],
            y=sell["high"],
            mode="markers",
            name="SELL Signal",
            marker={
                "symbol": "triangle-down",
                "size": 11,
                "color": "red"
            },
            hovertemplate=(
                "SELL<br>%{x}<br>"
                "Price: %{y:.4f}<extra></extra>"
            )
        ),
        row=1,
        col=1
    )

    # Actual completed trade entries and exits
    if trades_df is not None and not trades_df.empty:
        trades = trades_df.copy()

        for column in ["entry_time", "exit_time"]:
            trades[column] = pd.to_datetime(
                trades[column],
                utc=True,
                errors="coerce"
            )

        trades["pnl"] = pd.to_numeric(
            trades["pnl"], errors="coerce"
        )

        buy_trades = trades[trades["signal"] == "BUY"]
        sell_trades = trades[trades["signal"] == "SELL"]

        fig.add_trace(
            go.Scatter(
                x=buy_trades["entry_time"],
                y=buy_trades["entry_price"],
                mode="markers",
                name="BUY Entry",
                marker={"symbol": "circle", "size": 8},
            ),
            row=1,
            col=1
        )

        fig.add_trace(
            go.Scatter(
                x=sell_trades["entry_time"],
                y=sell_trades["entry_price"],
                mode="markers",
                name="SELL Entry",
                marker={"symbol": "circle", "size": 8},
            ),
            row=1,
            col=1
        )

        winners = trades[trades["pnl"] > 0]
        losers = trades[trades["pnl"] < 0]

        fig.add_trace(
            go.Scatter(
                x=winners["exit_time"],
                y=winners["exit_price"],
                mode="markers",
                name="Winning Exit",
                marker={"symbol": "x", "size": 9, "color": "green"},
                customdata=winners[["pnl"]].to_numpy(),
                hovertemplate=(
                    "Winning Exit<br>%{x}<br>"
                    "Price: %{y:.4f}<br>"
                    "PnL: %{customdata[0]:.2f}"
                    "<extra></extra>"
                )
            ),
            row=1,
            col=1
        )

        fig.add_trace(
            go.Scatter(
                x=losers["exit_time"],
                y=losers["exit_price"],
                mode="markers",
                name="Losing Exit",
                marker={"symbol": "x", "size": 9, "color": "red"},
                customdata=losers[["pnl"]].to_numpy(),
                hovertemplate=(
                    "Losing Exit<br>%{x}<br>"
                    "Price: %{y:.4f}<br>"
                    "PnL: %{customdata[0]:.2f}"
                    "<extra></extra>"
                )
            ),
            row=1,
            col=1
        )

    # Volume chart
    fig.add_trace(
        go.Bar(
            x=df["timestamp"],
            y=df["volume"],
            name="Volume",
            opacity=0.6
        ),
        row=2,
        col=1
    )

    fig.update_layout(
        title=f"{symbol} — Interactive Strategy Chart",
        template="plotly_dark",
        height=850,
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        legend={
            "orientation": "h",
            "y": 1.02,
            "x": 0
        }
    )

    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    fig.update_xaxes(title_text="Time", row=2, col=1)

    fig.show()




def plot_equity_curve(
    trades_df,
    initial_capital
):
    """
    Plot strategy equity curve.
    """

    if trades_df.empty:
        print("No trades available for equity curve.")
        return

    equity = pd.Series(
        [initial_capital]
        + trades_df["capital_after"].tolist()
    )

    plt.figure(figsize=(14, 6))

    plt.plot(
        equity,
        linewidth=2
    )

    plt.title(
        "Strategy Equity Curve"
    )

    plt.xlabel("Trade Number")
    plt.ylabel("Account Equity")

    plt.grid(
        True,
        alpha=0.3
    )

    plt.tight_layout()

    plt.show()


def plot_drawdown(
    trades_df,
    initial_capital
):
    """
    Plot strategy drawdown.
    """

    if trades_df.empty:
        print("No trades available for drawdown.")
        return

    equity = pd.Series(
        [initial_capital]
        + trades_df["capital_after"].tolist()
    )

    running_peak = equity.cummax()

    drawdown_pct = (
        (equity - running_peak)
        / running_peak
        * 100
    )

    plt.figure(figsize=(14, 6))

    plt.plot(
        drawdown_pct,
        linewidth=2
    )

    plt.title(
        "Strategy Drawdown"
    )

    plt.xlabel("Trade Number")
    plt.ylabel("Drawdown %")

    plt.grid(
        True,
        alpha=0.3
    )

    plt.tight_layout()

    plt.show()


def plot_volume(df):
    """
    Plot trading volume and volume moving average.
    """

    df = df.copy()

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        utc=True
    )

    plt.figure(figsize=(16, 6))

    plt.bar(
        df["timestamp"],
        df["volume"],
        width=0.003,
        alpha=0.6,
        label="Volume"
    )

    if "Volume_MA" in df.columns:

        plt.plot(
            df["timestamp"],
            df["Volume_MA"],
            linewidth=1.5,
            label="Volume MA"
        )

    plt.title(
        "BTCUSDT Trading Volume"
    )

    plt.xlabel("Time")
    plt.ylabel("Volume")

    plt.legend()

    plt.grid(
        True,
        alpha=0.3
    )

    plt.tight_layout()

    plt.show()
    

def generate_tradingview_style_dashboard(
    df,
    trades_df,
    lookback_candles=3000,
):
    """
    Create a TradingView-style multi-symbol research dashboard.

    Strategy/backtest:
        - Remains BTCUSDT 5m + 15m.
        - Existing BUY/SELL and trade markers are shown only on BTCUSDT 5m.

    Dashboard:
        - BTCUSDT, ETHUSDT, SOLUSDT from local Binance CSV files.
        - NIFTY, BANKNIFTY, TATAMOTORS, RELIANCE, TCS and INFY
          from Yahoo Finance through yfinance.
        - Timeframes: 1m, 5m, 15m, 30m, 1H, 4H, 1D.
    """

    import json
    import webbrowser
    from pathlib import Path

    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go
    from plotly.offline.offline import get_plotlyjs

    from strategy.indicators import add_all_indicators

    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "data"
    REPORT_DIR = BASE_DIR / "reports"

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    OUTPUT_FILE = REPORT_DIR / "crypto_strategy_tradingview.html"

    TIMEFRAMES = ["1m", "5m", "15m", "30m", "1H", "4H", "1D"]

    # ============================================================
    # SYMBOLS
    # ============================================================

    CRYPTO_SYMBOLS = {
        "BTCUSDT": "BTCUSDT",
        "ETHUSDT": "ETHUSDT",
        "SOLUSDT": "SOLUSDT",
    }

    INDIA_SYMBOLS = {
        "NIFTY": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "TATAMOTORS": "TATAMOTORS.NS",
        "RELIANCE": "RELIANCE.NS",
        "TCS": "TCS.NS",
        "INFY": "INFY.NS",
    }

    # ============================================================
    # HELPERS
    # ============================================================

    def clean_number(value):
        if value is None:
            return None

        try:
            value = float(value)
        except (TypeError, ValueError):
            return None

        if not np.isfinite(value):
            return None

        return value

    def clean_values(series):
        return [clean_number(value) for value in series]

    def format_timestamp(value):
        if pd.isna(value):
            return None

        timestamp = pd.Timestamp(value)

        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize("UTC")

        timestamp = timestamp.tz_convert("Asia/Kolkata")

        return timestamp.strftime("%Y-%m-%dT%H:%M:%S%z")

    def add_indicators_safe(chart_df):
        chart_df = chart_df.copy()

        chart_df["timestamp"] = pd.to_datetime(
            chart_df["timestamp"],
            utc=True,
        )

        chart_df = chart_df.sort_values("timestamp").reset_index(drop=True)

        return add_all_indicators(chart_df)

    
    def read_crypto_csv(symbol, timeframe):
        """
        Download the latest available crypto candles from Binance.
        Save the refreshed data locally for future use.
        """

        import requests
        from pathlib import Path

        file_path = DATA_DIR / f"{symbol}_{timeframe}.csv"

        # Map dashboard timeframe to Binance interval
        interval_map = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1H": "1h",
            "4H": "4h",
            "1D": "1d",
        }

        interval = interval_map.get(timeframe)

        if interval is None:
            print(f"Unsupported timeframe: {timeframe}")
            return None

        try:
            print(
                f"Fetching latest Binance data: "
                f"{symbol} ({timeframe})"
            )

            response = requests.get(
                "https://api.binance.com/api/v3/klines",
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "limit": 1000,
                },
                timeout=20,
            )

            response.raise_for_status()
            candles = response.json()

            if not isinstance(candles, list) or not candles:
                raise ValueError("Binance returned no candle data.")

            columns = [
                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "quote_volume",
                "trades",
                "taker_buy_volume",
                "taker_buy_quote_volume",
                "ignore",
            ]

            chart_df = pd.DataFrame(
                candles,
                columns=columns,
            )

            chart_df["timestamp"] = pd.to_datetime(
                chart_df["open_time"],
                unit="ms",
                utc=True,
            )

            for column in [
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]:
                chart_df[column] = pd.to_numeric(
                    chart_df[column],
                    errors="coerce",
                )

            chart_df = chart_df[
                [
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ]
            ]

            chart_df = chart_df.dropna()
            chart_df = chart_df.sort_values(
                "timestamp"
            ).reset_index(drop=True)

            DATA_DIR.mkdir(
                parents=True,
                exist_ok=True,
            )

            chart_df.to_csv(
                file_path,
                index=False,
            )

            latest_time = chart_df["timestamp"].max()

            print(
                f"Updated {symbol} {timeframe}: "
                f"{len(chart_df)} candles"
            )
            print(f"Latest candle timestamp (UTC): {latest_time}")
            print(f"Saved: {file_path}")

            return chart_df

        except Exception as error:
            print(
                f"WARNING: Could not refresh {symbol} "
                f"{timeframe} from Binance: {error}"
            )

            # If download fails, use the existing local data.
            if file_path.exists():
                print("Using previously saved CSV data.")
                return pd.read_csv(file_path)

            return None



    def download_yahoo(symbol, yahoo_ticker, timeframe):
        """
        Download actual Indian-market data from Yahoo Finance.

        Yahoo intraday availability is limited:
            1m  -> recent few days
            5m/15m/30m -> recent weeks
            1h  -> recent history
            1D  -> long history

        4H is built locally from 1H data.
        """

        try:
            import yfinance as yf
        except ImportError:
            print(
                "WARNING: yfinance is not installed. "
                "Run: pip install yfinance"
            )
            return None

        if timeframe == "1m":
            interval = "1m"
            period = "7d"

        elif timeframe in {"5m", "15m", "30m"}:
            interval = timeframe
            period = "60d"

        elif timeframe == "1H":
            interval = "1h"
            period = "730d"

        elif timeframe == "4H":
            interval = "1h"
            period = "730d"

        elif timeframe == "1D":
            interval = "1d"
            period = "10y"

        else:
            return None

        print(
            f"Downloading Yahoo data: "
            f"{symbol} ({timeframe})"
        )

        try:
            downloaded = yf.download(
                yahoo_ticker,
                period=period,
                interval=interval,
                auto_adjust=False,
                progress=False,
                threads=False,
            )

        except Exception as error:
            print(
                f"WARNING: Yahoo download failed for "
                f"{symbol} {timeframe}: {error}"
            )
            return None

        if downloaded is None or downloaded.empty:
            print(
                f"WARNING: No Yahoo data for "
                f"{symbol} {timeframe}."
            )
            return None

        # yfinance can return MultiIndex columns.
        if isinstance(downloaded.columns, pd.MultiIndex):
            downloaded.columns = downloaded.columns.get_level_values(0)

        downloaded = downloaded.reset_index()

        timestamp_column = None

        for candidate in ["Datetime", "Date", "index"]:
            if candidate in downloaded.columns:
                timestamp_column = candidate
                break

        if timestamp_column is None:
            print(
                f"WARNING: Timestamp column not found for "
                f"{symbol} {timeframe}."
            )
            return None

        downloaded = downloaded.rename(
            columns={
                timestamp_column: "timestamp",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )

        required = ["timestamp", "open", "high", "low", "close"]

        if any(column not in downloaded.columns for column in required):
            print(
                f"WARNING: Incomplete Yahoo OHLC data for "
                f"{symbol} {timeframe}."
            )
            return None

        if "volume" not in downloaded.columns:
            downloaded["volume"] = 0

        downloaded = downloaded[
            ["timestamp", "open", "high", "low", "close", "volume"]
        ].copy()

        downloaded["timestamp"] = pd.to_datetime(
            downloaded["timestamp"],
            utc=True,
        )

        for column in ["open", "high", "low", "close", "volume"]:
            downloaded[column] = pd.to_numeric(
                downloaded[column],
                errors="coerce",
            )

        downloaded = downloaded.dropna(
            subset=["timestamp", "open", "high", "low", "close"]
        )

        downloaded = downloaded.sort_values("timestamp")

        if timeframe == "4H":
            downloaded = (
                downloaded
                .set_index("timestamp")
                .resample(
                    "4h",
                    label="left",
                    closed="left",
                )
                .agg(
                    {
                        "open": "first",
                        "high": "max",
                        "low": "min",
                        "close": "last",
                        "volume": "sum",
                    }
                )
                .dropna(subset=["open", "high", "low", "close"])
                .reset_index()
            )

        return downloaded

    def prepare_dataframe(symbol, timeframe):
        # --------------------------------------------------------
        # CRYPTO
        # --------------------------------------------------------

        if symbol in CRYPTO_SYMBOLS:
            chart_df = read_crypto_csv(
                symbol,
                timeframe,
            )

        # --------------------------------------------------------
        # INDIAN MARKET
        # --------------------------------------------------------

        else:
            chart_df = download_yahoo(
                symbol,
                INDIA_SYMBOLS[symbol],
                timeframe,
            )

        if chart_df is None or chart_df.empty:
            return None

        chart_df["timestamp"] = pd.to_datetime(
            chart_df["timestamp"],
            utc=True,
        )

        chart_df = chart_df.sort_values(
            "timestamp"
        ).reset_index(drop=True)

        # Add indicators to every chart timeframe.
        try:
            chart_df = add_indicators_safe(chart_df)
        except Exception as error:
            print(
                f"WARNING: Indicator calculation failed "
                f"for {symbol} {timeframe}: {error}"
            )
            return None

        chart_df = chart_df.tail(
            lookback_candles
        ).copy()

        return chart_df

    # ============================================================
    # PREPARE ALL SYMBOLS + TIMEFRAMES
    # ============================================================

    all_symbols = list(CRYPTO_SYMBOLS) + list(INDIA_SYMBOLS)

    market_data = {}

    for symbol in all_symbols:

        market_data[symbol] = {}

        print()
        print("=" * 60)
        print(f"Preparing chart data: {symbol}")
        print("=" * 60)

        for timeframe in TIMEFRAMES:

            try:
                chart_df = prepare_dataframe(
                    symbol,
                    timeframe,
                )
            except Exception as error:
                print(
                    f"WARNING: {symbol} {timeframe} failed: "
                    f"{error}"
                )
                continue

            if chart_df is None or chart_df.empty:
                continue

            timestamps = [
                format_timestamp(value)
                for value in chart_df["timestamp"]
            ]

            buy_x = []
            buy_y = []
            buy_info = []

            sell_x = []
            sell_y = []
            sell_info = []

            # ====================================================
            # ONLY BTCUSDT 5m HAS ACTUAL STRATEGY SIGNALS
            # ====================================================

            if (
                symbol == "BTCUSDT"
                and timeframe == "5m"
                and "Signal" in chart_df.columns
            ):

                buy_rows = chart_df[
                    chart_df["Signal"] == "BUY"
                ]

                sell_rows = chart_df[
                    chart_df["Signal"] == "SELL"
                ]

                for _, row in buy_rows.iterrows():

                    buy_x.append(
                        format_timestamp(
                            row["timestamp"]
                        )
                    )

                    buy_y.append(
                        clean_number(row["low"])
                    )

                    buy_info.append(
                        [
                            "BUY",
                            clean_number(row["close"]),
                            clean_number(row["RSI"]),
                            clean_number(row["Volume_Ratio"]),
                        ]
                    )

                for _, row in sell_rows.iterrows():

                    sell_x.append(
                        format_timestamp(
                            row["timestamp"]
                        )
                    )

                    sell_y.append(
                        clean_number(row["high"])
                    )

                    sell_info.append(
                        [
                            "SELL",
                            clean_number(row["close"]),
                            clean_number(row["RSI"]),
                            clean_number(row["Volume_Ratio"]),
                        ]
                    )

            market_data[symbol][timeframe] = {
                "timestamp": timestamps,
                "open": clean_values(chart_df["open"]),
                "high": clean_values(chart_df["high"]),
                "low": clean_values(chart_df["low"]),
                "close": clean_values(chart_df["close"]),
                "volume": clean_values(chart_df["volume"]),
                "ema20": clean_values(chart_df["EMA_20"]),
                "ema50": clean_values(chart_df["EMA_50"]),
                "ema200": clean_values(chart_df["EMA_200"]),
                "rsi": clean_values(chart_df["RSI"]),
                "atr": clean_values(chart_df["ATR"]),
                "volume_ratio": clean_values(
                    chart_df["Volume_Ratio"]
                ),
                "buy_x": buy_x,
                "buy_y": buy_y,
                "buy_info": buy_info,
                "sell_x": sell_x,
                "sell_y": sell_y,
                "sell_info": sell_info,
            }

    # ============================================================
    # BTCUSDT BACKTEST TRADE MARKERS
    # ============================================================

    trade_entry_x = []
    trade_entry_y = []
    trade_entry_info = []

    trade_exit_x = []
    trade_exit_y = []
    trade_exit_info = []

    if (
        trades_df is not None
        and not trades_df.empty
    ):

        trades_copy = trades_df.copy()

        if "entry_time" in trades_copy.columns:
            trades_copy["entry_time"] = pd.to_datetime(
                trades_copy["entry_time"],
                utc=True,
            )

        if "exit_time" in trades_copy.columns:
            trades_copy["exit_time"] = pd.to_datetime(
                trades_copy["exit_time"],
                utc=True,
            )

        for _, trade in trades_copy.iterrows():

            if (
                "entry_time" in trade
                and not pd.isna(trade["entry_time"])
            ):

                entry_time = pd.Timestamp(
                    trade["entry_time"]
                ).tz_convert(
                    "Asia/Kolkata"
                )

                trade_entry_x.append(
                    entry_time.strftime(
                        "%Y-%m-%dT%H:%M:%S%z"
                    )
                )

                trade_entry_y.append(
                    clean_number(
                        trade.get(
                            "entry_price",
                            None,
                        )
                    )
                )

                trade_entry_info.append(
                    [
                        str(
                            trade.get(
                                "signal",
                                "",
                            )
                        ),
                        clean_number(
                            trade.get(
                                "entry_price",
                                None,
                            )
                        ),
                    ]
                )

            if (
                "exit_time" in trade
                and not pd.isna(trade["exit_time"])
            ):

                exit_time = pd.Timestamp(
                    trade["exit_time"]
                ).tz_convert(
                    "Asia/Kolkata"
                )

                trade_exit_x.append(
                    exit_time.strftime(
                        "%Y-%m-%dT%H:%M:%S%z"
                    )
                )

                trade_exit_y.append(
                    clean_number(
                        trade.get(
                            "exit_price",
                            None,
                        )
                    )
                )

                trade_exit_info.append(
                    [
                        str(
                            trade.get(
                                "exit_reason",
                                "",
                            )
                        ),
                        clean_number(
                            trade.get(
                                "exit_price",
                                None,
                            )
                        ),
                        clean_number(
                            trade.get(
                                "pnl",
                                0,
                            )
                        ),
                    ]
                )

    chart_data_json = json.dumps(
        market_data,
        allow_nan=False,
    )

    trade_data_json = json.dumps(
        {
            "entry_x": trade_entry_x,
            "entry_y": trade_entry_y,
            "entry_info": trade_entry_info,
            "exit_x": trade_exit_x,
            "exit_y": trade_exit_y,
            "exit_info": trade_exit_info,
        },
        allow_nan=False,
    )

    plotly_js = get_plotlyjs()

    # ============================================================
    # HTML
    # ============================================================

    html = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Multi-Symbol Crypto & Indian Market Research</title>

<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: #131722;
    color: #d1d4dc;
    font-family: Arial, sans-serif;
    overflow: hidden;
}

.topbar {
    min-height: 55px;
    background: #131722;
    border-bottom: 1px solid #2a2e39;
    display: flex;
    align-items: center;
    padding: 0 12px;
    gap: 5px;
    flex-wrap: wrap;
}

.symbol-selector {
    min-width: 150px;
    margin-right: 10px;
}

#symbolSelect {
    background: #1e222d;
    color: white;
    border: 1px solid #363a45;
    border-radius: 5px;
    padding: 8px 10px;
    font-size: 14px;
    font-weight: bold;
    cursor: pointer;
}

.timeframe-button {
    padding: 7px 10px;
    border-radius: 5px;
    color: #b2b5be;
    cursor: pointer;
    font-size: 13px;
    font-weight: bold;
}

.timeframe-button:hover {
    background: #2a2e39;
    color: white;
}

.timeframe-button.active {
    background: #2962ff;
    color: white;
}

.live-status {
    margin-left: auto;
    color: #26a69a;
    font-size: 12px;
    white-space: nowrap;
}

.main {
    display: flex;
    height: calc(100vh - 55px);
}

.leftbar {
    width: 48px;
    background: #131722;
    border-right: 1px solid #2a2e39;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-top: 10px;
    gap: 8px;
}

.tool {
    width: 36px;
    height: 36px;
    display: flex;
    justify-content: center;
    align-items: center;
    color: #b2b5be;
    font-size: 18px;
    cursor: pointer;
    border-radius: 4px;
}

.tool:hover {
    background: #2a2e39;
    color: white;
}

.chart-area {
    flex: 1;
    min-width: 0;
    position: relative;
}

#chart {
    width: 100%;
    height: 100%;
}

.watchlist {
    width: 310px;
    background: #131722;
    border-left: 1px solid #2a2e39;
    padding: 15px;
    overflow-y: auto;
}

.watch-title {
    font-size: 17px;
    font-weight: bold;
    margin-bottom: 15px;
    color: white;
}

.watch-section {
    margin-top: 20px;
    margin-bottom: 8px;
    color: #787b86;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 0.8px;
}

.watch-symbol {
    display: flex;
    justify-content: space-between;
    padding: 9px 6px;
    border-bottom: 1px solid #2a2e39;
    cursor: pointer;
    font-size: 13px;
}

.watch-symbol:hover {
    background: #1e222d;
}

.watch-symbol.active {
    background: #2962ff22;
}

.watch-symbol-price {
    color: #d1d4dc;
}

.watch-row {
    display: grid;
    grid-template-columns: 1fr 110px;
    padding: 9px 5px;
    border-bottom: 1px solid #2a2e39;
    font-size: 13px;
}

.green {
    color: #26a69a;
}

.red {
    color: #ef5350;
}

.info-box {
    margin-top: 20px;
    padding: 10px;
    background: #1e222d;
    border-radius: 5px;
    font-size: 12px;
    line-height: 1.7;
}

.footer {
    position: fixed;
    bottom: 0;
    left: 48px;
    right: 310px;
    height: 35px;
    background: #131722;
    border-top: 1px solid #2a2e39;
    display: flex;
    align-items: center;
    padding-left: 15px;
    gap: 22px;
    font-size: 13px;
}

.footer span:hover {
    color: white;
    cursor: pointer;
}

@media (max-width: 900px) {
    .watchlist {
        width: 240px;
    }

    .footer {
        right: 240px;
    }
}
</style>
</head>

<body>

<div class="topbar">

    <div class="symbol-selector">
        <select id="symbolSelect" onchange="changeSymbol(this.value)">
            <option value="BTCUSDT">₿ BTCUSDT</option>
            <option value="ETHUSDT">Ξ ETHUSDT</option>
            <option value="SOLUSDT">◎ SOLUSDT</option>
            <option value="NIFTY">NIFTY</option>
            <option value="BANKNIFTY">BANKNIFTY</option>
            <option value="TATAMOTORS">TATAMOTORS</option>
            <option value="RELIANCE">RELIANCE</option>
            <option value="TCS">TCS</option>
            <option value="INFY">INFY</option>
        </select>
    </div>

    <div class="timeframe-button"
         data-timeframe="1m"
         onclick="changeTimeframe('1m')">1m</div>

    <div class="timeframe-button active"
         data-timeframe="5m"
         onclick="changeTimeframe('5m')">5m</div>

    <div class="timeframe-button"
         data-timeframe="15m"
         onclick="changeTimeframe('15m')">15m</div>

    <div class="timeframe-button"
         data-timeframe="30m"
         onclick="changeTimeframe('30m')">30m</div>

    <div class="timeframe-button"
         data-timeframe="1H"
         onclick="changeTimeframe('1H')">1H</div>

    <div class="timeframe-button"
         data-timeframe="4H"
         onclick="changeTimeframe('4H')">4H</div>

    <div class="timeframe-button"
         data-timeframe="1D"
         onclick="changeTimeframe('1D')">1D</div>

    <div class="live-status">
        ● MARKET DATA
    </div>

</div>

<div class="main">

    <div class="leftbar">
        <div class="tool">＋</div>
        <div class="tool">↗</div>
        <div class="tool">╱</div>
        <div class="tool">⌁</div>
        <div class="tool">T</div>
        <div class="tool">⌖</div>
        <div class="tool">▢</div>
        <div class="tool">◉</div>
        <div class="tool">⌫</div>
    </div>

    <div class="chart-area">
        <div id="chart"></div>
    </div>

    <div class="watchlist">

        <div class="watch-title" id="watch-symbol-title">
            BTCUSDT
        </div>

        <div class="watch-section">
            CRYPTO
        </div>

        <div class="watch-symbol"
             onclick="changeSymbol('BTCUSDT')"
             id="watch-BTCUSDT">
            <span>BTCUSDT</span>
            <span class="watch-symbol-price" id="price-BTCUSDT">-</span>
        </div>

        <div class="watch-symbol"
             onclick="changeSymbol('ETHUSDT')"
             id="watch-ETHUSDT">
            <span>ETHUSDT</span>
            <span class="watch-symbol-price" id="price-ETHUSDT">-</span>
        </div>

        <div class="watch-symbol"
             onclick="changeSymbol('SOLUSDT')"
             id="watch-SOLUSDT">
            <span>SOLUSDT</span>
            <span class="watch-symbol-price" id="price-SOLUSDT">-</span>
        </div>

        <div class="watch-section">
            INDIAN MARKET
        </div>

        <div class="watch-symbol"
             onclick="changeSymbol('NIFTY')"
             id="watch-NIFTY">
            <span>NIFTY</span>
            <span class="watch-symbol-price" id="price-NIFTY">-</span>
        </div>

        <div class="watch-symbol"
             onclick="changeSymbol('BANKNIFTY')"
             id="watch-BANKNIFTY">
            <span>BANKNIFTY</span>
            <span class="watch-symbol-price" id="price-BANKNIFTY">-</span>
        </div>

        <div class="watch-symbol"
             onclick="changeSymbol('TATAMOTORS')"
             id="watch-TATAMOTORS">
            <span>TATAMOTORS</span>
            <span class="watch-symbol-price" id="price-TATAMOTORS">-</span>
        </div>

        <div class="watch-symbol"
             onclick="changeSymbol('RELIANCE')"
             id="watch-RELIANCE">
            <span>RELIANCE</span>
            <span class="watch-symbol-price" id="price-RELIANCE">-</span>
        </div>

        <div class="watch-symbol"
             onclick="changeSymbol('TCS')"
             id="watch-TCS">
            <span>TCS</span>
            <span class="watch-symbol-price" id="price-TCS">-</span>
        </div>

        <div class="watch-symbol"
             onclick="changeSymbol('INFY')"
             id="watch-INFY">
            <span>INFY</span>
            <span class="watch-symbol-price" id="price-INFY">-</span>
        </div>

        <div class="watch-section">
            CURRENT CHART
        </div>

        <div class="watch-row">
            <span>Timeframe</span>
            <b id="watch-timeframe">5m</b>
        </div>

        <div class="watch-row">
            <span>Last Price</span>
            <b id="watch-price">-</b>
        </div>

        <div class="watch-row">
            <span>EMA 20</span>
            <b id="watch-ema20">-</b>
        </div>

        <div class="watch-row">
            <span>EMA 50</span>
            <b id="watch-ema50">-</b>
        </div>

        <div class="watch-row">
            <span>EMA 200</span>
            <b id="watch-ema200">-</b>
        </div>

        <div class="watch-row">
            <span>RSI</span>
            <b id="watch-rsi">-</b>
        </div>

        <div class="watch-row">
            <span>ATR</span>
            <b id="watch-atr">-</b>
        </div>

        <div class="watch-row">
            <span>Volume Ratio</span>
            <b id="watch-volume">-</b>
        </div>

        <div class="info-box">
            <b>Strategy</b>
            <br>
            BTCUSDT 5m + 15m confirmation
            <br>
            EMA 20 / 50 / 200
            <br>
            RSI + Volume
            <br>
            Risk Management
            <br><br>
            <b>Chart</b>
            <br>
            Multi-symbol
            <br>
            Timeframe independent
        </div>

    </div>
</div>

<div class="footer">
    <span onclick="setRange('1D')">1D</span>
    <span onclick="setRange('5D')">5D</span>
    <span onclick="setRange('1M')">1M</span>
    <span onclick="setRange('3M')">3M</span>
    <span onclick="setRange('6M')">6M</span>
    <span onclick="setRange('All')">All</span>
</div>

<script>

const marketData =
    __MARKET_DATA__;

const tradeData =
    __TRADE_DATA__;

let currentSymbol = "BTCUSDT";
let currentTimeframe = "5m";

function numberOrDash(value, digits = 2) {
    if (value === null || value === undefined) {
        return "-";
    }

    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "-";
    }

    return number.toFixed(digits);
}

function buildTraces(data, symbol, timeframe) {

    const traces = [];

    // ========================================================
    // CANDLES
    // ========================================================

    traces.push({
        type: "candlestick",

        x: data.timestamp,

        open: data.open,

        high: data.high,

        low: data.low,

        close: data.close,

        name: symbol,

        increasing: {
            line: {
                color: "#26a69a"
            }
        },

        decreasing: {
            line: {
                color: "#ef5350"
            }
        },

        whiskerwidth: 0.5,

        hovertemplate:
            "<b>%{x}</b>" +
            "<br>Open: %{open}" +
            "<br>High: %{high}" +
            "<br>Low: %{low}" +
            "<br>Close: %{close}" +
            "<extra></extra>"
    });

    // ========================================================
    // EMA 20
    // ========================================================

    traces.push({
        type: "scatter",
        mode: "lines",

        x: data.timestamp,
        y: data.ema20,

        name: "EMA 20",

        line: {
            width: 1.5
        }
    });

    // ========================================================
    // EMA 50
    // ========================================================

    traces.push({
        type: "scatter",
        mode: "lines",

        x: data.timestamp,
        y: data.ema50,

        name: "EMA 50",

        line: {
            width: 1.5
        }
    });

    // ========================================================
    // EMA 200
    // ========================================================

    traces.push({
        type: "scatter",
        mode: "lines",

        x: data.timestamp,
        y: data.ema200,

        name: "EMA 200",

        line: {
            width: 1.5
        }
    });

    // ========================================================
    // BUY SIGNALS
    // ONLY BTCUSDT 5m
    // ========================================================

    traces.push({
        type: "scatter",
        mode: "markers",

        x:
            symbol === "BTCUSDT" && timeframe === "5m"
                ? data.buy_x
                : [],

        y:
            symbol === "BTCUSDT" && timeframe === "5m"
                ? data.buy_y
                : [],

        name: "BUY",

        customdata:
            symbol === "BTCUSDT" && timeframe === "5m"
                ? data.buy_info
                : [],

        marker: {
            symbol: "triangle-up",
            size: 11,
            color: "#26a69a"
        },

        hovertemplate:
            "<b>BUY</b>" +
            "<br>Price: %{customdata[1]}" +
            "<br>RSI: %{customdata[2]}" +
            "<br>Volume Ratio: %{customdata[3]}" +
            "<extra></extra>"
    });

    // ========================================================
    // SELL SIGNALS
    // ONLY BTCUSDT 5m
    // ========================================================

    traces.push({
        type: "scatter",
        mode: "markers",

        x:
            symbol === "BTCUSDT" && timeframe === "5m"
                ? data.sell_x
                : [],

        y:
            symbol === "BTCUSDT" && timeframe === "5m"
                ? data.sell_y
                : [],

        name: "SELL",

        customdata:
            symbol === "BTCUSDT" && timeframe === "5m"
                ? data.sell_info
                : [],

        marker: {
            symbol: "triangle-down",
            size: 11,
            color: "#ef5350"
        },

        hovertemplate:
            "<b>SELL</b>" +
            "<br>Price: %{customdata[1]}" +
            "<br>RSI: %{customdata[2]}" +
            "<br>Volume Ratio: %{customdata[3]}" +
            "<extra></extra>"
    });

    // ========================================================
    // ACTUAL BACKTEST ENTRIES
    // ========================================================

    traces.push({
        type: "scatter",
        mode: "markers",

        x:
            symbol === "BTCUSDT" && timeframe === "5m"
                ? tradeData.entry_x
                : [],

        y:
            symbol === "BTCUSDT" && timeframe === "5m"
                ? tradeData.entry_y
                : [],

        name: "Trade Entry",

        marker: {
            symbol: "circle",
            size: 7
        },

        customdata:
            symbol === "BTCUSDT" && timeframe === "5m"
                ? tradeData.entry_info
                : [],

        hovertemplate:
            "<b>TRADE ENTRY</b>" +
            "<br>Signal: %{customdata[0]}" +
            "<br>Price: %{customdata[1]}" +
            "<extra></extra>"
    });

    // ========================================================
    // ACTUAL BACKTEST EXITS
    // ========================================================

    traces.push({
        type: "scatter",
        mode: "markers",

        x:
            symbol === "BTCUSDT" && timeframe === "5m"
                ? tradeData.exit_x
                : [],

        y:
            symbol === "BTCUSDT" && timeframe === "5m"
                ? tradeData.exit_y
                : [],

        name: "Trade Exit",

        marker: {
            symbol: "x",
            size: 8
        },

        customdata:
            symbol === "BTCUSDT" && timeframe === "5m"
                ? tradeData.exit_info
                : [],

        hovertemplate:
            "<b>TRADE EXIT</b>" +
            "<br>Reason: %{customdata[0]}" +
            "<br>Price: %{customdata[1]}" +
            "<br>P&L: %{customdata[2]}" +
            "<extra></extra>"
    });

    return traces;
}

function buildLayout(symbol, timeframe) {

    return {

        paper_bgcolor: "#131722",

        plot_bgcolor: "#131722",

        font: {
            color: "#d1d4dc"
        },

        title: {
            text: symbol + "  •  " + timeframe,
            x: 0.02,
            xanchor: "left",
            font: {
                size: 15,
                color: "#d1d4dc"
            }
        },

        margin: {
            l: 10,
            r: 10,
            t: 45,
            b: 45
        },

        hovermode: "x unified",

        dragmode: "pan",

        showlegend: true,

        legend: {
            orientation: "h",
            y: 1.02,
            x: 0.25
        },

        xaxis: {
            showgrid: true,
            gridcolor: "#2a2e39",

            rangeslider: {
                visible: false
            },

            type: "date",
            fixedrange: false
        },

        yaxis: {
            showgrid: true,
            gridcolor: "#2a2e39",
            side: "right",
            fixedrange: false
        }
    };
}

function updateWatchlist(data, symbol, timeframe) {

    const lastIndex =
        data.close.length - 1;

    document.getElementById(
        "watch-symbol-title"
    ).textContent = symbol;

    document.getElementById(
        "watch-timeframe"
    ).textContent = timeframe;

    const price = data.close[lastIndex];

    document.getElementById(
        "watch-price"
    ).textContent =
        price === null || price === undefined
            ? "-"
            : Number(price).toLocaleString(
                "en-IN",
                {
                    maximumFractionDigits: 2
                }
            );

    document.getElementById(
        "watch-ema20"
    ).textContent =
        numberOrDash(data.ema20[lastIndex]);

    document.getElementById(
        "watch-ema50"
    ).textContent =
        numberOrDash(data.ema50[lastIndex]);

    document.getElementById(
        "watch-ema200"
    ).textContent =
        numberOrDash(data.ema200[lastIndex]);

    document.getElementById(
        "watch-rsi"
    ).textContent =
        numberOrDash(data.rsi[lastIndex]);

    document.getElementById(
        "watch-atr"
    ).textContent =
        numberOrDash(data.atr[lastIndex]);

    document.getElementById(
        "watch-volume"
    ).textContent =
        numberOrDash(data.volume_ratio[lastIndex]);

    // Update active watchlist row.
    document
        .querySelectorAll(".watch-symbol")
        .forEach(row => {
            row.classList.remove("active");
        });

    const activeRow =
        document.getElementById(
            "watch-" + symbol
        );

    if (activeRow) {
        activeRow.classList.add("active");
    }

    // Update prices for all symbols when data exists.
    Object.keys(marketData).forEach(
        marketSymbol => {

            const symbolData =
                marketData[marketSymbol][timeframe];

            const priceElement =
                document.getElementById(
                    "price-" + marketSymbol
                );

            if (
                !symbolData ||
                !priceElement ||
                symbolData.close.length === 0
            ) {
                if (priceElement) {
                    priceElement.textContent = "-";
                }
                return;
            }

            const last =
                symbolData.close[
                    symbolData.close.length - 1
                ];

            priceElement.textContent =
                last === null || last === undefined
                    ? "-"
                    : Number(last).toLocaleString(
                        "en-IN",
                        {
                            maximumFractionDigits: 2
                        }
                    );
        }
    );
}

function changeSymbol(symbol) {

    if (
        !marketData[symbol] ||
        !marketData[symbol][currentTimeframe]
    ) {
        alert(
            "Data not available for " +
            symbol +
            " on " +
            currentTimeframe
        );

        return;
    }

    currentSymbol = symbol;

    document.getElementById(
        "symbolSelect"
    ).value = symbol;

    renderChart();
}

function changeTimeframe(timeframe) {

    if (
        !marketData[currentSymbol] ||
        !marketData[currentSymbol][timeframe]
    ) {
        alert(
            "Data not available for " +
            currentSymbol +
            " on " +
            timeframe
        );

        return;
    }

    currentTimeframe = timeframe;

    document
        .querySelectorAll(".timeframe-button")
        .forEach(
            button => {

                button.classList.toggle(
                    "active",
                    button.dataset.timeframe === timeframe
                );
            }
        );

    renderChart();
}

function renderChart() {

    const data =
        marketData[currentSymbol][currentTimeframe];

    if (!data) {
        return;
    }

    const traces =
        buildTraces(
            data,
            currentSymbol,
            currentTimeframe
        );

    const layout =
        buildLayout(
            currentSymbol,
            currentTimeframe
        );

    Plotly.react(
        "chart",
        traces,
        layout,
        {
            responsive: true,
            displaylogo: false,
            scrollZoom: true,
            modeBarButtonsToRemove: [
                "lasso2d",
                "select2d"
            ]
        }
    );

    updateWatchlist(
        data,
        currentSymbol,
        currentTimeframe
    );
}

function setRange(range) {

    const chart =
        document.getElementById("chart");

    if (!chart) {
        return;
    }

    const now = new Date();

    let start = null;

    if (range === "1D") {
        start = new Date(
            now.getTime()
            - 24 * 60 * 60 * 1000
        );
    }

    else if (range === "5D") {
        start = new Date(
            now.getTime()
            - 5 * 24 * 60 * 60 * 1000
        );
    }

    else if (range === "1M") {
        start = new Date(
            now.getTime()
            - 30 * 24 * 60 * 60 * 1000
        );
    }

    else if (range === "3M") {
        start = new Date(
            now.getTime()
            - 90 * 24 * 60 * 60 * 1000
        );
    }

    else if (range === "6M") {
        start = new Date(
            now.getTime()
            - 180 * 24 * 60 * 60 * 1000
        );
    }

    if (start) {

        Plotly.relayout(
            "chart",
            {
                "xaxis.range": [
                    start,
                    now
                ]
            }
        );

    }

    else {

        Plotly.relayout(
            "chart",
            {
                "xaxis.autorange": true
            }
        );
    }
}

renderChart();

window.addEventListener(
    "resize",
    function() {

        Plotly.Plots.resize(
            document.getElementById("chart")
        );
    }
);

</script>

</body>
</html>
"""

    html = html.replace(
        "__MARKET_DATA__",
        chart_data_json,
    )

    html = html.replace(
        "__TRADE_DATA__",
        trade_data_json,
    )

    html = html.replace(
        "<head>",
        "<head>\n<script>"
        + plotly_js
        + "</script>",
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        file.write(html)

    print()
    print("=" * 60)
    print(
        "MULTI-SYMBOL TRADINGVIEW STYLE CHART CREATED"
    )
    print("=" * 60)

    print(
        f"Saved: {OUTPUT_FILE}"
    )

    print(
        "Symbols:"
    )

    print(
        "BTCUSDT | ETHUSDT | SOLUSDT | "
        "NIFTY | BANKNIFTY | TATAMOTORS | "
        "RELIANCE | TCS | INFY"
    )

    print(
        "Timeframes:"
    )

    print(
        "1m | 5m | 15m | 30m | 1H | 4H | 1D"
    )

    webbrowser.open(
        OUTPUT_FILE.resolve().as_uri()
    )

