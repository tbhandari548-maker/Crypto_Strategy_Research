# ==========================================
# CRYPTO STRATEGY RESEARCH CONFIGURATION
# Backtesting and research simulation only
# ==========================================

# ------------------------------------------
# Market
# ------------------------------------------

SYMBOL = "BTCUSDT"

PRIMARY_TIMEFRAME = "5min"
CONFIRMATION_TIMEFRAME = "15min"

# ------------------------------------------
# Indicators
# ------------------------------------------

EMA_FAST = 20
EMA_MEDIUM = 50
EMA_SLOW = 200

RSI_PERIOD = 14

RSI_LONG_MIN = 50
RSI_LONG_MAX = 70

RSI_SHORT_MIN = 30
RSI_SHORT_MAX = 50

ATR_PERIOD = 14
ATR_SL_MULTIPLIER = 1.5

VOLUME_LOOKBACK = 20
VOLUME_MULTIPLIER = 1.2

# ------------------------------------------
# Trading Costs
# Approximate cost per side
# ------------------------------------------

FEE_RATE = 0.0004
SLIPPAGE_RATE = 0.0002

# Funding fees are not modelled yet.
ENABLE_FUNDING_FEES = False

# ------------------------------------------
# Strategy Filters
# ------------------------------------------

ALLOW_LONG = True
ALLOW_SHORT = True

ENABLE_FVG_FILTER = True
FVG_MIN_GAP_PERCENT = 0.05

ENABLE_SESSION_FILTER = True

# All sessions use UTC.
ASIA_SESSION = ("00:00", "09:00")
LONDON_SESSION = ("07:00", "16:00")
NEW_YORK_SESSION = ("13:00", "22:00")

# ------------------------------------------
# Backtesting
# ------------------------------------------

TRADING_MODE = "BACKTEST"

INITIAL_CAPITAL = 100000

ENABLE_FVG_BACKTEST_COMPARISON = True

# ------------------------------------------
# Futures Simulation
# ------------------------------------------

LEVERAGE = 2

RISK_PER_TRADE = 0.01

MAX_MARGIN_FRACTION = 0.25

MAINTENANCE_MARGIN_RATE = 0.005

MARGIN_MODE = "ISOLATED"

# ------------------------------------------
# Research Notes
# ------------------------------------------

# Simulation only. These are not exchange guarantees.
# Funding costs are excluded until implemented.
# Exchange-specific liquidation rules must be validated
# before using this model for live trading.

RISK_REWARD_RATIO = 2.0