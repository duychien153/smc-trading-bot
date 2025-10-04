import os
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from pybit.unified_trading import HTTP
import json
import time
from datetime import datetime

print("=== 🤖 SMC Bot GitHub Actions ===")
print(f"🕐 Thời gian chạy: {datetime.now()}")

# ======================
# 1️⃣ Load config
# ======================
load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
SYMBOL = os.getenv("SYMBOL", "BTCUSDT")
LEVERAGE = int(os.getenv("LEVERAGE", 5))
RISK_PERCENT = float(os.getenv("RISK_PERCENT", 1))
AUTO_TRADE = os.getenv("AUTO_TRADE", "false").lower() == "true"
POSITION_SIZE_USDT = float(os.getenv("POSITION_SIZE_USDT", "10"))

print(f"📊 Symbol: {SYMBOL}")
print(f"🤖 Auto Trade: {AUTO_TRADE}")
print(f"💰 Position Size: ${POSITION_SIZE_USDT}")

if not API_KEY or not API_SECRET:
    print("❌ Thiếu API credentials")
    exit(1)

# Kết nối Bybit
session = HTTP(testnet=True, api_key=API_KEY, api_secret=API_SECRET)
print("✅ Kết nối Bybit thành công")

# ======================
# 2️⃣ Hàm phân tích đơn giản
# ======================
def get_simple_signal():
    """Phân tích đơn giản cho GitHub Actions"""
    try:
        # Lấy giá hiện tại
        ticker = session.get_tickers(category="linear", symbol=SYMBOL)
        current_price = float(ticker['result']['list'][0]['lastPrice'])
        print(f"📈 Giá {SYMBOL}: ${current_price:,.2f}")
        
        # Lấy dữ liệu candles
        candles = session.get_kline(
            category="linear",
            symbol=SYMBOL,
            interval="15",
            limit=50
        )
        
        # Convert sang DataFrame
        df = pd.DataFrame(candles['result']['list'], columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
        ])
        
        for col in ['open', 'high', 'low', 'close']:
            df[col] = df[col].astype(float)
        
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Tính SMA đơn giản
        df['sma_5'] = df['close'].rolling(5).mean()
        df['sma_10'] = df['close'].rolling(10).mean()
        df['sma_20'] = df['close'].rolling(20).mean()
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        sma5 = latest['sma_5']
        sma10 = latest['sma_10']
        sma20 = latest['sma_20']
        
        print(f"📊 SMA5: ${sma5:.2f}")
        print(f"📊 SMA10: ${sma10:.2f}")
        print(f"📊 SMA20: ${sma20:.2f}")
        
        # Logic signal đơn giản
        # LONG: Price > SMA5 > SMA10 > SMA20 (bullish alignment)
        if (current_price > sma5 > sma10 > sma20 and
            latest['sma_5'] > prev['sma_5']):  # SMA5 đang tăng
            
            return {
                'direction': 'LONG',
                'entry_price': current_price,
                'stop_loss': sma10 * 0.995,  # SL dưới SMA10
                'take_profit': current_price * 1.02,  # TP 2%
                'reason': 'Bullish SMA alignment + trending up'
            }
        
        # SHORT: Price < SMA5 < SMA10 < SMA20 (bearish alignment)
        elif (current_price < sma5 < sma10 < sma20 and
              latest['sma_5'] < prev['sma_5']):  # SMA5 đang giảm
            
            return {
                'direction': 'SHORT',
                'entry_price': current_price,
                'stop_loss': sma10 * 1.005,  # SL trên SMA10
                'take_profit': current_price * 0.98,  # TP 2%
                'reason': 'Bearish SMA alignment + trending down'
            }
        
        return None
        
    except Exception as e:
        print(f"❌ Lỗi phân tích: {e}")
        return None

