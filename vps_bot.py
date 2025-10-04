import os
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from pybit.unified_trading import HTTP
import time
import random
from datetime import datetime

print("=== 🤖 SMC Bot VPS Version ===")
print(f"🕐 Singapore Time: {datetime.now()}")

# ======================
# 🔄 Retry function cho stability
# ======================
def retry_api_call(func, *args, **kwargs):
    """Retry API calls với exponential backoff"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                delay = (2 ** attempt) + random.uniform(0, 1)
                print(f"⏳ Retry {attempt + 1}/{max_retries}, waiting {delay:.1f}s...")
                time.sleep(delay)
            
            result = func(*args, **kwargs)
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Attempt {attempt + 1} failed: {error_msg}")
            
            if "rate limit" in error_msg.lower() or "403" in error_msg:
                if attempt < max_retries - 1:
                    continue
                else:
                    print("🚫 Rate limit after 3 retries!")
                    return None
            else:
                raise e
    
    return None

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
POSITION_SIZE_USDT = float(os.getenv("POSITION_SIZE_USDT", "25"))

print(f"📊 Symbol: {SYMBOL}")
print(f"🤖 Auto Trade: {AUTO_TRADE}")
print(f"💰 Position Size: ${POSITION_SIZE_USDT}")

if not API_KEY or not API_SECRET:
    print("❌ Missing API credentials in .env file")
    exit(1)

# ======================
# 2️⃣ Connect Bybit
# ======================
try:
    session = HTTP(testnet=True, api_key=API_KEY, api_secret=API_SECRET)
    print("✅ Connected to Bybit Singapore successfully!")
except Exception as e:
    print(f"❌ Bybit connection failed: {e}")
    exit(1)

# ======================
# 3️⃣ SMC Analysis Functions
# ======================
def calculate_rsi(prices, period=14):
    """Calculate RSI without TA-Lib"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def detect_market_structure(df):
    """Detect BOS (Break of Structure) and CHoCH (Change of Character)"""
    highs = df['high'].rolling(5, center=True).max() == df['high']
    lows = df['low'].rolling(5, center=True).min() == df['low']
    
    swing_highs = df.loc[highs, 'high'].dropna()
    swing_lows = df.loc[lows, 'low'].dropna()
    
    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        latest_high = swing_highs.iloc[-1]
        prev_high = swing_highs.iloc[-2]
        latest_low = swing_lows.iloc[-1] 
        prev_low = swing_lows.iloc[-2]
        
        # BOS Bullish: New higher high
        if latest_high > prev_high:
            return "BULLISH_BOS"
        # BOS Bearish: New lower low  
        elif latest_low < prev_low:
            return "BEARISH_BOS"
    
    return "NEUTRAL"

def detect_order_blocks(df):
    """Detect SMC Order Blocks"""
    order_blocks = []
    
    for i in range(5, len(df)-5):
        # Bullish Order Block: Strong green candle before impulse move
        if (df.iloc[i]['close'] > df.iloc[i]['open'] and  # Green candle
            df.iloc[i]['close'] - df.iloc[i]['open'] > df.iloc[i-5:i]['close'].std() * 2):  # Strong move
            
            # Check if followed by upward impulse
            future_high = df.iloc[i+1:i+6]['high'].max()
            if future_high > df.iloc[i]['high'] * 1.01:  # 1% impulse
                order_blocks.append({
                    'type': 'BULLISH_OB',
                    'high': df.iloc[i]['high'],
                    'low': df.iloc[i]['low'],
                    'index': i
                })
        
        # Bearish Order Block: Strong red candle before impulse move
        elif (df.iloc[i]['close'] < df.iloc[i]['open'] and  # Red candle
              df.iloc[i]['open'] - df.iloc[i]['close'] > df.iloc[i-5:i]['close'].std() * 2):  # Strong move
            
            # Check if followed by downward impulse
            future_low = df.iloc[i+1:i+6]['low'].min()
            if future_low < df.iloc[i]['low'] * 0.99:  # 1% impulse
                order_blocks.append({
                    'type': 'BEARISH_OB', 
                    'high': df.iloc[i]['high'],
                    'low': df.iloc[i]['low'],
                    'index': i
                })
    
    return order_blocks[-3:] if order_blocks else []  # Return latest 3

