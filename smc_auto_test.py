import os
from dotenv import load_dotenv
from pybit.unified_trading import HTTP
import pandas as pd
import numpy as np

# Force enable auto trading
load_dotenv()
os.environ['AUTO_TRADE'] = 'true'
os.environ['POSITION_SIZE_USDT'] = '25'

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET") 
AUTO_TRADE = True

session = HTTP(testnet=True, api_key=API_KEY, api_secret=API_SECRET)

print("=== 🤖 SMC Bot Auto Trading Test ===")
print(f"🔥 AUTO_TRADE: {AUTO_TRADE}")

def simple_smc_check():
    """Simplified SMC check for demo"""
    
    # Get current price
    ticker = session.get_tickers(category="linear", symbol="BTCUSDT")
    current_price = float(ticker['result']['list'][0]['lastPrice'])
    
    print(f"📊 Current BTC Price: ${current_price:,.2f}")
    
    # Get some candle data
    candles = session.get_kline(category="linear", symbol="BTCUSDT", interval="15", limit=20)
    df = pd.DataFrame(candles['result']['list'], columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
    ])
    
    # Convert to float
    for col in ['open', 'high', 'low', 'close']:
        df[col] = df[col].astype(float)
    
    # Simple trend check
    sma_short = df['close'].tail(5).mean()
    sma_long = df['close'].tail(10).mean()
    
    print(f"📈 SMA(5): ${sma_short:.2f}")
    print(f"📈 SMA(10): ${sma_long:.2f}")
    
    # Simple signal logic
    if sma_short > sma_long and current_price > sma_short:
        signal = {
            'direction': 'LONG',
            'entry_price': current_price,
            'stop_loss': current_price * 0.98,  # 2% SL
            'take_profit': current_price * 1.04,  # 4% TP
            'reason': 'Simple bullish signal: Price > SMA(5) > SMA(10)'
        }
        return signal
    elif sma_short < sma_long and current_price < sma_short:
        signal = {
            'direction': 'SHORT', 
            'entry_price': current_price,
            'stop_loss': current_price * 1.02,  # 2% SL
            'take_profit': current_price * 0.96,  # 4% TP
            'reason': 'Simple bearish signal: Price < SMA(5) < SMA(10)'
        }
        return signal
    
    return None

def place_auto_order(signal):
    """Place order automatically"""
    try:
        # Check balance
        balance_data = session.get_wallet_balance(accountType="UNIFIED")
        account_info = balance_data['result']['list'][0]
        available_balance = float(account_info.get('totalAvailableBalance', 0))
        
        if available_balance < 25:
            print(f"❌ Insufficient balance: ${available_balance}")
            return False
        
        # Check existing positions
        positions = session.get_positions(category="linear", symbol="BTCUSDT")
        open_positions = [p for p in positions['result']['list'] if float(p['size']) > 0]
        
        if len(open_positions) > 0:
            print("⚠️ Already have open position, skipping...")
            return False
        
        # Calculate position size (simple)
        position_value = 25  # $25 USD
        quantity = round(position_value / signal['entry_price'], 6)
        
        print(f"\n🚀 PLACING AUTO ORDER:")
        print(f"   Direction: {signal['direction']}")
        print(f"   Quantity: {quantity} BTC")
        print(f"   Entry: ${signal['entry_price']:.2f}")
        print(f"   SL: ${signal['stop_loss']:.2f}")
        print(f"   TP: ${signal['take_profit']:.2f}")
        print(f"   Reason: {signal['reason']}")
        
        # Place the order
        side = "Buy" if signal['direction'] == 'LONG' else "Sell"
        
        order_result = session.place_order(
            category="linear",
            symbol="BTCUSDT", 
            side=side,
            orderType="Market",
            qty=str(quantity)
        )
        
        if order_result['retCode'] == 0:
            order_id = order_result['result']['orderId']
            print(f"✅ ORDER PLACED! ID: {order_id}")
            return True
        else:
            print(f"❌ Order failed: {order_result['retMsg']}")
            return False
            
    except Exception as e:
        print(f"❌ Error placing order: {e}")
        return False

# Main test
try:
    signal = simple_smc_check()
    
    if signal:
        print(f"\n🚨 SIGNAL DETECTED: {signal['direction']}")
        
        # Calculate RR ratio
        if signal['direction'] == 'LONG':
            risk = signal['entry_price'] - signal['stop_loss']
            reward = signal['take_profit'] - signal['entry_price']
        else:
            risk = signal['stop_loss'] - signal['entry_price']
            reward = signal['entry_price'] - signal['take_profit']
        
        rr_ratio = reward / risk
        print(f"📊 Risk/Reward Ratio: 1:{rr_ratio:.2f}")
        
        if rr_ratio >= 1.5:  # Minimum 1.5:1 RR
            print("✅ Good RR ratio!")
            
            if AUTO_TRADE:
                success = place_auto_order(signal)
                if success:
                    print("🎉 AUTO ORDER COMPLETED!")
                else:
                    print("❌ Auto order failed")
            else:
                print("🔒 AUTO_TRADE disabled")
        else:
            print("❌ RR ratio too low")
    else:
        print("⏳ No signal detected")
        
except Exception as e:
    print(f"❌ Error: {e}")