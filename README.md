# SMC Trading Bot 🤖

Bot trading tự động sử dụng Smart Money Concept (SMC) và Inner Circle Trader (ICT) methodology cho Bybit testnet.

## Features
- ✅ Market Structure Analysis (BOS/CHoCH Detection)
- ✅ Order Block Detection với volume filtering
- ✅ Fair Value Gap (FVG) Detection  
- ✅ RSI & Price Action Confluence
- ✅ Risk Management với 1% risk per trade
- ✅ Auto Trading 24/7 trên VPS

## Current Setup
🟢 **Đang chạy trên DigitalOcean VPS Singapore**
- **VPS IP**: 139.59.226.82
- **Latency**: ~20ms đến Bybit Singapore
- **Schedule**: Cron job mỗi 15 phút
- **Symbol**: BTCUSDT
- **Environment**: Bybit Testnet

## Dependencies
```txt
python-dotenv==1.1.1
pybit==5.12.0
pandas==1.3.5
numpy==1.21.6
```

## Files Structure
```
├── vps_bot.py          # Main trading bot
├── requirements.txt    # Python dependencies  
├── .env               # API credentials (local)
├── README.md          # This file
└── VPS_SETUP.md       # VPS deployment guide
```

## Bot Logic
1. **Market Structure**: Detect BOS (Break of Structure) và CHoCH
2. **Order Blocks**: Identify supply/demand zones với volume confirmation
3. **Fair Value Gaps**: Detect imbalance areas
4. **Entry Signal**: Confluence of structure + order block + FVG
5. **Risk Management**: 1% risk per trade, 2:1 RR minimum

## Current Status
- ✅ **Bot Status**: Running 24/7 on VPS
- ✅ **Balance**: $10,020+ USDT (testnet)
- ✅ **Monitoring**: Real-time logs via SSH
- ✅ **Performance**: Stable connection, no errors

---
*Created with SMC/ICT methodology - Singapore VPS deployment*
