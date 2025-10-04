import os
import pandas as pd
import numpy as np
import talib
from dotenv import load_dotenv
from pybit.unified_trading import HTTP
import json
import time
from datetime import datetime, timedelta

print("=== 🧠 SMC/ICT Trading Bot ===")

# ======================
# 1️⃣ Cấu hình và kết nối
# ======================
load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
SYMBOL = os.getenv("SYMBOL", "BTCUSDT")
LEVERAGE = int(os.getenv("LEVERAGE", 10))
RISK_PERCENT = float(os.getenv("RISK_PERCENT", 1))

# SMC/ICT Settings
TIMEFRAME = "15"  # 15 phút cho entry, có thể dùng 1H cho HTF bias
CANDLES_LIMIT = 200  # Số candles để phân tích
MIN_RR_RATIO = 2.0  # Risk/Reward tối thiểu

# Trading Settings
AUTO_TRADE = os.getenv("AUTO_TRADE", "false").lower() == "true"  # Bật tự động trade
POSITION_SIZE_USDT = float(os.getenv("POSITION_SIZE_USDT", "10"))  # Size mỗi lệnh (USDT)

# Trading Settings
AUTO_TRADE = True  # Tự động đặt lệnh
POSITION_SIZE_USDT = 50  # Kích thước position (USDT)

if not API_KEY or not API_SECRET:
    print("❌ Thiếu API credentials")
    exit(1)

# Kết nối Bybit
session = HTTP(testnet=True, api_key=API_KEY, api_secret=API_SECRET)
print("✅ Kết nối Bybit thành công")

# ======================
# 2️⃣ Hàm lấy dữ liệu candles
# ======================
def get_candles(symbol, interval="15", limit=200):
    """Lấy dữ liệu OHLCV từ Bybit"""
    try:
        result = session.get_kline(
            category="linear",
            symbol=symbol,
            interval=interval,
            limit=limit
        )
        
        if result['retCode'] != 0:
            print(f"❌ Lỗi API: {result['retMsg']}")
            return None
            
        # Convert sang DataFrame
        candles = result['result']['list']
        df = pd.DataFrame(candles, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
        ])
        
        # Convert data types
        df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
            
        # Sort by timestamp (oldest first)
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        print(f"📊 Đã lấy {len(df)} candles cho {symbol}")
        return df
        
    except Exception as e:
        print(f"❌ Lỗi lấy candles: {e}")
        return None

# ======================
# 3️⃣ SMC Market Structure Analysis
# ======================
def identify_swing_points(df, window=5):
    """Xác định swing highs và swing lows"""
    df = df.copy()
    
    # Swing Highs: high cao nhất trong window
    df['swing_high'] = df['high'].rolling(window=window*2+1, center=True).max() == df['high']
    
    # Swing Lows: low thấp nhất trong window  
    df['swing_low'] = df['low'].rolling(window=window*2+1, center=True).min() == df['low']
    
    return df

def analyze_market_structure(df):
    """Phân tích cấu trúc thị trường theo SMC"""
    df = identify_swing_points(df)
    
    # Lấy các swing points
    swing_highs = df[df['swing_high'] == True][['timestamp', 'high']].copy()
    swing_lows = df[df['swing_low'] == True][['timestamp', 'low']].copy()
    
    trend = "NEUTRAL"
    
    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        # Check for Higher Highs và Higher Lows (Uptrend)
        recent_highs = swing_highs.tail(2)['high'].values
        recent_lows = swing_lows.tail(2)['low'].values
        
        if recent_highs[-1] > recent_highs[-2] and recent_lows[-1] > recent_lows[-2]:
            trend = "BULLISH"
        # Check for Lower Highs và Lower Lows (Downtrend)    
        elif recent_highs[-1] < recent_highs[-2] and recent_lows[-1] < recent_lows[-2]:
            trend = "BEARISH"
    
    return {
        'trend': trend,
        'swing_highs': swing_highs,
        'swing_lows': swing_lows,
        'df': df
    }

