import os
from dotenv import load_dotenv
from pybit.unified_trading import HTTP
import json

print("=== 🚀 Bot Trading Bybit ===")

# ======================
# 1️⃣ Load .env
# ======================
load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
SYMBOL = os.getenv("SYMBOL", "BTCUSDT")  # default BTCUSDT
LEVERAGE = int(os.getenv("LEVERAGE", 5))
RISK_PERCENT = float(os.getenv("RISK_PERCENT", 1))  # % vốn mỗi lệnh

# Debug load env
if not API_KEY or not API_SECRET:
    print("❌ API_KEY hoặc API_SECRET chưa load được từ .env")
    exit(1)
else:
    print("✅ API_KEY & API_SECRET đã load")

# ======================
# 2️⃣ Kết nối Bybit testnet
# ======================
session = HTTP(
    testnet=True,
    api_key=API_KEY,
    api_secret=API_SECRET
)
print("✅ Kết nối client testnet thành công")

# ======================
# 3️⃣ Kiểm tra balance 
# ======================
try:
    balance_data = session.get_wallet_balance(accountType="UNIFIED")
    account_info = balance_data['result']['list'][0]
    total_wallet_balance = float(account_info.get('totalWalletBalance', 0))
    total_available_balance = float(account_info.get('totalAvailableBalance', 0))
    
    print(f"💰 Tổng số dư ví: {total_wallet_balance} USDT")
    print(f"💰 Số dư khả dụng: {total_available_balance} USDT")
    
    # Chi tiết coins nếu có
    coins = account_info.get('coin', [])
    if coins:
        print("📋 Chi tiết coins:")
        for coin in coins:
            coin_name = coin.get('coin', 'Unknown')
            wallet_balance = float(coin.get('walletBalance', 0))
            if wallet_balance > 0:
                print(f"   {coin_name}: {wallet_balance}")
    else:
        print("ℹ️  Chưa có coin nào trong ví (balance = 0)")
        
except Exception as e:
    print("❌ Lỗi khi lấy balance:", e)

# ======================
# 4️⃣ Test lấy giá Bitcoin
# ======================
print(f"\n📈 Lấy giá {SYMBOL}:")
try:
    ticker = session.get_tickers(category="linear", symbol=SYMBOL)
    if ticker['result']['list']:
        btc_price = float(ticker['result']['list'][0]['lastPrice'])
        print(f"   🪙 Giá {SYMBOL} hiện tại: ${btc_price:,.2f}")
    else:
        print("   ❌ Không lấy được giá")
except Exception as e:
    print(f"   ❌ Lỗi lấy giá: {e}")

# ======================  
# 5️⃣ Thông tin debug
# ======================
print(f"\n📋 Thông tin kết nối:")
print(f"   API Key: {API_KEY[:8]}...")
print(f"   Symbol: {SYMBOL}")
print(f"   Leverage: {LEVERAGE}x")
print(f"   Risk per trade: {RISK_PERCENT}%")

print(f"\n💡 Trạng thái:")
if total_wallet_balance > 0:
    print("✅ Sẵn sàng để trading!")
else:
    print("⚠️  Balance = 0. Cần kiểm tra:")
    print("   1. Vào testnet.bybit.com kiểm tra balance")  
    print("   2. Kiểm tra API permissions")
    print("   3. Đợi sync (5-10 phút)")