def detect_fair_value_gaps(df):
    """Detect Fair Value Gaps (FVG)"""
    fvgs = []
    
    for i in range(1, len(df)-1):
        # Bullish FVG: Gap between candle 1 low and candle 3 high
        if (df.iloc[i-1]['low'] > df.iloc[i+1]['high'] and
            df.iloc[i]['close'] > df.iloc[i]['open']):  # Middle candle is bullish
            
            fvgs.append({
                'type': 'BULLISH_FVG',
                'high': df.iloc[i-1]['low'],
                'low': df.iloc[i+1]['high'],
                'index': i
            })
        
        # Bearish FVG: Gap between candle 1 high and candle 3 low  
        elif (df.iloc[i-1]['high'] < df.iloc[i+1]['low'] and
              df.iloc[i]['close'] < df.iloc[i]['open']):  # Middle candle is bearish
            
            fvgs.append({
                'type': 'BEARISH_FVG',
                'high': df.iloc[i+1]['low'], 
                'low': df.iloc[i-1]['high'],
                'index': i
            })
    
    return fvgs[-2:] if fvgs else []  # Return latest 2

def get_smc_signal():
    """Main SMC analysis function"""
    try:
        print("🔍 Starting SMC analysis...")
        
        # Get market data
        candles = retry_api_call(
            session.get_kline,
            category="linear",
            symbol=SYMBOL,
            interval="15",
            limit=100
        )
        
        if not candles:
            print("❌ Failed to get market data")
            return None
            
        # Convert to DataFrame
        df = pd.DataFrame(candles['result']['list'], columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
        ])
        
        for col in ['open', 'high', 'low', 'close']:
            df[col] = df[col].astype(float)
        
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Calculate indicators
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean() 
        df['rsi'] = calculate_rsi(df['close'], 14)
        
        current_price = df['close'].iloc[-1]
        current_rsi = df['rsi'].iloc[-1]
        
        print(f"📈 Current Price: ${current_price:,.2f}")
        print(f"📊 RSI: {current_rsi:.1f}")
        
        # SMC Analysis
        market_structure = detect_market_structure(df)
        order_blocks = detect_order_blocks(df)
        fvgs = detect_fair_value_gaps(df)
        
        print(f"🏗️ Market Structure: {market_structure}")
        print(f"📦 Order Blocks: {len(order_blocks)} detected")
        print(f"📊 Fair Value Gaps: {len(fvgs)} detected")
        
        # Generate signal based on SMC confluence
        signal = None
        
        # LONG Signal Conditions
        if (market_structure == "BULLISH_BOS" and
            current_rsi < 70 and  # Not overbought
            current_price > df['sma_20'].iloc[-1] and
            any(ob['type'] == 'BULLISH_OB' for ob in order_blocks)):
            
            signal = {
                'direction': 'LONG',
                'entry_price': current_price,
                'stop_loss': current_price * 0.985,  # 1.5% SL
                'take_profit': current_price * 1.025,  # 2.5% TP
                'confidence': 85,
                'reason': 'Bullish BOS + OB + Above SMA20 + RSI OK'
            }
        
        # SHORT Signal Conditions  
        elif (market_structure == "BEARISH_BOS" and
              current_rsi > 30 and  # Not oversold
              current_price < df['sma_20'].iloc[-1] and
              any(ob['type'] == 'BEARISH_OB' for ob in order_blocks)):
            
            signal = {
                'direction': 'SHORT',
                'entry_price': current_price,
                'stop_loss': current_price * 1.015,  # 1.5% SL
                'take_profit': current_price * 0.975,  # 2.5% TP
                'confidence': 85,
                'reason': 'Bearish BOS + OB + Below SMA20 + RSI OK'
            }
        
        return signal
        
    except Exception as e:
        print(f"❌ SMC analysis error: {e}")
        return None

def calculate_position_size(signal, available_balance):
    """Calculate position size based on risk management"""
    try:
        current_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        
        # Calculate risk per unit
        if signal['direction'] == 'LONG':
            risk_per_unit = current_price - stop_loss
        else:
            risk_per_unit = stop_loss - current_price
            
        # Calculate position size based on risk
        risk_amount = available_balance * (RISK_PERCENT / 100)  # 1% risk
        position_size = min(risk_amount / risk_per_unit, POSITION_SIZE_USDT / current_price)
        
        # Round to appropriate precision for BTCUSDT
        position_size = round(position_size, 3)
        
        print(f"💰 Risk Amount: ${risk_amount:.2f}")
        print(f"📏 Position Size: {position_size} BTC")
        
        return position_size if position_size >= 0.001 else 0.001  # Minimum 0.001 BTC
        
    except Exception as e:
        print(f"❌ Position size calculation error: {e}")
        return 0.001

