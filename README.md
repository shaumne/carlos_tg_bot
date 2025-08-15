# 🤖 Carlos Telegram Trading Bot

Advanced cryptocurrency trading bot that operates entirely through Telegram with direct Crypto.com Exchange integration. Features dynamic settings management, real-time portfolio tracking, comprehensive technical analysis, and professional-grade trading capabilities.

## ✨ Features

### 🔥 Core Features
- **📊 Real-time Technical Analysis** - RSI, ATR, MACD, Bollinger Bands, Stochastic
- **🤖 Automated Trading** - Buy/sell execution with risk management
- **📱 Interactive Telegram Dashboard** - Complete control through intuitive chat interface  
- **💰 Live Portfolio Management** - Real-time balance, P&L, and position tracking
- **📋 Active Orders & Positions** - Monitor open orders and active positions
- **📜 Exchange History** - Direct trade and order history from Crypto.com
- **🔔 Smart Notifications** - Real-time alerts for signals, trades, and system events
- **🛡️ Advanced Risk Management** - ATR-based stop loss, take profit, and position sizing

### 💡 Advanced Features
- **⚙️ Dynamic Settings Management** - JSON-based runtime configuration system
- **👥 Multi-user Support** - Authorization system with admin controls
- **🔐 Security First** - Encrypted credentials, rate limiting, audit logs
- **📈 AI-powered Signal Generation** - Technical analysis with confidence scoring
- **🎯 Precision Trading** - Optimized quantity formatting for different cryptocurrencies
- **📊 Real-time Performance Analytics** - Detailed trading statistics and health monitoring
- **💾 Database & Exchange Integration** - Seamless data flow between local DB and exchange

### 🎨 Enhanced User Experience
- **🔄 Real-time Data Sync** - All data directly from Crypto.com Exchange API
- **📱 Interactive Button Menus** - Intuitive navigation with inline keyboards
- **⚡ Live Updates** - Refresh portfolio, orders, and positions with one click
- **💬 Conversation Flows** - Natural chat interactions for complex operations
- **👑 Admin Panel** - Advanced system management for administrators
- **🏥 Health Monitoring** - Comprehensive system health checks and diagnostics

## 🏗️ Enhanced Architecture

```
┌─────────────────────────────────────────────┐
│           TELEGRAM INTERFACE               │
├─────────────────────────────────────────────┤
│  🤖 Bot Core (telegram_bot/bot_core.py)    │
│  ├── Command Handlers (/start, /portfolio) │
│  ├── Interactive Callback Queries          │
│  ├── Dynamic Settings UI                   │
│  ├── Active Orders & Positions Display     │
│  └── Message Handler & Session Management  │
├─────────────────────────────────────────────┤
│  ⚙️ Settings System (telegram_bot/settings_handlers.py) │
│  ├── JSON-based Configuration              │
│  ├── Runtime Settings Updates              │
│  ├── Input Validation & Type Conversion    │
│  └── Hot-reload Configuration              │
├─────────────────────────────────────────────┤
│  📊 Signal Engine (signals/signal_engine.py) │
│  ├── Multi-indicator Technical Analysis    │
│  ├── Real-time Market Data (CCXT)          │
│  ├── Signal Generation & Confidence        │
│  └── Risk Assessment & Filtering           │
├─────────────────────────────────────────────┤
│  💱 Exchange API (exchange/crypto_exchange_api.py) │
│  ├── Crypto.com Direct Integration         │
│  ├── Order Management (Market/Limit)       │
│  ├── Real-time Balance & Portfolio         │
│  ├── Trade History & Open Orders           │
│  ├── Position Tracking & P&L               │
│  └── Quantity Formatting & Validation      │
├─────────────────────────────────────────────┤
│  🗄️ Database Layer (database/database_manager.py) │
│  ├── SQLite Storage & Schema               │
│  ├── Settings Persistence                  │
│  ├── Signal Archive & Audit Logs           │
│  └── User Management & Authorization       │
├─────────────────────────────────────────────┤
│  ⚙️ Dynamic Configuration (config/)        │
│  ├── Environment Variables (.env)          │
│  ├── JSON Settings Schema                  │
│  ├── Runtime Settings Manager              │
│  └── Validation & Type System              │
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
git clone https://github.com/shaumne/carlos_tg_bot.git
cd carlos_tg_bot

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

## 📱 Telegram Commands & Interface

### 🔰 Basic Commands
- `/start` - Initialize bot and show welcome message with main menu
- `/help` - Show all available commands and features
- `/status` - Display bot status, system information, and health metrics
- `/health` - Perform comprehensive system health check

### 💰 Portfolio & Trading Management
- `/portfolio` - **Enhanced portfolio view** with balances, open orders, and positions
- `/balance` - Check live exchange account balances (all currencies)
- `/history` - **Direct exchange history** - trades and orders from Crypto.com
- `/signals` - Display recent trading signals with technical analysis

### 🔧 Coin & Watchlist Management
- `/watchlist` - Show tracked cryptocurrencies with analysis
- `/add_coin [SYMBOL]` - Add coin to watchlist (e.g., `/add_coin BTC`)
- `/remove_coin [SYMBOL]` - Remove coin from watchlist
- `/analyze [SYMBOL]` - Perform detailed technical analysis on specific coin

### ⚙️ Dynamic Settings & Configuration
- `/settings` - **Interactive settings panel** with JSON-based configuration
  - Real-time settings updates (no restart required for most settings)
  - Input validation and type conversion
  - Settings categories: Trading, Technical, Notifications, Security

### 👑 Admin & System Management
- `/admin` - Comprehensive admin panel (admin users only)
- `/logs` - View system logs with filtering (admin users only)
- `/backup` - Create database backup (admin users only)

### 🎮 Enhanced Interactive Features
- **📋 Active Orders Panel** - View and monitor all open orders with fill status
- **📈 Positions Panel** - Real-time position tracking with P&L calculations
- **🔄 Live Refresh Buttons** - Update data from exchange with one click
- **⚙️ Settings Conversation Flow** - Natural chat for configuration changes
- **📱 Inline Keyboards** - Intuitive button-based navigation
- **💬 Message Handlers** - Smart input processing for different contexts

## 📊 Dashboard Features

### 💹 Enhanced Portfolio Dashboard
```
💰 Portfolio Report

