# 🤖 Telegram Trading Bot

Production-ready cryptocurrency trading bot that operates entirely through Telegram. Complete replacement for Google Sheets-based trading systems with advanced technical analysis, automated trading, and comprehensive portfolio management.

## ✨ Features

### 🔥 Core Features
- **📊 Real-time Technical Analysis** - RSI, ATR, MACD, Bollinger Bands, Stochastic
- **🤖 Automated Trading** - Buy/sell execution with risk management
- **📱 Telegram Dashboard** - Complete control through interactive chat interface  
- **💰 Portfolio Management** - Live P&L tracking and position monitoring
- **🔔 Smart Notifications** - Real-time alerts for signals, trades, and system events
- **🛡️ Risk Management** - ATR-based stop loss, take profit, and position sizing

### 💡 Advanced Features
- **👥 Multi-user Support** - Authorization system with admin controls
- **🔐 Security First** - Encrypted credentials, rate limiting, audit logs
- **📈 Signal Generation** - AI-powered technical analysis with confidence scoring
- **🎯 Precision Trading** - Optimized quantity formatting for different cryptocurrencies
- **📊 Performance Analytics** - Detailed trading statistics and health monitoring
- **💾 Data Persistence** - SQLite database with automatic backups

### 🎨 User Experience
- **Interactive Menus** - Button-based navigation for ease of use
- **Real-time Updates** - Live price feeds and portfolio monitoring
- **Conversation Flow** - Natural chat interactions for complex operations
- **Admin Panel** - Advanced system management for administrators
- **Health Monitoring** - Automatic system health checks and alerts

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│           TELEGRAM INTERFACE               │
├─────────────────────────────────────────────┤
│  🤖 Bot Core (telegram_bot/bot_core.py)    │
│  ├── Command Handlers                      │
│  ├── Callback Queries                      │
│  ├── Interactive Menus                     │
│  └── User Session Management               │
├─────────────────────────────────────────────┤
│  📊 Signal Engine (signals/signal_engine.py) │
│  ├── Technical Analysis                    │
│  ├── Market Data Provider                  │
│  ├── Signal Generation                     │
│  └── Risk Assessment                       │
├─────────────────────────────────────────────┤
│  💱 Exchange API (exchange/crypto_exchange_api.py) │
│  ├── Crypto.com Integration               │
│  ├── Order Management                      │
│  ├── Balance Tracking                      │
│  └── Trade Execution                       │
├─────────────────────────────────────────────┤
│  🗄️ Database Layer (database/database_manager.py) │
│  ├── SQLite Storage                        │
│  ├── Trade History                         │
│  ├── Signal Archive                        │
│  └── User Management                       │
├─────────────────────────────────────────────┤
│  ⚙️ Configuration (config/config.py)       │
│  ├── Environment Variables                 │
│  ├── Settings Management                   │
│  ├── Security Configuration               │
│  └── Validation System                     │
└─────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Prerequisites

- **Python 3.8+** 
- **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather))
- **Crypto.com Exchange API** credentials
- **System Requirements**: 1GB RAM, 10GB storage

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/telegram-trading-bot.git
cd telegram-trading-bot

# Install dependencies
pip install -r requirements.txt

# Create environment configuration
cp env.example .env
```

### 3. Configuration

Edit `.env` file with your credentials:

```bash
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
TELEGRAM_AUTHORIZED_USERS=123456789,987654321

# Exchange Configuration  
CRYPTO_API_KEY=your_api_key_here
CRYPTO_API_SECRET=your_api_secret_here

# Trading Settings
TRADE_AMOUNT=10.0
MAX_POSITIONS=5
ENABLE_AUTO_TRADING=false
ENABLE_PAPER_TRADING=true

# Risk Management
RISK_PER_TRADE=2.0
STOP_LOSS_PERCENTAGE=5.0
TAKE_PROFIT_PERCENTAGE=10.0
```

### 4. Testing Setup

```bash
# Run setup verification
python test_setup.py

# Expected output: All tests should pass
# ✅ Configuration - Success
# ✅ Database - Success  
# ✅ Signal Engine - Success
# ✅ Exchange API - Success (with valid credentials)
```

### 5. Start the Bot

```bash
# Start the trading bot
python main.py