def place_market_order(signal):
    """Place market order with stop loss and take profit"""
    try:
        print(f"🚀 Placing {signal['direction']} market order...")
        
        # Get current balance
        balance_data = retry_api_call(session.get_wallet_balance, accountType="UNIFIED")
        if not balance_data:
            print("❌ Cannot get balance for order placement")
            return None
            
        available_balance = float(balance_data['result']['list'][0].get('totalAvailableBalance', 0))
        
        # Calculate position size
        qty = calculate_position_size(signal, available_balance)
        
        if qty < 0.001:
            print("❌ Position size too small or insufficient balance")
            return None
        
        # Place main market order
        side = "Buy" if signal['direction'] == 'LONG' else "Sell"
        
        order_result = retry_api_call(
            session.place_order,
            category="linear",
            symbol=SYMBOL,
            side=side,
            orderType="Market",
            qty=str(qty),
            reduceOnly=False
        )
        
        if not order_result or order_result.get('retCode') != 0:
            print(f"❌ Market order failed: {order_result}")
            return None
            
        order_id = order_result['result']['orderId']
        print(f"✅ Market order placed! ID: {order_id}")
        
        # Wait a moment for order to execute
        time.sleep(2)
        
        # Place Stop Loss order
        sl_side = "Sell" if signal['direction'] == 'LONG' else "Buy"
        sl_result = retry_api_call(
            session.place_order,
            category="linear", 
            symbol=SYMBOL,
            side=sl_side,
            orderType="Market",
            qty=str(qty),
            stopLoss=str(signal['stop_loss']),
            reduceOnly=True
        )
        
        if sl_result and sl_result.get('retCode') == 0:
            print(f"✅ Stop Loss placed at ${signal['stop_loss']:.2f}")
        else:
            print(f"⚠️ Stop Loss failed: {sl_result}")
        
        # Place Take Profit order  
        tp_result = retry_api_call(
            session.place_order,
            category="linear",
            symbol=SYMBOL, 
            side=sl_side,
            orderType="Market",
            qty=str(qty),
            takeProfit=str(signal['take_profit']),
            reduceOnly=True
        )
        
        if tp_result and tp_result.get('retCode') == 0:
            print(f"✅ Take Profit placed at ${signal['take_profit']:.2f}")
        else:
            print(f"⚠️ Take Profit failed: {tp_result}")
            
        return order_id
        
    except Exception as e:
        print(f"❌ Order placement error: {e}")
        return None

def check_account_status():
    """Check account balance and positions"""
    try:
        print("💰 Checking account...")
        
        # Get balance with retry
        balance_data = retry_api_call(
            session.get_wallet_balance,
            accountType="UNIFIED"
        )
        
        if balance_data is None:
            print("⚠️ Cannot get balance, using mock data...")
            return {
                'balance': 0,
                'positions': 0,
                'can_trade': False,
                'error': 'rate_limit'
            }
        
        account_info = balance_data['result']['list'][0]
        available_balance = float(account_info.get('totalAvailableBalance', 0))
        
        # Get positions with retry
        print("📊 Checking positions...")
        positions_data = retry_api_call(
            session.get_positions,
            category="linear",
            symbol=SYMBOL
        )
        
        if positions_data is None:
            print("⚠️ Cannot get positions, assume 0 positions...")
            open_positions = []
        else:
            open_positions = [p for p in positions_data['result']['list'] if float(p['size']) > 0]
        
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
        print(f"❌ Account check error: {e}")
        return {'balance': 0, 'positions': 0, 'can_trade': False}

# ======================
# 4️⃣ Main Execution
# ======================
def main():
    """Main bot execution"""
    print("🚀 Starting SMC Bot...")
    
    # Check account
    account = check_account_status()
    if not account['can_trade'] and AUTO_TRADE:
        print("⚠️ Cannot trade - insufficient balance or open positions")
        return
    
    # Get SMC signal
    signal = get_smc_signal()
    
    if signal:
        print(f"🎯 {signal['direction']} Signal Detected!")
        print(f"📍 Entry: ${signal['entry_price']:.2f}")
        print(f"🛑 Stop Loss: ${signal['stop_loss']:.2f}")  
        print(f"🎯 Take Profit: ${signal['take_profit']:.2f}")
        print(f"💡 Reason: {signal['reason']}")
        print(f"🔒 Confidence: {signal['confidence']}%")
        
        if AUTO_TRADE:
            print("🤖 Auto-trading enabled - placing order...")
            place_order_result = place_market_order(signal)
            if place_order_result:
                print(f"✅ Order placed successfully! ID: {place_order_result}")
            else:
                print("❌ Failed to place order")
        else:
            print("📋 Auto-trading disabled - signal logged only")
    else:
        print("⏳ No SMC signal detected")
    
    print(f"✅ Analysis complete at {datetime.now()}")

if __name__ == "__main__":
    main()