💵 USDT Balance: $125.50

🪙 Crypto Holdings (3)

💎 BTC
• Available: 0.002150
• Total: 0.002150
• Locked: 0.000000
• Price: $45,230.50
• Value: $97.25

💎 ETH
• Available: 0.035000
• Total: 0.035000
• Locked: 0.000000
• Price: $2,845.20
• Value: $99.58

💰 Total Portfolio Value: $322.33

📋 Open Orders (2)
🟢 BTC-USDT 🟡
• Type: BUY LIMIT
• Price: $44,500.00
• Quantity: 0.002000
• Filled: 0.000000 (0.0%)

📊 Positions (1)
🟢 ETH-USDT
• Quantity: 0.035000
• Cost: $99.58
• Open P&L: $2.15
• Session P&L: $0.75
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

### ⚙️ Dynamic Settings Management Panel
```
⚙️ Bot Settings Panel

Choose a category to configure:

💰 Trading Settings
Configure trading parameters and risk management

📊 Technical Analysis
Technical analysis and signal generation settings

🔔 Notifications
Alert and notification preferences

🔒 Security
Security and access control settings

📊 Settings Status | 📤 Export Settings | 🔄 Reset Category

---

💰 Trading Settings:
✅ Trade Amount: 25.0 USDT (Runtime Update)
✅ Max Positions: 3 (Runtime Update)  
✅ Risk Per Trade: 1.5% (Runtime Update)
✅ Auto Trading: ❌ (Runtime Update)
✅ Stop Loss: 3.0% (Runtime Update)
✅ Take Profit: 8.0% (Runtime Update)

📊 Technical Analysis:
✅ RSI Period: 14 (Runtime Update)
✅ RSI Oversold: 25.0 (Runtime Update)
✅ RSI Overbought: 75.0 (Runtime Update)
✅ ATR Period: 14 (Runtime Update)
✅ Signal Confidence: 65% (Runtime Update)

🔔 Notifications:
✅ Enable Signals: ✅ (Runtime Update)
✅ Enable Trades: ✅ (Runtime Update)
✅ Enable Errors: ✅ (Runtime Update)

Note: Settings marked with (Runtime Update) apply immediately without restart
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

### 🛠️ Enhanced Project Structure
```
carlos_tg_bot/
├── 📁 config/                     # Enhanced configuration system
│   ├── config.py                 # Main config manager
│   ├── dynamic_settings.py       # Runtime settings manager
│   └── settings_config.json      # JSON-based settings schema
├── 📁 database/                   # Database layer
│   ├── schema.sql                # Enhanced database schema
│   └── database_manager.py       # Database operations
├── 📁 exchange/                   # Direct Crypto.com integration
│   └── crypto_exchange_api.py     # Full Crypto.com API implementation
├── 📁 signals/                    # Advanced signal generation
│   └── signal_engine.py          # Multi-indicator technical analysis
├── 📁 telegram_bot/               # Enhanced Telegram interface
│   ├── bot_core.py               # Main bot with real-time features
│   └── settings_handlers.py      # Interactive settings management
├── 📁 utils/                      # Utility functions
│   └── logging_setup.py          # Advanced logging configuration
├── 📁 data/                       # Database storage
│   ├── trading_bot.db            # Main database
│   ├── demo_settings.db          # Demo configuration
│   └── test_*.db                 # Test databases
├── 📁 logs/                       # Log files
│   ├── trading_bot.log           # Main application log
│   └── test.log                  # Test execution log
├── 📁 backups/                    # Automatic backups
├── main.py                       # Application entry point
├── test_*.py                     # Comprehensive test suites
├── requirements.txt              # Enhanced Python dependencies
├── env.example                   # Environment template
└── README.md                     # This comprehensive documentation
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
# Core Libraries
python-dotenv                 # Environment configuration
dataclasses                   # Python < 3.7 compatibility