# ======================
# 4️⃣ Order Block Detection
# ======================
def find_order_blocks(df, structure_info):
    """Tìm Order Blocks - vùng mà institutional orders được đặt"""
    order_blocks = []
    
    # Lấy swing points
    swing_highs = structure_info['swing_highs']
    swing_lows = structure_info['swing_lows']
    
    # Bullish Order Block: Candle trước khi price tăng mạnh
    for _, swing_low in swing_lows.iterrows():
        # Tìm candles trước swing low
        before_swing = df[df['timestamp'] < swing_low['timestamp']].tail(5)
        
        if len(before_swing) > 0:
            # Lấy candle có thể body lớn trước khi tạo swing low
            for _, candle in before_swing.iterrows():
                body_size = abs(candle['close'] - candle['open'])
                wick_size = candle['high'] - candle['low']
                
                # Điều kiện Order Block: body lớn, volume cao
                if body_size > wick_size * 0.6:  # Body chiếm 60% range
                    order_blocks.append({
                        'type': 'BULLISH_OB',
                        'high': candle['high'],
                        'low': candle['low'],
                        'timestamp': candle['timestamp'],
                        'tested': False
                    })
    
    # Bearish Order Block: Tương tự cho downside
    for _, swing_high in swing_highs.iterrows():
        before_swing = df[df['timestamp'] < swing_high['timestamp']].tail(5)
        
        if len(before_swing) > 0:
            for _, candle in before_swing.iterrows():
                body_size = abs(candle['close'] - candle['open'])
                wick_size = candle['high'] - candle['low']
                
                if body_size > wick_size * 0.6:
                    order_blocks.append({
                        'type': 'BEARISH_OB',
                        'high': candle['high'], 
                        'low': candle['low'],
                        'timestamp': candle['timestamp'],
                        'tested': False
                    })
    
    return order_blocks

# ======================
# 5️⃣ Fair Value Gap (FVG) Detection  
# ======================
def find_fair_value_gaps(df):
    """Tìm Fair Value Gaps - imbalances trên chart"""
    fvgs = []
    
    for i in range(2, len(df)):
        candle1 = df.iloc[i-2]  # Candle trước
        candle2 = df.iloc[i-1]  # Candle giữa
        candle3 = df.iloc[i]    # Candle hiện tại
        
        # Bullish FVG: Gap giữa candle1.high và candle3.low
        if candle1['high'] < candle3['low']:
            fvgs.append({
                'type': 'BULLISH_FVG',
                'high': candle3['low'],
                'low': candle1['high'],
                'timestamp': candle3['timestamp'],
                'filled': False
            })
        
        # Bearish FVG: Gap giữa candle1.low và candle3.high    
        elif candle1['low'] > candle3['high']:
            fvgs.append({
                'type': 'BEARISH_FVG',
                'high': candle1['low'],
                'low': candle3['high'], 
                'timestamp': candle3['timestamp'],
                'filled': False
            })
    
    return fvgs

# ======================
# 6️⃣ Liquidity Detection
# ======================
def find_liquidity_zones(df, structure_info):
    """Tìm Equal Highs/Lows và Premium/Discount zones"""
    liquidity_zones = []
    
    swing_highs = structure_info['swing_highs']
    swing_lows = structure_info['swing_lows']
    
    # Equal Highs - nơi có nhiều liquidity
    if len(swing_highs) >= 2:
        for i in range(len(swing_highs)-1):
            current = swing_highs.iloc[i]
            next_high = swing_highs.iloc[i+1]
            
            # Nếu 2 highs gần bằng nhau (trong khoảng 0.1%)
            price_diff = abs(current['high'] - next_high['high']) / current['high']
            if price_diff < 0.001:  # 0.1%
                liquidity_zones.append({
                    'type': 'EQUAL_HIGHS',
                    'price': (current['high'] + next_high['high']) / 2,
                    'timestamp': next_high['timestamp']
                })
    
    # Equal Lows - tương tự
    if len(swing_lows) >= 2:
        for i in range(len(swing_lows)-1):
            current = swing_lows.iloc[i]
            next_low = swing_lows.iloc[i+1]
            
            price_diff = abs(current['low'] - next_low['low']) / current['low']
            if price_diff < 0.001:
                liquidity_zones.append({
                    'type': 'EQUAL_LOWS', 
                    'price': (current['low'] + next_low['low']) / 2,
                    'timestamp': next_low['timestamp']
                })
    
    return liquidity_zones

