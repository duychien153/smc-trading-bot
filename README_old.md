# SMC Trading Bot v2.0 🚀

**Professional Trading System** sử dụng Smart Money Concept (SMC) với kiến trúc modular.

## 🆕 Architecture v2.0 - REFACTORED

### ✨ **Key Improvements**
- 🏗️ **Modular Design**: Tách biệt các concerns (data, strategy, risk, orders)
- 📊 **Professional Logging**: Multi-level logging với performance metrics  
- 🔄 **Extensible**: Dễ dàng thêm strategies và exchanges mới
- 🧪 **Testable**: Clean interfaces cho unit testing
- 📈 **Monitoring**: Real-time performance tracking
- 🛡️ **Type Safety**: Sử dụng dataclasses và enums

### 📁 **New Project Structure**
```
├── src/                          # 🎯 Core modules  
│   ├── models.py                 # 📊 Data models & types
│   ├── data_feed/               # 🔌 Market data management
│   │   └── market_data.py       # Bybit API + caching
│   ├── strategy/                # 🧠 Trading strategies
│   │   ├── base_strategy.py     # Abstract base class  
│   │   └── smc_strategy.py      # SMC implementation
│   ├── risk_management/         # 🛡️ Risk controls (TODO)
│   ├── order_manager/           # 📋 Order execution (TODO)
│   ├── backtest/                # 📈 Historical testing (TODO)
│   └── monitoring/              # 📝 Logging & metrics
│       ├── logger.py            # Professional logging
│       └── metrics.py           # Performance tracking
├── config/                      # ⚙️ Configuration files
├── tests/                       # 🧪 Unit tests  
├── logs/                        # � Log files
├── vps_bot.py                   # 🔄 Legacy bot (still running on VPS)
└── demo_new_architecture.py     # 🎬 Demo script
```

## 🚀 **Quick Start với Architecture Mới**

### 1. **Setup Environment**
```bash
# Install dependencies
pip install -r requirements.txt

# Setup .env file with API credentials
cp .env.example .env
# Edit .env with your Bybit API keys
```

### 2. **Demo Usage**
```bash
# Run architecture demo
python3 demo_new_architecture.py

# Check logs
ls logs/
```

### 3. **Usage Example**
```python
from src.data_feed.market_data import MarketDataFeed
from src.strategy.smc_strategy import SMCStrategy

# Initialize components
data_feed = MarketDataFeed(api_key, api_secret)
strategy = SMCStrategy("BTCUSDT", config)

# Get market data  
candles = data_feed.get_candles("BTCUSDT", "15", 100)
market_data = data_feed.get_market_data("BTCUSDT")

# Generate trading signal
signal = strategy.process_signal(candles, market_data)

if signal:
    print(f"Signal: {signal.signal_type.value}")
    print(f"Entry: ${signal.entry_price:.2f}")
    print(f"Confidence: {signal.confidence:.1f}%")
```

## 🏗️ **Components**

### **📊 Data Feed**
- Real-time market data từ Bybit API
- Intelligent caching với 30s TTL
- Retry mechanism với exponential backoff
- Data validation và error handling

### **🧠 SMC Strategy**  
- Market Structure Analysis (BOS/CHoCH)
- Order Block Detection với volume confirmation
- Fair Value Gap identification
- Multi-factor confluence scoring
- Configurable parameters

### **📝 Monitoring**
- Professional logging với multiple levels
- Performance metrics tracking
- Trade history export
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
