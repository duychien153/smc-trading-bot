# SMC Trading Bot v2.0 🚀# SMC Trading Bot v2.0 🚀



**Professional SMC Trading System** with clean modular architecture.**Professional Trading System** sử dụng Smart Money Concept (SMC) với kiến trúc modular.



## 🎯 **Architecture v2.0 - COMPLETE**## 🆕 Architecture v2.0 - REFACTORED



### ✨ **Implemented Features**### ✨ **Key Improvements**

- 🏗️ **Modular Design**: Clean separation of concerns- 🏗️ **Modular Design**: Tách biệt các concerns (data, strategy, risk, orders)

- 📊 **Real-time Data Feed**: Bybit API + caching + validation  - 📊 **Professional Logging**: Multi-level logging với performance metrics  

- 🧠 **SMC Strategy**: Market structure + Order blocks + FVG analysis- 🔄 **Extensible**: Dễ dàng thêm strategies và exchanges mới

- 🛡️ **Risk Management**: Position sizing + portfolio limits- 🧪 **Testable**: Clean interfaces cho unit testing

- 📋 **Order Manager**: Live + Paper trading modes- 📈 **Monitoring**: Real-time performance tracking

- 📝 **Professional Logging**: Multi-level with rotation- 🛡️ **Type Safety**: Sử dụng dataclasses và enums

- 📈 **Performance Tracking**: Real-time P&L + metrics

- 🔧 **Type Safety**: Dataclasses + enums for reliability### 📁 **New Project Structure**

```

### 📁 **Clean Project Structure**├── src/                          # 🎯 Core modules  

```│   ├── models.py                 # 📊 Data models & types

├── src/                          # 🎯 Core modules (2,934 lines total)│   ├── data_feed/               # 🔌 Market data management

│   ├── models.py                 # 📊 Type-safe data models (206 lines)│   │   └── market_data.py       # Bybit API + caching

│   ├── trading_bot.py            # 🤖 Main orchestrator (386 lines)│   ├── strategy/                # 🧠 Trading strategies

│   ├── data_feed/               # 🔌 Market data management│   │   ├── base_strategy.py     # Abstract base class  

│   │   └── market_data.py       # ✅ Bybit API + caching (293 lines)│   │   └── smc_strategy.py      # SMC implementation

│   ├── strategy/                # 🧠 Trading strategies│   ├── risk_management/         # 🛡️ Risk controls (TODO)

│   │   ├── base_strategy.py     # ✅ Abstract base (219 lines)│   ├── order_manager/           # 📋 Order execution (TODO)

│   │   └── smc_strategy.py      # ✅ SMC implementation (410 lines)│   ├── backtest/                # 📈 Historical testing (TODO)

│   ├── risk_management/         # 🛡️ Risk controls│   └── monitoring/              # 📝 Logging & metrics

│   │   └── risk_manager.py      # ✅ Position sizing + limits (397 lines)│       ├── logger.py            # Professional logging

│   ├── order_manager/           # 📋 Order execution│       └── metrics.py           # Performance tracking

│   │   └── order_manager.py     # ✅ Live + Paper trading (554 lines)├── config/                      # ⚙️ Configuration files

│   └── monitoring/              # 📝 Logging & metrics├── tests/                       # 🧪 Unit tests  

│       ├── logger.py            # ✅ Professional logging (159 lines)├── logs/                        # � Log files

│       └── metrics.py           # ✅ Performance tracking (272 lines)├── vps_bot.py                   # 🔄 Legacy bot (still running on VPS)

├── main.py                      # 🚀 Production entry point└── demo_new_architecture.py     # 🎬 Demo script

├── demo_new_architecture.py     # 🎬 Demo & testing script```

└── vps_bot_legacy_backup.py     # 💾 Legacy monolithic backup (463 lines)

```## 🚀 **Quick Start với Architecture Mới**



## 🚀 **Quick Start**### 1. **Setup Environment**

```bash

### 1. **Setup Environment**# Install dependencies

```bashpip install -r requirements.txt

# Install dependencies

pip install -r requirements.txt# Setup .env file with API credentials

cp .env.example .env

# Setup environment variables  # Edit .env with your Bybit API keys

cp .env.example .env```

# Edit .env with your Bybit API keys

```### 2. **Demo Usage**

```bash

### 2. **Run Demo (Paper Trading)**# Run architecture demo

```bashpython3 demo_new_architecture.py

# Test architecture with 2-minute live demo

python demo_new_architecture.py# Check logs

```ls logs/

```

### 3. **Production Mode**

```bash### 3. **Usage Example**

# Run production bot (requires valid .env)```python

python main.pyfrom src.data_feed.market_data import MarketDataFeed