# ======================
# 🔧 Trading Functions
# ======================
def get_account_balance():
    """Lấy số dư tài khoản"""
    try:
        balance_data = session.get_wallet_balance(accountType="UNIFIED")
        account_info = balance_data['result']['list'][0]
        total_balance = float(account_info.get('totalWalletBalance', 0))
        available_balance = float(account_info.get('totalAvailableBalance', 0))
        
        return {
            'total': total_balance,
            'available': available_balance
        }
    except Exception as e:
        print(f"❌ Lỗi lấy balance: {e}")
        return None

def calculate_position_size(entry_price, stop_loss, risk_usdt=POSITION_SIZE_USDT):
    """Tính kích thước position dựa trên risk"""
    try:
        # Tính risk per share
        risk_per_share = abs(entry_price - stop_loss)
        
        # Tính số lượng có thể mua với risk cho phép
        quantity = risk_usdt / risk_per_share
        
        # Áp dụng leverage
        quantity_with_leverage = quantity * LEVERAGE
        
        return round(quantity_with_leverage, 6)
        
    except Exception as e:
        print(f"❌ Lỗi tính position size: {e}")
        return None

def place_market_order(direction, quantity, stop_loss, take_profit):
    """Đặt lệnh Market với SL và TP"""
    try:
        print(f"🚀 Đặt lệnh {direction}...")
        
        # Đặt lệnh market
        side = "Buy" if direction == "LONG" else "Sell"
        
        order_result = session.place_order(
            category="linear",
            symbol=SYMBOL,
            side=side,
            orderType="Market",
            qty=str(quantity),
            timeInForce="IOC",  # Immediate or Cancel
            reduceOnly=False
        )
        
        if order_result['retCode'] == 0:
            order_id = order_result['result']['orderId']
            print(f"✅ Lệnh Market đã đặt: {order_id}")
            
            # Đợi một chút để lệnh fill
            time.sleep(2)
            
            # Đặt Stop Loss
            sl_result = session.place_order(
                category="linear", 
                symbol=SYMBOL,
                side="Sell" if direction == "LONG" else "Buy",
                orderType="Market",
                qty=str(quantity),
                triggerPrice=str(stop_loss),
                reduceOnly=True
            )
            
            # Đặt Take Profit
            tp_result = session.place_order(
                category="linear",
                symbol=SYMBOL, 
                side="Sell" if direction == "LONG" else "Buy",
                orderType="Market",
                qty=str(quantity),
                triggerPrice=str(take_profit),
                reduceOnly=True
            )
            
            return {
                'success': True,
                'order_id': order_id,
                'sl_result': sl_result,
                'tp_result': tp_result
            }
        else:
            print(f"❌ Lỗi đặt lệnh: {order_result['retMsg']}")
            return {'success': False, 'error': order_result['retMsg']}
            
    except Exception as e:
        print(f"❌ Lỗi đặt lệnh: {e}")
        return {'success': False, 'error': str(e)}

def get_current_positions():
    """Lấy danh sách positions hiện tại"""
    try:
        positions = session.get_positions(category="linear", symbol=SYMBOL)
        
        if positions['retCode'] == 0:
            pos_list = positions['result']['list']
            active_positions = [pos for pos in pos_list if float(pos['size']) > 0]
            return active_positions
        else:
            return []
            
    except Exception as e:
        print(f"❌ Lỗi lấy positions: {e}")
        return []