# Expected output:
# 🤖 Telegram Trading Bot Starting...
# ✅ Configuration loaded and validated
# ✅ Database initialized
# ✅ Exchange API authenticated  
# ✅ Signal engine initialized
# ✅ Telegram Trading Bot started successfully!
```

## 📱 Telegram Commands

### 🔰 Basic Commands
- `/start` - Initialize bot and show welcome message
- `/help` - Show all available commands
- `/status` - Display bot status and system information
- `/health` - Perform system health check

### 💰 Portfolio & Trading  
- `/portfolio` - View active positions and P&L
- `/balance` - Check exchange account balances
- `/history` - View trading history and statistics
- `/signals` - Display recent trading signals

### 🔧 Coin Management
- `/watchlist` - Show tracked cryptocurrencies
- `/add_coin [SYMBOL]` - Add coin to watchlist (e.g., `/add_coin BTC`)
- `/remove_coin [SYMBOL]` - Remove coin from watchlist
- `/analyze [SYMBOL]` - Perform technical analysis on specific coin

### ⚙️ Settings & Admin
- `/settings` - View and modify bot configuration
- `/admin` - Admin panel (admin users only)
- `/logs` - View system logs (admin users only)
- `/backup` - Create database backup (admin users only)

### 🎮 Interactive Features
- **Button Menus** - Use inline keyboards for navigation
- **Real-time Updates** - Refresh data with button clicks
- **Conversation Flows** - Natural chat for adding coins
- **Quick Actions** - One-click portfolio operations

## 📊 Dashboard Features

### 💹 Portfolio View
```
💰 Portfolio Report

🟢 BTC_USDT
• Entry: $45,230.50
• Current: $46,120.30  
• Quantity: 0.000221
• P&L: $0.20 (+1.97%)
• TP: $47,000.00
• SL: $44,500.00

🔴 ETH_USDT  
• Entry: $2,845.20
• Current: $2,789.50
• Quantity: 0.0035
• P&L: -$0.19 (-1.96%)
• TP: $2,950.00
• SL: $2,750.00

🟢 Total P&L: $0.01
```

### 📈 Signal Analysis
```
📊 BTC Technical Analysis

🟢 Signal: BUY
📈 Price: $45,230.50
🎯 Confidence: █████ (85%)
⚠️ Risk: LOW

📋 Technical Indicators:
• RSI: 28.5 (Oversold)
• ATR: 1,245.30
• MA20: $44,850.20
• EMA12: $45,100.10

🔍 Analysis Reasons:
• RSI oversold (28.5)
• Price above MA20 and EMA12 > MA20
• MACD bullish crossover
• High volume confirmation

📊 Market Data:
• 24h Change: +2.15%
• 24h High: $46,500.00
• 24h Low: $44,200.00
• Volume: 125,430
```

### ⚙️ Settings Panel
```
⚙️ Bot Settings

💰 Trading Settings:
• Trade Amount: 10.0 USDT
• Max Positions: 5
• Risk/Trade: 2.0%
• Auto Trading: ❌
• Paper Trading: ✅

🔔 Notifications:
• Signals: ✅
• Trades: ✅
• Errors: ✅
• System Events: ✅

