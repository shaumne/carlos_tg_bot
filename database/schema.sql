-- Telegram Trading Bot Database Schema
-- Version: 1.0.0

-- Takip edilen coinler
CREATE TABLE IF NOT EXISTS watched_coins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT UNIQUE NOT NULL,
    formatted_symbol TEXT NOT NULL, -- BTC_USDT format
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    custom_settings TEXT, -- JSON format for coin-specific settings
    created_by TEXT DEFAULT 'system',
    UNIQUE(symbol, formatted_symbol)
);

-- Aktif pozisyonlar
CREATE TABLE IF NOT EXISTS active_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    formatted_symbol TEXT NOT NULL,
    side TEXT NOT NULL, -- BUY/SELL
    entry_price REAL NOT NULL,
    quantity REAL NOT NULL,
    stop_loss REAL,
    take_profit REAL,
    order_id TEXT UNIQUE,
    tp_order_id TEXT,
    sl_order_id TEXT,
    highest_price REAL, -- For trailing stop
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'ACTIVE', -- ACTIVE, FILLED, CANCELLED, CLOSED
    notes TEXT,
    FOREIGN KEY (symbol) REFERENCES watched_coins(symbol)
);

-- İşlem geçmişi
CREATE TABLE IF NOT EXISTS trade_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    formatted_symbol TEXT NOT NULL,
    action TEXT NOT NULL, -- BUY/SELL
    price REAL NOT NULL,
    quantity REAL NOT NULL,
    order_id TEXT,
    trade_id TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pnl REAL DEFAULT 0,
    fees REAL DEFAULT 0,
    execution_type TEXT, -- MARKET, LIMIT, STOP_LOSS, TAKE_PROFIT
    notes TEXT,
    position_id INTEGER,
    FOREIGN KEY (position_id) REFERENCES active_positions(id)
);

-- Sinyal geçmişi
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    formatted_symbol TEXT NOT NULL,
    signal_type TEXT NOT NULL, -- BUY/SELL/WAIT
    price REAL NOT NULL,
    confidence REAL DEFAULT 0.5, -- 0-1 arası
    rsi_value REAL,
    atr_value REAL,
    ma_signal TEXT,
    ema_signal TEXT,
    indicators TEXT, -- JSON format with all technical indicators
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed BOOLEAN DEFAULT FALSE,
    execution_timestamp TIMESTAMP,
    execution_price REAL,
    notes TEXT
);

-- Bot kullanıcıları (güvenlik için)
CREATE TABLE IF NOT EXISTS bot_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    is_authorized BOOLEAN DEFAULT FALSE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    settings TEXT -- JSON format
);

-- Bot ayarları
CREATE TABLE IF NOT EXISTS bot_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    data_type TEXT DEFAULT 'string', -- string, number, boolean, json
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT
);

-- Sistem logları
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL, -- INFO, WARNING, ERROR, CRITICAL
    module TEXT NOT NULL,
    message TEXT NOT NULL,
    details TEXT, -- JSON format for additional details
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    telegram_id INTEGER
);

-- Risk yönetimi metrikleri
CREATE TABLE IF NOT EXISTS risk_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    volatility REAL,
    atr_value REAL,
    max_position_size REAL,
    current_exposure REAL,
    risk_score REAL, -- 0-10 arası
    notes TEXT,
    UNIQUE(symbol, date)
);

-- İndeksler
CREATE INDEX IF NOT EXISTS idx_watched_coins_symbol ON watched_coins(symbol);
CREATE INDEX IF NOT EXISTS idx_watched_coins_active ON watched_coins(is_active);
CREATE INDEX IF NOT EXISTS idx_active_positions_symbol ON active_positions(symbol);
CREATE INDEX IF NOT EXISTS idx_active_positions_status ON active_positions(status);
CREATE INDEX IF NOT EXISTS idx_trade_history_symbol ON trade_history(symbol);
CREATE INDEX IF NOT EXISTS idx_trade_history_timestamp ON trade_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);
CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp);
CREATE INDEX IF NOT EXISTS idx_signals_executed ON signals(executed);
CREATE INDEX IF NOT EXISTS idx_bot_users_telegram_id ON bot_users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);

-- Default ayarlar
INSERT OR IGNORE INTO bot_settings (key, value, description, data_type) VALUES
('trade_amount', '10.0', 'Default trade amount in USDT', 'number'),
('max_positions', '5', 'Maximum concurrent positions', 'number'),
('risk_per_trade', '2.0', 'Maximum risk per trade as percentage', 'number'),
('atr_period', '14', 'ATR calculation period', 'number'),
('atr_multiplier', '2.0', 'ATR multiplier for stop loss', 'number'),
('rsi_oversold', '30', 'RSI oversold threshold', 'number'),
('rsi_overbought', '70', 'RSI overbought threshold', 'number'),
('signal_check_interval', '30', 'Signal check interval in seconds', 'number'),
('enable_auto_trading', 'false', 'Enable automatic trade execution', 'boolean'),
('enable_notifications', 'true', 'Enable telegram notifications', 'boolean'),
('notification_level', 'all', 'Notification level: all, signals, trades, errors', 'string'),
('timezone', 'UTC', 'Bot timezone', 'string'),
('api_rate_limit', '10', 'API calls per minute limit', 'number'),
('backup_interval', '3600', 'Database backup interval in seconds', 'number');

-- Trigger'lar
-- Active positions için updated_at otomatik güncelleme
CREATE TRIGGER IF NOT EXISTS update_active_positions_timestamp 
    AFTER UPDATE ON active_positions
    FOR EACH ROW
BEGIN
    UPDATE active_positions SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Trade history kaydında PnL hesaplama trigger'ı
CREATE TRIGGER IF NOT EXISTS calculate_pnl 
    AFTER INSERT ON trade_history
    FOR EACH ROW
    WHEN NEW.action = 'SELL'
BEGIN
    UPDATE trade_history 
    SET pnl = (
        SELECT 
            (NEW.price - ap.entry_price) * NEW.quantity - NEW.fees
        FROM active_positions ap 
        WHERE ap.id = NEW.position_id
    )
    WHERE id = NEW.id;
END;