# ======================
# 7️⃣ SMC Entry Logic
# ======================
def check_smc_entry(df, current_price):
    """Check điều kiện entry theo SMC (Optimized)"""
    print(f"🔍 SMC Analysis - Giá: ${current_price:,.2f}")
    
    # 1. Phân tích Market Structure (nhanh)
    structure = analyze_market_structure(df)
    print(f"📈 Trend: {structure['trend']}")
    
    # 2. Tìm Order Blocks (giới hạn 10 blocks gần nhất)
    order_blocks = find_order_blocks(df, structure)[-10:]
    print(f"📦 Order Blocks: {len(order_blocks)}")
    
    # 3. Tìm Fair Value Gaps (giới hạn 5 gaps gần nhất)
    fvgs = find_fair_value_gaps(df)[-5:]
    print(f"⚡ FVGs: {len(fvgs)}")
    
    # Skip liquidity zones để tăng tốc
    # liquidity_zones = find_liquidity_zones(df, structure)
    
    # Entry logic
    entry_signal = None
    
    # BULLISH SETUP: Uptrend + Bullish OB + có FVG support
    if structure['trend'] == 'BULLISH':
        for ob in order_blocks:
            if (ob['type'] == 'BULLISH_OB' and 
                ob['low'] <= current_price <= ob['high']):
                
                # Check có FVG hỗ trợ không
                for fvg in fvgs:
                    if (fvg['type'] == 'BULLISH_FVG' and 
                        fvg['low'] <= current_price <= fvg['high']):
                        
                        entry_signal = {
                            'direction': 'LONG',
                            'entry_price': current_price,
                            'stop_loss': ob['low'] * 0.999,  # SL dưới OB
                            'take_profit': current_price * 1.02,  # TP 2%
                            'reason': 'Bullish OB + FVG confluence'
                        }
                        break
    
    # BEARISH SETUP: Downtrend + Bearish OB + có FVG resistance        
    elif structure['trend'] == 'BEARISH':
        for ob in order_blocks:
            if (ob['type'] == 'BEARISH_OB' and 
                ob['low'] <= current_price <= ob['high']):
                
                for fvg in fvgs:
                    if (fvg['type'] == 'BEARISH_FVG' and
                        fvg['low'] <= current_price <= fvg['high']):
                        
                        entry_signal = {
                            'direction': 'SHORT',
                            'entry_price': current_price,
                            'stop_loss': ob['high'] * 1.001,  # SL trên OB
                            'take_profit': current_price * 0.98,  # TP 2%
                            'reason': 'Bearish OB + FVG confluence'
                        }
                        break
    
    return entry_signal

# ======================
# 8️⃣ Order Management Functions
# ======================
def get_account_balance():
    """Lấy số dư tài khoản"""
    try:
        balance_data = session.get_wallet_balance(accountType="UNIFIED")
        account_info = balance_data['result']['list'][0]
        total_balance = float(account_info.get('totalWalletBalance', 0))
        available_balance = float(account_info.get('totalAvailableBalance', 0))
        return {
            'total': total_balance,
            'available': available_balance
        }
    except Exception as e:
        print(f"❌ Lỗi lấy balance: {e}")
        return {'total': 0, 'available': 0}

def calculate_position_size(entry_price, stop_loss, risk_amount):
    """Tính size position dựa trên risk management"""
    try:
        risk_per_unit = abs(entry_price - stop_loss)
        if risk_per_unit > 0:
            quantity = risk_amount / risk_per_unit
            return round(quantity, 6)
        return 0
    except Exception as e:
        print(f"❌ Lỗi tính position size: {e}")
        return 0