🔒 Security:
• Session Timeout: 3600s
• Rate Limiting: ✅
• Audit Log: ✅
```

## 🛡️ Security Features

### 🔐 Authentication & Authorization
- **User Registration** - Automatic user database management
- **Authorization Lists** - Configurable authorized user IDs
- **Admin Controls** - Separate admin privileges and commands
- **Session Management** - Automatic session timeouts

### 🛠️ Security Measures
- **API Key Encryption** - Secure credential storage
- **Rate Limiting** - Protection against API abuse
- **Input Validation** - Comprehensive input sanitization
- **Audit Logging** - Complete activity tracking
- **Error Handling** - Graceful failure management

### 🌐 Network Security
- **HTTPS Only** - Encrypted communication
- **Webhook Support** - Secure Telegram webhook option
- **IP Whitelisting** - Optional IP address restrictions
- **Connection Pooling** - Optimized API connections

## 📈 Technical Analysis

### 📊 Supported Indicators
- **RSI** (Relative Strength Index) - Momentum oscillator
- **ATR** (Average True Range) - Volatility measurement
- **Moving Averages** - SMA and EMA trend analysis
- **Bollinger Bands** - Price volatility and mean reversion
- **MACD** - Trend following momentum indicator
- **Stochastic** - Momentum oscillator for overbought/oversold

### 🎯 Signal Generation Logic
1. **Multi-indicator Analysis** - Combines multiple technical indicators
2. **Confidence Scoring** - 0-100% confidence levels
3. **Risk Assessment** - Low/Medium/High risk categorization
4. **Market Context** - 24h price movement and volume analysis
5. **Signal Filtering** - Minimum confidence thresholds

### 📋 Signal Types
- **BUY** - Strong bullish signals (🟢)
- **SELL** - Strong bearish signals (🔴)  
- **WAIT** - Mixed or weak signals (⚪)

## 💰 Trading Features

### 🎯 Order Types
- **Market Orders** - Immediate execution at current price
- **Limit Orders** - Execution at specific price levels
- **Stop Loss** - Automatic loss limitation
- **Take Profit** - Automatic profit taking

### 📏 Position Sizing
- **Fixed USDT Amount** - Consistent trade sizing
- **Risk-based Sizing** - Position size based on risk percentage
- **Balance Checking** - Automatic balance validation
- **Precision Handling** - Coin-specific quantity formatting

### ⚡ Risk Management
- **ATR-based Stops** - Dynamic stop loss calculation
- **Trailing Stops** - Profit protection with upside capture
- **Maximum Positions** - Portfolio diversification limits
- **Drawdown Protection** - Maximum loss thresholds

## 🗄️ Data Management

### 💾 Database Schema
- **Watched Coins** - Cryptocurrency tracking list
- **Active Positions** - Current trading positions
- **Trade History** - Complete transaction records
- **Signal Archive** - Historical signal data
- **User Management** - Authorization and activity logs
- **System Logs** - Application event tracking

### 🔄 Data Operations
- **Automatic Backups** - Scheduled database backups
- **Data Retention** - Configurable data cleanup policies
- **Export Capabilities** - Trade history export functionality
- **Migration Support** - Database schema updates

## ⚙️ Configuration

### 🔧 Environment Variables

#### Telegram Settings
```bash
TELEGRAM_BOT_TOKEN=           # Bot token from @BotFather
TELEGRAM_CHAT_ID=             # Your Telegram chat ID
TELEGRAM_AUTHORIZED_USERS=    # Comma-separated user IDs
TELEGRAM_ADMIN_USERS=         # Admin user IDs
```

#### Exchange Settings
```bash
CRYPTO_API_KEY=               # Crypto.com API key
CRYPTO_API_SECRET=            # Crypto.com API secret
CRYPTO_TIMEOUT=30             # API timeout in seconds
CRYPTO_RATE_LIMIT=10          # API calls per minute
```

#### Trading Settings
```bash
TRADE_AMOUNT=10.0             # Trade amount in USDT
MAX_POSITIONS=5               # Maximum concurrent positions
RISK_PER_TRADE=2.0            # Risk percentage per trade
ENABLE_AUTO_TRADING=false     # Enable automated trading
ENABLE_PAPER_TRADING=true     # Enable paper trading mode
```

#### Technical Analysis
```bash
ATR_PERIOD=14                 # ATR calculation period
ATR_MULTIPLIER=2.0            # ATR multiplier for stops
RSI_PERIOD=14                 # RSI calculation period
RSI_OVERSOLD=30.0             # RSI oversold threshold
RSI_OVERBOUGHT=70.0           # RSI overbought threshold
```

#### System Settings
```bash
LOG_LEVEL=INFO                # Logging level
LOG_FILE=logs/trading_bot.log # Log file path
DB_PATH=data/trading_bot.db   # Database file path
BACKUP_ENABLED=true           # Enable automatic backups
```

### 📝 Configuration Files
- **config/config.py** - Main configuration manager
- **env.example** - Environment variable template
- **.env** - Your environment configuration (create from example)

## 🔧 Development

### 🛠️ Project Structure
```
telegram-trading-bot/
├── 📁 config/                 # Configuration management
│   └── config.py             # Main config manager
├── 📁 database/               # Database layer
│   ├── schema.sql            # Database schema
│   └── database_manager.py   # Database operations
├── 📁 exchange/               # Exchange integration
│   └── crypto_exchange_api.py # Crypto.com API adapter
├── 📁 signals/                # Signal generation
│   └── signal_engine.py      # Technical analysis engine
├── 📁 telegram_bot/           # Telegram bot core
│   └── bot_core.py           # Main bot implementation
├── 📁 utils/                  # Utility functions
│   └── logging_setup.py      # Logging configuration
├── 📁 data/                   # Database files
├── 📁 logs/                   # Log files
├── 📁 backups/               # Database backups
├── main.py                   # Application entry point
├── test_setup.py             # Setup verification script
├── requirements.txt          # Python dependencies
├── env.example              # Environment template
└── README.md                # This documentation
```

### 🧪 Testing
```bash
# Run setup tests
python test_setup.py

