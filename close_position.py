import os
from dotenv import load_dotenv
from pybit.unified_trading import HTTP

load_dotenv()
os.environ['AUTO_TRADE'] = 'true'  # Force enable

session = HTTP(testnet=True, api_key=os.getenv("API_KEY"), api_secret=os.getenv("API_SECRET"))

print("=== 🔄 Close Position để test SMC bot ===")

try:
    # Get open positions
    positions = session.get_positions(category="linear", symbol="BTCUSDT")
    
    for pos in positions['result']['list']:
        if float(pos['size']) > 0:
            print(f"📊 Tìm thấy position: {pos['side']} {pos['size']} @ ${pos['avgPrice']}")
            
            # Close position bằng lệnh ngược lại
            close_side = "Sell" if pos['side'] == "Buy" else "Buy"
            quantity = pos['size']
            
            print(f"🔄 Đang close bằng lệnh {close_side}...")
            
            close_result = session.place_order(
                category="linear",
                symbol="BTCUSDT",
                side=close_side,
                orderType="Market",
                qty=quantity,
                reduceOnly=True
            )
            
            if close_result['retCode'] == 0:
                print(f"✅ Close thành công! OrderID: {close_result['result']['orderId']}")
            else:
                print(f"❌ Lỗi close: {close_result['retMsg']}")
            break
    else:
        print("ℹ️ Không có position nào để close")

    # Check lại positions sau khi close
    import time
    time.sleep(2)
    
    positions = session.get_positions(category="linear", symbol="BTCUSDT")
    open_count = sum(1 for p in positions['result']['list'] if float(p['size']) > 0)
    
    print(f"\n📊 Sau khi close: {open_count} positions")
    
    if open_count == 0:
        print("✅ Đã close hết positions!")
        print("🚀 Bây giờ SMC bot có thể đặt lệnh mới")
        print("\nChạy: python smc_bot.py để test auto trading")
    
except Exception as e:
    print(f"❌ Lỗi: {e}")