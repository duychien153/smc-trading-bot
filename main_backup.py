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
# 3️⃣ Kiểm tra balance tất cả các account
# ======================

# Danh sách các account type để kiểm tra
account_types = ["UNIFIED", "SPOT", "CONTRACT", "INVESTMENT", "OPTION"]

for account_type in account_types:
    try:
        print(f"\n🔍 Kiểm tra {account_type} Account:")
        balance_data = session.get_wallet_balance(accountType=account_type)
        
        # Kiểm tra nếu có dữ liệu
        if balance_data.get('result', {}).get('list'):
            account_info = balance_data['result']['list'][0]
            total_wallet_balance = float(account_info.get('totalWalletBalance', 0))
            total_available_balance = float(account_info.get('totalAvailableBalance', 0))
            
            print(f"   💰 Tổng số dư ví: {total_wallet_balance}")
            print(f"   💰 Số dư khả dụng: {total_available_balance}")
            
            # Chi tiết từng coin
            coins = account_info.get('coin', [])
            if coins:
                print("   📋 Chi tiết coins:")
                for coin in coins:
                    coin_name = coin.get('coin', 'Unknown')
                    wallet_balance = float(coin.get('walletBalance', 0))
                    available_balance = float(coin.get('availableToWithdraw', 0))
                    if wallet_balance > 0:
                        print(f"      {coin_name}: {wallet_balance} (khả dụng: {available_balance})")
            else:
                print("   ℹ️  Không có coin nào")
        else:
            print(f"   ❌ Không thể lấy dữ liệu cho {account_type}")
            
    except Exception as e:
        print(f"   ❌ Lỗi khi lấy {account_type} balance: {e}")

# Thử các API khác để lấy balance
print(f"\n🔍 Thử các API khác:")

# 1. Thử get account info
try:
    account_info = session.get_account_info()
    print("📊 Account Info:", json.dumps(account_info, indent=2))
except Exception as e:
    print(f"❌ Lỗi get_account_info: {e}")

# 2. Thử get all coins balance (nếu có)
try:
    all_balance = session.get_all_coins_balance(accountType="UNIFIED")
    print("📊 All Coins Balance:", json.dumps(all_balance, indent=2))
except Exception as e:
    print(f"❌ Lỗi get_all_coins_balance: {e}")

print(f"\n� Thử thêm một số API khác:")

# Thử lấy position info
try:
    positions = session.get_positions(category="linear")
    print("📊 Positions:", json.dumps(positions, indent=2))
except Exception as e:
    print(f"❌ Lỗi get_positions: {e}")

# Thử get server time để test connection
try:
    server_time = session.get_server_time()
    print("🕐 Server Time:", json.dumps(server_time, indent=2))
except Exception as e:
    print(f"❌ Lỗi get_server_time: {e}")

print(f"\n💡 Các bước kiểm tra tiếp theo:")
print("1. 🌐 Vào https://testnet.bybit.com để kiểm tra balance trực tiếp")
print("2. 🔑 Kiểm tra API Key permissions (cần có 'Read' permission)")
print("3. ⏰ Có thể cần đợi 5-10 phút để balance sync")
print("4. 📧 Kiểm tra email xác nhận nạp tiền thành công")
print("5. 🔄 Thử tạo API key mới với full permissions")

# Hiển thị thông tin kết nối hiện tại
print(f"\n📋 Thông tin kết nối hiện tại:")
print(f"   API Key: {API_KEY[:8]}...")
print(f"   Testnet: True")
print(f"   Unified Margin Status: 5")
print(f"   Account Margin Mode: REGULAR_MARGIN")
