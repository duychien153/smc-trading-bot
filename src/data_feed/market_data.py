"""
Market Data Feed - Quản lý dữ liệu thị trường real-time
"""
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
import pandas as pd
from pybit.unified_trading import HTTP

from ..models import Candle, MarketData
from ..monitoring.logger import TradingLogger


class MarketDataFeed:
    """
    Quản lý feed dữ liệu thị trường từ Bybit API
    
    Features:
    - Real-time price updates
    - Candle data caching  
    - Data validation
    - Retry mechanism
    - Rate limit handling
    """
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.session = None
        self.logger = TradingLogger("DataFeed")
        
        # Data cache
        self.candle_cache: Dict[str, pd.DataFrame] = {}
        self.market_data_cache: Dict[str, MarketData] = {}
        
        # Callbacks
        self.price_callbacks: List[Callable] = []
        self.candle_callbacks: List[Callable] = []
        
        # Threading
        self.is_running = False
        self.update_thread = None
        
        self._connect()
    
    def _connect(self):
        """Kết nối đến Bybit API"""
        try:
            self.session = HTTP(
                testnet=self.testnet,
                api_key=self.api_key,
                api_secret=self.api_secret
            )
            self.logger.info("Kết nối Bybit API thành công")
        except Exception as e:
            self.logger.error(f"Lỗi kết nối API: {e}")
            raise
    
    def get_candles(self, symbol: str, interval: str = "15", limit: int = 100) -> pd.DataFrame:
        """
        Lấy dữ liệu nến từ API
        
        Args:
            symbol: Cặp giao dịch (BTCUSDT)
            interval: Khung thời gian (1, 5, 15, 60, 240, D)
            limit: Số nến (tối đa 1000)
            
        Returns:
            DataFrame với columns: timestamp, open, high, low, close, volume
        """
        try:
            cache_key = f"{symbol}_{interval}_{limit}"
            
            # Kiểm tra cache (cache 30s)
            if cache_key in self.candle_cache:
                cached_df = self.candle_cache[cache_key]
                if not cached_df.empty:
                    last_update = cached_df.attrs.get('last_update', datetime.min)
                    if datetime.now() - last_update < timedelta(seconds=30):
                        return cached_df
            
            # Lấy data từ API với retry
            response = self._retry_api_call(
                self.session.get_kline,
                category="linear",
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            if not response or response.get('retCode') != 0:
                self.logger.error(f"Lỗi lấy dữ liệu nến: {response}")
                return pd.DataFrame()
            
            # Convert sang DataFrame
            candles_data = response['result']['list']
            df = pd.DataFrame(candles_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
            ])
            
            # Data processing
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # Validation
            if not self._validate_candle_data(df):
                self.logger.warning("Dữ liệu nến không hợp lệ")
                return pd.DataFrame()
            
            # Cache data
            df.attrs['last_update'] = datetime.now()
            self.candle_cache[cache_key] = df
            
            self.logger.debug(f"Lấy {len(df)} nến cho {symbol} thành công")
            return df
            
        except Exception as e:
            self.logger.error(f"Lỗi get_candles: {e}")
            return pd.DataFrame()
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Lấy giá hiện tại"""
        try:
            response = self._retry_api_call(
                self.session.get_tickers,
                category="linear", 
                symbol=symbol
            )
            
            if response and response.get('retCode') == 0:
                ticker_data = response['result']['list'][0]
                return float(ticker_data['lastPrice'])
            
        except Exception as e:
            self.logger.error(f"Lỗi lấy giá hiện tại: {e}")
        
        return None
    
    def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Lấy thông tin thị trường đầy đủ"""
        try:
            response = self._retry_api_call(
                self.session.get_tickers,
                category="linear",
                symbol=symbol
            )
            
            if not response or response.get('retCode') != 0:
                return None
            
            ticker = response['result']['list'][0]
            
            market_data = MarketData(
                symbol=symbol,
                current_price=float(ticker['lastPrice']),
                bid=float(ticker['bid1Price']) if ticker.get('bid1Price') else 0,
                ask=float(ticker['ask1Price']) if ticker.get('ask1Price') else 0,
                volume_24h=float(ticker['volume24h']) if ticker.get('volume24h') else 0,
                change_24h=float(ticker['price24hPcnt']) if ticker.get('price24hPcnt') else 0
            )
            
            # Cache
            self.market_data_cache[symbol] = market_data
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"Lỗi lấy market data: {e}")
            return None
    
    def start_real_time_updates(self, symbols: List[str], interval: int = 5):
        """
        Bắt đầu cập nhật dữ liệu real-time
        
        Args:
            symbols: Danh sách symbols cần theo dõi
            interval: Khoảng thời gian cập nhật (giây)
        """
        if self.is_running:
            self.logger.warning("Real-time updates đã đang chạy")
            return
        
        self.is_running = True
        self.symbols_to_track = symbols
        self.update_interval = interval
        
        self.update_thread = threading.Thread(
            target=self._update_loop,
            daemon=True
        )
        self.update_thread.start()
        
        self.logger.info(f"Bắt đầu real-time updates cho {symbols}")
    
    def stop_real_time_updates(self):
        """Dừng cập nhật real-time"""
        self.is_running = False
        if self.update_thread:
            self.update_thread.join()
        self.logger.info("Dừng real-time updates")
    
    def add_price_callback(self, callback: Callable):
        """Thêm callback khi có cập nhật giá"""
        self.price_callbacks.append(callback)
    
    def add_candle_callback(self, callback: Callable):
        """Thêm callback khi có nến mới"""
        self.candle_callbacks.append(callback)
    
    def _update_loop(self):
        """Vòng lặp cập nhật dữ liệu"""
        while self.is_running:
            try:
                for symbol in self.symbols_to_track:
                    # Cập nhật market data
                    market_data = self.get_market_data(symbol)
                    if market_data:
                        for callback in self.price_callbacks:
                            try:
                                callback(market_data)
                            except Exception as e:
                                self.logger.error(f"Lỗi price callback: {e}")
                    
                    # Cập nhật candle data (mỗi phút)
                    if int(time.time()) % 60 == 0:
                        candles = self.get_candles(symbol, "1", 2)  # 2 nến gần nhất
                        if not candles.empty:
                            for callback in self.candle_callbacks:
                                try:
                                    callback(symbol, candles)
                                except Exception as e:
                                    self.logger.error(f"Lỗi candle callback: {e}")
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"Lỗi update loop: {e}")
                time.sleep(5)
    
    def _validate_candle_data(self, df: pd.DataFrame) -> bool:
        """Validation dữ liệu nến"""
        if df.empty:
            return False
        
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            return False
        
        # Kiểm tra OHLC logic
        invalid_rows = (
            (df['high'] < df[['open', 'close']].max(axis=1)) |
            (df['low'] > df[['open', 'close']].min(axis=1)) |
            (df['high'] < df['low'])
        )
        
        if invalid_rows.any():
            self.logger.warning(f"Phát hiện {invalid_rows.sum()} nến không hợp lệ")
            return False
        
        return True
    
    def _retry_api_call(self, func, max_retries: int = 3, **kwargs):
        """Retry API call với exponential backoff"""
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = 2 ** attempt
                    self.logger.debug(f"Retry {attempt + 1}, chờ {delay}s...")
                    time.sleep(delay)
                
                result = func(**kwargs)
                return result
                
            except Exception as e:
                error_msg = str(e)
                self.logger.warning(f"API call attempt {attempt + 1} failed: {error_msg}")
                
                if attempt == max_retries - 1:
                    raise e
        
        return None
    
    def get_cache_info(self) -> Dict:
        """Thông tin cache hiện tại"""
        return {
            'candle_cache_keys': list(self.candle_cache.keys()),
            'market_data_cache': list(self.market_data_cache.keys()),
            'is_running': self.is_running
        }