from strategy.database.db_connection import get_connection


def create_tables():
    """Create the database tables for crypto research."""

    with get_connection() as conn:

        # 1. Historical market candles
        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL,
                UNIQUE(symbol, timeframe, timestamp)
            )
        """)

        # 2. Trading signals
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trading_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                signal TEXT NOT NULL,
                ema20 REAL,
                ema50 REAL,
                ema200 REAL,
                rsi REAL,
                atr REAL
            )
        """)

        # 3. Backtest runs
        conn.execute("""
            CREATE TABLE IF NOT EXISTS backtest_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                initial_capital REAL,
                final_capital REAL,
                total_trades INTEGER,
                win_rate REAL,
                net_pnl REAL,
                profit_factor REAL,
                max_drawdown REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4. Individual trades
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backtest_run_id INTEGER,
                signal_time TEXT,
                entry_time TEXT,
                exit_time TEXT,
                signal TEXT,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                exit_price REAL,
                position_size REAL,
                leverage REAL,
                initial_margin REAL,
                gross_pnl REAL,
                entry_fee REAL,
                exit_fee REAL,
                total_fees REAL,
                pnl REAL,
                capital_before REAL,
                capital_after REAL,
                exit_reason TEXT,
                FOREIGN KEY(backtest_run_id)
                    REFERENCES backtest_runs(id)
            )
        """)

        # 5. Strategy comparison
        conn.execute("""
            CREATE TABLE IF NOT EXISTS strategy_comparison (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backtest_run_id INTEGER,
                strategy_name TEXT NOT NULL,
                total_trades INTEGER,
                win_rate REAL,
                net_pnl REAL,
                profit_factor REAL,
                max_drawdown REAL,
                FOREIGN KEY(backtest_run_id)
                    REFERENCES backtest_runs(id)
            )
        """)

    print("Database tables created successfully!")


if __name__ == "__main__":
    create_tables()