# Test individual components
python -m pytest tests/ -v

# Test with paper trading
ENABLE_PAPER_TRADING=true python main.py
```

### 🐛 Debugging
```bash
# Enable debug logging
LOG_LEVEL=DEBUG python main.py

# Check logs
tail -f logs/trading_bot.log

# Database inspection
sqlite3 data/trading_bot.db ".tables"
```

## 📋 Requirements

### 🐍 Python Dependencies
```
python-dotenv>=1.0.0          # Environment configuration
python-telegram-bot>=20.0     # Telegram bot framework
requests>=2.31.0              # HTTP client
aiohttp>=3.8.0                # Async HTTP client
numpy>=1.24.0                 # Numerical computing
pandas>=2.0.0                 # Data analysis
ccxt>=4.0.0                   # Cryptocurrency exchange library
openpyxl>=3.1.0               # Excel file support
```

### 🔗 External Dependencies
- **Telegram Bot API** - Message handling and user interface
- **Crypto.com Exchange API** - Trading and market data
- **Market Data Providers** - CCXT for price feeds
- **SQLite** - Local database (included with Python)

### 💻 System Requirements
- **Operating System**: Linux, macOS, Windows
- **Python**: 3.8 or higher
- **Memory**: 1GB RAM minimum, 2GB recommended
- **Storage**: 10GB free space for database and logs
- **Network**: Stable internet connection for API access

## 🚨 Important Notes

### ⚠️ Trading Risks
- **Real Money**: This bot trades with real cryptocurrency
- **Market Risk**: Cryptocurrency markets are highly volatile
- **Technical Risk**: Software bugs could cause trading losses
- **API Risk**: Exchange API issues could affect operations

### 🛡️ Safety Recommendations
1. **Start with Paper Trading** - Test thoroughly before live trading
2. **Use Small Amounts** - Start with minimal trade sizes
3. **Monitor Actively** - Keep track of bot performance
4. **Set Stop Losses** - Always use risk management
5. **Keep Backups** - Regular database and configuration backups

### 📞 Support & Maintenance
- **Regular Updates** - Keep dependencies updated
- **Monitor Logs** - Check logs for errors and warnings
- **Database Maintenance** - Regular cleanup and optimization
- **Security Updates** - Update API keys and credentials periodically

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. **Fork the Repository**
2. **Create Feature Branch** (`git checkout -b feature/amazing-feature`)
3. **Commit Changes** (`git commit -m 'Add amazing feature'`)
4. **Push to Branch** (`git push origin feature/amazing-feature`)
5. **Open Pull Request**

### 📝 Development Guidelines
- **Code Style**: Follow PEP 8 Python style guide
- **Testing**: Add tests for new features
- **Documentation**: Update README and code comments
- **Security**: Follow security best practices

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚡ Quick Support

### 🆘 Common Issues
- **Bot not responding**: Check Telegram token and chat ID
- **API errors**: Verify exchange API credentials
- **Database errors**: Check file permissions and disk space
- **Signal issues**: Verify internet connection and market data

### 🔧 Quick Fixes
```bash
# Reset database
rm data/trading_bot.db
python main.py

# Clear logs
rm logs/*.log

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### 📞 Getting Help
1. **Check Logs** - Review logs/trading_bot.log for errors
2. **Run Health Check** - Use `/health` command in Telegram
3. **Test Setup** - Run `python test_setup.py`
4. **Discord/Telegram** - Join our community channels

---

**🚀 Ready to start? Copy `env.example` to `.env`, configure your settings, and run `python main.py`!**

**⚠️ Remember: Start with paper trading and small amounts. Never risk more than you can afford to lose.**
