import os
from dotenv import load_dotenv
from pybit.unified_trading import HTTP
import json

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

session = HTTP(testnet=True, api_key=API_KEY, api_secret=API_SECRET)

print("=== 🧪 Test Long Order ===")

# Lấy giá hiện tại
try:
    ticker = session.get_tickers(category="linear", symbol="BTCUSDT")
    current_price = float(ticker['result']['list'][0]['lastPrice'])
    print(f"📊 Giá BTC hiện tại: ${current_price:,.2f}")
except Exception as e:
    print(f"❌ Lỗi lấy giá: {e}")
    exit()

# Kiểm tra balance
try:
    balance_data = session.get_wallet_balance(accountType="UNIFIED")
    account_info = balance_data['result']['list'][0]
    available_balance = float(account_info.get('totalAvailableBalance', 0))
    print(f"💰 Số dư khả dụng: ${available_balance:,.2f}")
except Exception as e:
    print(f"❌ Lỗi lấy balance: {e}")
    exit()

if available_balance < 10:
    print("❌ Không đủ balance để test")
    exit()

# Tham số test Long
SYMBOL = "BTCUSDT"
QUANTITY = "0.001"  # Test với quantity nhỏ
LEVERAGE = 5

print(f"\n🚀 Chuẩn bị đặt lệnh Long:")
print(f"   Symbol: {SYMBOL}")
print(f"   Quantity: {QUANTITY} BTC")
print(f"   Leverage: {LEVERAGE}x")
print(f"   Entry Price: Market (~${current_price:,.2f})")

# Set leverage trước
try:
    leverage_result = session.set_leverage(
        category="linear",
        symbol=SYMBOL,
        buyLeverage=str(LEVERAGE),
        sellLeverage=str(LEVERAGE)
    )
    print(f"✅ Set leverage {LEVERAGE}x thành công")
except Exception as e:
    print(f"⚠️  Set leverage lỗi: {e} (có thể đã được set từ trước)")

# Đặt lệnh Long Market
try:
    print("\n📤 Đang đặt lệnh Long Market...")
    
    order_result = session.place_order(
        category="linear",
        symbol=SYMBOL,
        side="Buy",
        orderType="Market",
        qty=QUANTITY
    )
    
    print(f"📋 Order result: {json.dumps(order_result, indent=2)}")
    
    if order_result['retCode'] == 0:
        order_id = order_result['result']['orderId']
        print(f"✅ THÀNH CÔNG! Order ID: {order_id}")
        
        # Đợi 2 giây rồi check status
        import time
        time.sleep(2)
        
        # Kiểm tra order status
        try:
            order_info = session.get_open_orders(
                category="linear",
                symbol=SYMBOL,
                orderId=order_id
            )
            print(f"📊 Order status: {json.dumps(order_info, indent=2)}")
        except Exception as e:
            print(f"⚠️  Không check được order status: {e}")
        
        # Kiểm tra positions
        try:
            positions = session.get_positions(category="linear", symbol=SYMBOL)
            if positions['retCode'] == 0:
                for pos in positions['result']['list']:
                    if float(pos['size']) > 0:
                        print(f"\n🎯 Position mở thành công:")
                        print(f"   Side: {pos['side']}")
                        print(f"   Size: {pos['size']} BTC")
                        print(f"   Entry Price: ${float(pos['avgPrice']):,.2f}")
                        print(f"   Unrealized PnL: ${float(pos['unrealisedPnl']):,.2f}")
                        break
        except Exception as e:
            print(f"⚠️  Không check được positions: {e}")
            
    else:
        print(f"❌ Đặt lệnh thất bại: {order_result['retMsg']}")
        print(f"   Error Code: {order_result['retCode']}")
        
except Exception as e:
    print(f"❌ Lỗi đặt lệnh: {e}")

print("\n💡 Lưu ý:")
print("- Đây là lệnh test trên testnet")
print("- Để close position: dùng lệnh Sell với cùng quantity")
print("- Hoặc vào web testnet.bybit.com để close thủ công")