def place_order(signal):
    """Đặt lệnh thực tế trên Bybit"""
    if not AUTO_TRADE:
        print("🔒 AUTO_TRADE = False. Chỉ hiển thị signal, không đặt lệnh thật.")
        return False
        
    try:
        # Lấy balance
        total_balance, available_balance = get_account_balance()
        if available_balance < POSITION_SIZE_USDT:
            print(f"❌ Không đủ balance. Cần: ${POSITION_SIZE_USDT}, Có: ${available_balance}")
            return False
        
        # Tính position size
        quantity = calculate_position_size(
            signal['entry_price'], 
            signal['stop_loss'], 
            POSITION_SIZE_USDT
        )
        
        if quantity <= 0:
            print("❌ Position size không hợp lệ")
            return False
        
        print(f"\n📤 Đặt lệnh {signal['direction']}...")
        print(f"   Quantity: {quantity}")
        print(f"   Entry: ${signal['entry_price']}")
        print(f"   SL: ${signal['stop_loss']}")
        print(f"   TP: ${signal['take_profit']}")
        
        # Đặt lệnh market
        side = "Buy" if signal['direction'] == 'LONG' else "Sell"
        
        order_result = session.place_order(
            category="linear",
            symbol=SYMBOL,
            side=side,
            orderType="Market",
            qty=str(quantity),
            leverage=str(LEVERAGE)
        )
        
        if order_result['retCode'] == 0:
            order_id = order_result['result']['orderId']
            print(f"✅ Đặt lệnh thành công! OrderID: {order_id}")
            
            # Đặt Stop Loss
            sl_side = "Sell" if side == "Buy" else "Buy"
            sl_result = session.place_order(
                category="linear",
                symbol=SYMBOL,
                side=sl_side,
                orderType="Market",
                qty=str(quantity),
                stopLoss=str(signal['stop_loss']),
                tpslMode="Full"
            )
            
            # Đặt Take Profit
            tp_result = session.place_order(
                category="linear",
                symbol=SYMBOL,
                side=sl_side,
                orderType="Market", 
                qty=str(quantity),
                takeProfit=str(signal['take_profit']),
                tpslMode="Full"
            )
            
            print("✅ Đặt SL & TP thành công!")
            return True
        else:
            print(f"❌ Lỗi đặt lệnh: {order_result['retMsg']}")
            return False
            
    except Exception as e:
        print(f"❌ Lỗi place_order: {e}")
        return False

def get_open_positions():
    """Lấy danh sách positions đang mở"""
    try:
        positions = session.get_positions(category="linear", symbol=SYMBOL)
        if positions['retCode'] == 0:
            return positions['result']['list']
        return []
    except Exception as e:
        print(f"❌ Lỗi lấy positions: {e}")
        return []

# ======================
# 9️⃣ Main Trading Loop
# ======================
def main_trading_loop():
    """Main loop cho SMC trading bot"""
    print(f"🤖 Bắt đầu SMC Trading Bot cho {SYMBOL}")
    
    while True:
        try:
            # Lấy dữ liệu mới
            df = get_candles(SYMBOL, TIMEFRAME, CANDLES_LIMIT)
            if df is None:
                time.sleep(60)
                continue
                
            # Lấy giá hiện tại
            current_price = float(df.iloc[-1]['close'])
            
            # Check entry signal
            signal = check_smc_entry(df, current_price)
            
            if signal:
                print(f"\n🚨 ENTRY SIGNAL: {signal['direction']}")
                print(f"   Entry: ${signal['entry_price']:,.2f}")
                print(f"   SL: ${signal['stop_loss']:,.2f}")
                print(f"   TP: ${signal['take_profit']:,.2f}")
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
                
                if rr_ratio >= MIN_RR_RATIO:
                    print("✅ RR ratio tốt!")
                    
                    if AUTO_TRADE:
                        # Kiểm tra balance
                        balance = get_account_balance()
                        if balance and balance['available'] > POSITION_SIZE_USDT:
                            
                            # Kiểm tra không có position nào đang mở
                            current_positions = get_current_positions()
                            if len(current_positions) == 0:
                                
                                # Tính position size
                                quantity = calculate_position_size(
                                    signal['entry_price'], 
                                    signal['stop_loss'],
                                    POSITION_SIZE_USDT
                                )
                                
                                if quantity and quantity > 0:
                                    print(f"📊 Position size: {quantity} {SYMBOL}")
                                    print("🚀 Đang đặt lệnh tự động...")
                                    
                                    # Đặt lệnh thực tế
                                    order_result = place_market_order(
                                        signal['direction'],
                                        quantity,
                                        signal['stop_loss'],
                                        signal['take_profit']
                                    )
                                    
                                    if order_result['success']:
                                        print("✅ Đã đặt lệnh thành công!")
                                        print(f"📝 Order ID: {order_result['order_id']}")
                                    else:
                                        print(f"❌ Đặt lệnh thất bại: {order_result['error']}")
                                else:
                                    print("❌ Không thể tính position size")
                            else:
                                print("⚠️ Đã có position đang mở - bỏ qua signal")
                        else:
                            print("❌ Balance không đủ để trade")
                    else:
                        print("💡 AUTO_TRADE = False - chỉ báo signal")
                else:
                    print("❌ RR ratio không đủ tốt")
            else:
                print("⏳ Chưa có signal - tiếp tục monitor...")
            
            # Đợi 1 phút trước khi check lại
            print(f"\n💤 Đợi 60s... (Next check: {datetime.now() + timedelta(seconds=60)})")
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("\n🛑 Dừng bot...")
            break
        except Exception as e:
            print(f"❌ Lỗi: {e}")
            time.sleep(60)

