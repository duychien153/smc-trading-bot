import os
from dotenv import load_dotenv
from pybit.unified_trading import HTTP

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
AUTO_TRADE = os.getenv("AUTO_TRADE", "false").lower() == "true"

session = HTTP(testnet=True, api_key=API_KEY, api_secret=API_SECRET)

print("=== 🧪 Test Auto Trading ===")
print(f"AUTO_TRADE setting: {AUTO_TRADE}")

# Test 1: Kiểm tra balance
try:
    balance_data = session.get_wallet_balance(accountType="UNIFIED")
    account_info = balance_data['result']['list'][0]
    total_balance = float(account_info.get('totalWalletBalance', 0))
    available_balance = float(account_info.get('totalAvailableBalance', 0))
    print(f"💰 Balance: ${total_balance} (Available: ${available_balance})")
except Exception as e:
    print(f"❌ Lỗi lấy balance: {e}")

# Test 2: Kiểm tra positions hiện tại
try:
    positions = session.get_positions(category="linear", symbol="BTCUSDT")
    if positions['retCode'] == 0:
        open_positions = [p for p in positions['result']['list'] if float(p['size']) > 0]
        print(f"📊 Open positions: {len(open_positions)}")
        
        for pos in open_positions:
            print(f"   {pos['side']} {pos['size']} @ ${pos['avgPrice']}")
    else:
        print(f"❌ Lỗi lấy positions: {positions['retMsg']}")
except Exception as e:
    print(f"❌ Lỗi check positions: {e}")

# Test 3: Simulate đặt lệnh (nếu AUTO_TRADE = True)
if AUTO_TRADE:
    print("\n🚨 AUTO_TRADE = True")
    print("⚠️  Bot sẽ đặt lệnh thật khi có signal!")
    print("📝 Để test an toàn, set AUTO_TRADE=false trong .env")
else:
    print("\n✅ AUTO_TRADE = False") 
    print("🔒 Bot chỉ hiển thị signal, không đặt lệnh thật")
    print("💡 Để bật auto trading, set AUTO_TRADE=true trong .env")

print("\n🔍 Để xem bot hoạt động:")
print("1. python smc_bot.py - test 1 lần")
print("2. Chọn 'y' để chạy live monitoring")
print("3. Bot sẽ báo khi có signal SMC")

if AUTO_TRADE and available_balance > 0:
    print("\n⚡ Bot sẵn sàng auto trading!")
elif AUTO_TRADE and available_balance == 0:
    print("\n⚠️  AUTO_TRADE bật nhưng balance = 0")
else:
    print("\n🔒 Safe mode: Chỉ hiển thị signals")