```from src.strategy.smc_strategy import SMCStrategy



## 📊 **SMC Strategy Features**# Initialize components

data_feed = MarketDataFeed(api_key, api_secret)

### Market Structure Analysisstrategy = SMCStrategy("BTCUSDT", config)

- **Break of Structure (BOS)**: Trend continuation signals

- **Change of Character (CHoCH)**: Trend reversal detection  # Get market data  

- **Order Blocks**: Support/resistance level detectioncandles = data_feed.get_candles("BTCUSDT", "15", 100)

- **Fair Value Gaps**: Price imbalance analysismarket_data = data_feed.get_market_data("BTCUSDT")



### Confluence Scoring# Generate trading signal

- **Multi-factor Analysis**: 5+ confluence factorssignal = strategy.process_signal(candles, market_data)

- **Minimum Confidence**: 75% threshold for signals

- **Risk-Reward**: Minimum 1:2 R:R ratioif signal:

    print(f"Signal: {signal.signal_type.value}")

## 🛡️ **Risk Management**    print(f"Entry: ${signal.entry_price:.2f}")

    print(f"Confidence: {signal.confidence:.1f}%")

- **Position Sizing**: Fixed 1% risk per trade```

- **Portfolio Limits**: Max 5% total risk, 3 positions

- **Drawdown Protection**: 10% maximum decline## 🏗️ **Components**

- **Kelly Criterion**: Optional dynamic sizing

### **📊 Data Feed**

## 📈 **Architecture Benefits**- Real-time market data từ Bybit API

- Intelligent caching với 30s TTL

| Feature | Legacy (463 lines) | v2.0 (2,934 lines) |- Retry mechanism với exponential backoff

|---------|-------------------|---------------------|- Data validation và error handling

| Structure | Monolithic | Modular (8 modules) |

| Testing | Difficult | Easy |### **🧠 SMC Strategy**  

| Maintenance | Hard | Easy |- Market Structure Analysis (BOS/CHoCH)

| Extensibility | Limited | High |- Order Block Detection với volume confirmation

| Type Safety | Basic | Comprehensive |- Fair Value Gap identification

| Logging | Basic | Professional |- Multi-factor confluence scoring

- Configurable parameters

**Status**: ✅ Complete - Legacy kept as backup

### **📝 Monitoring**

---- Professional logging với multiple levels

- Performance metrics tracking

**Built with**: Python 3.9, Pandas, NumPy, Pybit- Trade history export
- Real-time P&L calculation

## 🎛️ **Configuration**

### **SMC Strategy Config**
```python
smc_config = {
    'required_history': 100,     # Số nến cần thiết
    'timeframe': '15',           # Khung thời gian  
    'min_confidence': 75.0,      # Confidence tối thiểu
    'stop_loss_pct': 1.5,        # Stop loss %
    'take_profit_pct': 2.5,      # Take profit %
    'rsi_period': 14,            # RSI period
    'rsi_overbought': 70,        # RSI overbought
    'rsi_oversold': 30           # RSI oversold
}
```

## 🔄 **Legacy vs New**

| Aspect | Legacy (vps_bot.py) | New Architecture |
|--------|-------------------|------------------|
| **Structure** | Monolithic | Modular |
| **Testing** | Hard to test | Unit testable |
| **Logging** | Basic prints | Professional logging |
| **Extensibility** | Hard to extend | Easy to add strategies |
| **Maintenance** | Complex | Clean separation |
| **Monitoring** | Manual | Real-time metrics |

## 🎯 **Roadmap**

### **Phase 1 (DONE)** ✅
- [x] Modular architecture design
- [x] Data feed module  
- [x] SMC strategy engine
- [x] Professional logging
- [x] Performance metrics

### **Phase 2 (IN PROGRESS)** 🚧
- [ ] Risk management module
- [ ] Order manager với real execution
- [ ] Paper trading mode
- [ ] Backtest engine

### **Phase 3 (PLANNED)** 📋
- [ ] Multi-strategy support
- [ ] Portfolio management
- [ ] Web dashboard
- [ ] Alert notifications

## 🌐 **Current VPS Status**
🟢 **Legacy bot vẫn đang chạy ổn định trên VPS:**
- **VPS**: DigitalOcean Singapore (139.59.226.82)
- **Balance**: $10,020+ USDT (testnet)
- **Schedule**: Cron job mỗi 15 phút
- **Status**: Stable, no errors

## 📞 **Support**
- **Issues**: GitHub Issues
- **Architecture**: Modular, extensible design
- **Version**: 2.0.0 (Professional)

---
*🚀 Professional Trading System - Clean Architecture & Type Safety*