# Telegram Integration
python-telegram-bot           # Advanced Telegram bot framework
telegram                     # Telegram API

# HTTP & Networking
requests                      # HTTP client for API calls
aiohttp                       # Async HTTP client
urllib3                       # HTTP client utilities

# Database
db-sqlite3                    # Enhanced SQLite support

# Data Analysis & Computing
numpy                         # Numerical computing for technical analysis
pandas                        # Data analysis and manipulation
ccxt                          # Cryptocurrency exchange library

# File Support
openpyxl                      # Excel file support

# Development & Testing
pytest                        # Testing framework
pytest-asyncio               # Async testing support
pytest-mock                  # Mock testing utilities

# System Monitoring
psutil                        # System performance monitoring
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

## 🔥 Recent Updates & Enhancements

### ✨ Version 2.0 Features
- **🔄 Real-time Data Integration** - All portfolio, orders, and history data directly from Crypto.com Exchange
- **⚙️ Dynamic Settings System** - JSON-based configuration with hot-reload capabilities
- **📋 Active Orders & Positions** - Enhanced monitoring with detailed P&L tracking
- **💬 Improved Message Handling** - Fixed conversation state management for settings
- **🎯 Precision Trading** - Enhanced quantity formatting and validation for different cryptocurrencies
- **📊 Advanced Portfolio View** - Multi-currency balances with real-time price updates

### 🛠️ Technical Improvements
- **State Management Fix** - Resolved settings input conversation state conflicts
- **API Optimization** - Enhanced Crypto.com API integration with proper error handling
- **Validation System** - Comprehensive input validation and type conversion
- **Debug Logging** - Enhanced logging for troubleshooting and monitoring

### 🔧 Developer Experience
- **Comprehensive Documentation** - Updated README with detailed feature explanations
- **Test Suite** - Multiple test files for different components
- **Code Organization** - Modular architecture with clear separation of concerns

---

## 🚀 Quick Start Summary

1. **Clone & Install**
   ```bash
   git clone https://github.com/shaumne/carlos_tg_bot.git
   cd carlos_tg_bot
   pip install -r requirements.txt
   ```

2. **Configure**
   ```bash
   cp env.example .env
   # Edit .env with your credentials
   ```

3. **Test & Run**
   ```bash
   python test_setup.py  # Verify setup
   python main.py        # Start the bot
   ```

4. **Start Trading**
   - Begin with `/start` in Telegram
   - Configure settings via `/settings`
   - Monitor portfolio with `/portfolio`
   - View history with `/history`

---

**🚀 Ready to start? The enhanced Carlos Trading Bot is production-ready with real-time Crypto.com integration!**

**⚠️ Important: Start with paper trading mode and small amounts. Test thoroughly before live trading. Never risk more than you can afford to lose.**

**📈 Pro Tip: Use the dynamic settings system to fine-tune your trading strategy without restarting the bot!**