def check_account_status():
    """Kiểm tra trạng thái tài khoản"""
    try:
        # Balance
        balance_data = session.get_wallet_balance(accountType="UNIFIED")
        account_info = balance_data['result']['list'][0]
        available_balance = float(account_info.get('totalAvailableBalance', 0))
        
        # Positions
        positions = session.get_positions(category="linear", symbol=SYMBOL)
        open_positions = [p for p in positions['result']['list'] if float(p['size']) > 0]
        
        print(f"💰 Available Balance: ${available_balance:.2f}")
        print(f"📊 Open Positions: {len(open_positions)}")
        
        for pos in open_positions:
            print(f"   {pos['side']} {pos['size']} @ ${pos['avgPrice']} (PnL: ${pos['unrealisedPnl']})")
        
        return {
            'balance': available_balance,
            'positions': len(open_positions),
            'can_trade': available_balance >= POSITION_SIZE_USDT and len(open_positions) == 0
        }
        
    except Exception as e:
        print(f"❌ Lỗi check account: {e}")
        return {'balance': 0, 'positions': 0, 'can_trade': False}

def place_order_if_enabled(signal):
    """Đặt lệnh nếu AUTO_TRADE enabled"""
    if not AUTO_TRADE:
        print("🔒 AUTO_TRADE = False, chỉ hiển thị signal")
        return False
        
    try:
        # Tính position size
        risk_amount = POSITION_SIZE_USDT * (RISK_PERCENT / 100)
        price_diff = abs(signal['entry_price'] - signal['stop_loss'])
        
        if price_diff > 0:
            quantity = round(risk_amount / price_diff, 6)
        else:
            print("❌ Invalid price difference")
            return False
        
        print(f"📊 Calculated quantity: {quantity} {SYMBOL}")
        
        # Đặt lệnh
        side = "Buy" if signal['direction'] == 'LONG' else "Sell"
        
        order_result = session.place_order(
            category="linear",
            symbol=SYMBOL,
            side=side,
            orderType="Market",
            qty=str(quantity)
        )
        
        if order_result['retCode'] == 0:
            order_id = order_result['result']['orderId']
            print(f"✅ Đặt lệnh thành công! OrderID: {order_id}")
            
            # Log thành file để GitHub Actions lưu
            with open('trade_log.txt', 'a') as f:
                f.write(f"{datetime.now()}: {signal['direction']} {quantity} @ {signal['entry_price']}\n")
            
            return True
        else:
            print(f"❌ Đặt lệnh thất bại: {order_result['retMsg']}")
            return False
            
    except Exception as e:
        print(f"❌ Lỗi đặt lệnh: {e}")
        return False

# ======================
# 3️⃣ Main execution
# ======================
def main():
    """Main function cho GitHub Actions"""
    print("\n🔍 Bắt đầu phân tích...")
    
    # Check account
    account_status = check_account_status()
    
    # Phân tích signal
    signal = get_simple_signal()
    
    if signal:
        print(f"\n🚨 SIGNAL DETECTED: {signal['direction']}")
        print(f"   Entry: ${signal['entry_price']:.2f}")
        print(f"   SL: ${signal['stop_loss']:.2f}")
        print(f"   TP: ${signal['take_profit']:.2f}")
        print(f"   Reason: {signal['reason']}")
        
        # Tính RR ratio
        if signal['direction'] == 'LONG':
            risk = signal['entry_price'] - signal['stop_loss']
            reward = signal['take_profit'] - signal['entry_price']
        else:
            risk = signal['stop_loss'] - signal['entry_price']
            reward = signal['entry_price'] - signal['take_profit']
        
        rr_ratio = reward / risk if risk > 0 else 0
        print(f"   Risk/Reward: 1:{rr_ratio:.2f}")
        
        if rr_ratio >= 1.5:  # Min RR
            print("✅ Good RR ratio!")
            
            if account_status['can_trade']:
                success = place_order_if_enabled(signal)
                if success:
                    print("🎉 Trade executed!")
                else:
                    print("❌ Trade failed")
            else:
                if account_status['balance'] < POSITION_SIZE_USDT:
                    print("❌ Insufficient balance")
                else:
                    print("⚠️ Already have open position")
        else:
            print("❌ RR ratio too low")
    else:
        print("⏳ No signal detected")
    
    print(f"\n✅ Hoàn tất lúc: {datetime.now()}")

if __name__ == "__main__":
    main()