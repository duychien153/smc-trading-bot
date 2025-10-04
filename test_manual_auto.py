import os
from dotenv import load_dotenv

# Force reload .env
load_dotenv(override=True)

print("Current .env values:")
print(f"AUTO_TRADE = {os.getenv('AUTO_TRADE')}")
print(f"POSITION_SIZE_USDT = {os.getenv('POSITION_SIZE_USDT')}")

# Manually set for this session
os.environ['AUTO_TRADE'] = 'true'
os.environ['POSITION_SIZE_USDT'] = '25'

AUTO_TRADE = os.getenv("AUTO_TRADE", "false").lower() == "true"
print(f"\nAfter manual set:")
print(f"AUTO_TRADE = {AUTO_TRADE}")

if AUTO_TRADE:
    print("🚨 AUTO_TRADING IS NOW ENABLED!")
    print("⚡ Bot sẽ đặt lệnh thật khi có signal SMC")
    
    # Import và test SMC bot
    from pybit.unified_trading import HTTP
    import pandas as pd
    import numpy as np
    
    # Tạo fake signal để test
    fake_signal = {
        'direction': 'LONG',
        'entry_price': 24200,
        'stop_loss': 24000,
        'take_profit': 24600,
        'reason': 'Test signal'
    }
    
    print(f"\n🧪 Test với fake signal:")
    print(f"Direction: {fake_signal['direction']}")
    print(f"Entry: ${fake_signal['entry_price']}")
    print(f"SL: ${fake_signal['stop_loss']}")
    print(f"TP: ${fake_signal['take_profit']}")
    
    # Calculate RR
    risk = fake_signal['entry_price'] - fake_signal['stop_loss']
    reward = fake_signal['take_profit'] - fake_signal['entry_price']
    rr_ratio = reward / risk
    print(f"Risk/Reward: 1:{rr_ratio:.2f}")
    
    # Test với session thật
    session = HTTP(testnet=True, api_key=os.getenv("API_KEY"), api_secret=os.getenv("API_SECRET"))
    
    try:
        # Check positions
        positions = session.get_positions(category="linear", symbol="BTCUSDT")
        open_positions = [p for p in positions['result']['list'] if float(p['size']) > 0]
        print(f"\nOpen positions: {len(open_positions)}")
        
        if len(open_positions) > 0:
            print("⚠️ Đã có position mở, sẽ không đặt lệnh mới")
        else:
            print("✅ Không có position nào, có thể đặt lệnh mới")
            
            # Simulate placing order
            print("🚀 [SIMULATION] Sẽ đặt lệnh Long nếu có signal thật")
            
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        
else:
    print("❌ AUTO_TRADE vẫn là False")