# ======================
# 🚀 Chạy bot (Optimized)
# ======================
if __name__ == "__main__":
    print("🧪 Test nhanh SMC bot...")
    
    try:
        # Test connection đơn giản trước
        print("📡 Kiểm tra kết nối API...")
        test_ticker = session.get_tickers(category="linear", symbol=SYMBOL)
        current_price = float(test_ticker['result']['list'][0]['lastPrice'])
        print(f"✅ Kết nối OK - Giá {SYMBOL}: ${current_price:,.2f}")
        
        # Lấy ít dữ liệu hơn để test nhanh (chỉ 50 candles)
        print("📊 Lấy dữ liệu candles...")
        df = get_candles(SYMBOL, TIMEFRAME, 50)  # Giảm từ 200 xuống 50
        
        if df is not None and len(df) > 10:
            print("✅ Dữ liệu OK")
            
            # Quick analysis
            print("🔍 Phân tích nhanh...")
            signal = check_smc_entry(df, current_price)
            
            if signal:
                print(f"\n🚨 CỮ SIGNAL: {signal['direction']}")
                print(f"💰 Entry: ${signal['entry_price']:,.2f}")
                print(f"🛑 SL: ${signal['stop_loss']:,.2f}")  
                print(f"🎯 TP: ${signal['take_profit']:,.2f}")
                print(f"📝 Lý do: {signal['reason']}")
            else:
                print("⏳ Chưa có signal SMC")
            
            # Kiểm tra balance
            balance = get_account_balance()
            if balance:
                print(f"💰 Balance: {balance['available']:.2f} USDT khả dụng")
            
            print("\n✅ Test hoàn tất!")
            
            # Hỏi user có muốn chạy live không
            if signal:
                run_live = input("🤖 Có signal! Chạy live trading? (y/n): ")
            else:
                run_live = input("🤖 Chạy live trading để monitor? (y/n): ")
                
            if run_live.lower() == 'y':
                print(f"🚀 Bắt đầu live trading...")
                print(f"⚙️ AUTO_TRADE: {AUTO_TRADE}")
                print(f"💰 Position Size: {POSITION_SIZE_USDT} USDT")
                print(f"🎯 Min RR: 1:{MIN_RR_RATIO}")
                print("🛑 Nhấn Ctrl+C để dừng\n")
                
                main_trading_loop()
            else:
                print("👋 Tạm dừng. Bot sẵn sàng khi bạn cần!")
            
        else:
            print("❌ Không đủ dữ liệu để phân tích")
            
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        print("🔧 Kiểm tra API key và kết nối mạng")