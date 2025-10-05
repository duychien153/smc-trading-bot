"""
Base Strategy Class - Abstract base cho tất cả trading strategies
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import pandas as pd
from datetime import datetime

from ..models import TradingSignal, MarketData, Candle
from ..monitoring.logger import TradingLogger


class BaseStrategy(ABC):
    """
    Abstract base class cho trading strategies
    
    Tất cả strategies phải implement:
    - generate_signal(): Tạo tín hiệu trading
    - update_data(): Cập nhật dữ liệu mới
    - validate_signal(): Validate tín hiệu trước khi gửi
    """
    
    def __init__(self, name: str, symbol: str, config: Dict[str, Any] = None):
        self.name = name
        self.symbol = symbol
        self.config = config or {}
        self.logger = TradingLogger(f"Strategy-{name}")
        
        # Data storage
        self.candle_data: pd.DataFrame = pd.DataFrame()
        self.market_data: Optional[MarketData] = None
        
        # Strategy state
        self.last_signal: Optional[TradingSignal] = None
        self.last_update: Optional[datetime] = None
        self.is_active = True
        
        # Performance tracking
        self.signals_generated = 0
        self.signals_executed = 0
        
        self.logger.info(f"Khởi tạo strategy {name} cho {symbol}")
    
    @abstractmethod
    def generate_signal(self) -> Optional[TradingSignal]:
        """
        Tạo tín hiệu trading dựa trên dữ liệu hiện tại
        
        Returns:
            TradingSignal hoặc None nếu không có tín hiệu
        """
        pass
    
    @abstractmethod
    def update_data(self, candles: pd.DataFrame, market_data: MarketData):
        """
        Cập nhật dữ liệu mới cho strategy
        
        Args:
            candles: DataFrame chứa OHLCV data
            market_data: Dữ liệu thị trường real-time
        """
        pass
    
    def validate_signal(self, signal: TradingSignal) -> bool:
        """
        Validate tín hiệu trước khi gửi
        
        Args:
            signal: Tín hiệu cần validate
            
        Returns:
            True nếu tín hiệu hợp lệ
        """
        if not signal:
            return False
        
        # Basic validation
        if signal.symbol != self.symbol:
            self.logger.warning(f"Signal symbol {signal.symbol} != strategy symbol {self.symbol}")
            return False
        
        if signal.confidence <= 0:
            self.logger.warning("Signal confidence <= 0")
            return False
        
        if signal.entry_price <= 0:
            self.logger.warning("Invalid entry price")
            return False
        
        # Custom validation
        return self._custom_validation(signal)
    
    def _custom_validation(self, signal: TradingSignal) -> bool:
        """Override để thêm validation logic riêng"""
        return True
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Thông tin về strategy"""
        return {
            'name': self.name,
            'symbol': self.symbol,
            'config': self.config,
            'is_active': self.is_active,
            'last_update': self.last_update,
            'signals_generated': self.signals_generated,
            'signals_executed': self.signals_executed,
            'data_rows': len(self.candle_data),
            'last_signal': {
                'type': self.last_signal.signal_type.value if self.last_signal else None,
                'confidence': self.last_signal.confidence if self.last_signal else None,
                'timestamp': self.last_signal.timestamp if self.last_signal else None
            }
        }
    
    def reset_strategy(self):
        """Reset strategy state"""
        self.candle_data = pd.DataFrame()
        self.market_data = None
        self.last_signal = None
        self.last_update = None
        self.signals_generated = 0
        self.signals_executed = 0
        
        self.logger.info("Strategy state reset")
    
    def set_config(self, config: Dict[str, Any]):
        """Cập nhật config"""
        self.config.update(config)
        self.logger.info(f"Config updated: {config}")
    
    def get_required_history(self) -> int:
        """Số nến lịch sử cần thiết"""
        return self.config.get('required_history', 100)
    
    def get_timeframe(self) -> str:
        """Timeframe strategy sử dụng"""
        return self.config.get('timeframe', '15')
    
    def activate(self):
        """Kích hoạt strategy"""
        self.is_active = True
        self.logger.info("Strategy activated")
    
    def deactivate(self):
        """Tắt strategy"""
        self.is_active = False
        self.logger.info("Strategy deactivated")
    
    def process_signal(self, candles: pd.DataFrame, market_data: MarketData) -> Optional[TradingSignal]:
        """
        Main method để xử lý và tạo tín hiệu
        
        Args:
            candles: OHLCV data
            market_data: Real-time market data
            
        Returns:
            Validated trading signal hoặc None
        """
        if not self.is_active:
            return None
        
        try:
            # Cập nhật data
            self.update_data(candles, market_data)
            self.last_update = datetime.now()
            
            # Tạo tín hiệu
            signal = self.generate_signal()
            
            if signal:
                self.signals_generated += 1
                
                # Validate
                if self.validate_signal(signal):
                    self.last_signal = signal
                    self.logger.info(
                        f"Generated {signal.signal_type.value} signal: "
                        f"confidence={signal.confidence:.1f}%, reason='{signal.reason}'"
                    )
                    return signal
                else:
                    self.logger.warning("Signal validation failed")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error processing signal: {e}")
            return None
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Tính RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_sma(self, prices: pd.Series, period: int) -> pd.Series:
        """Tính Simple Moving Average"""
        return prices.rolling(window=period).mean()
    
    def calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """Tính Exponential Moving Average"""
        return prices.ewm(span=period).mean()
    
    def detect_support_resistance(self, df: pd.DataFrame, window: int = 5) -> Dict:
        """Tìm support/resistance levels"""
        # Simple implementation
        highs = df['high'].rolling(window=window, center=True).max() == df['high']
        lows = df['low'].rolling(window=window, center=True).min() == df['low']
        
        resistance_levels = df.loc[highs, 'high'].dropna().tail(3).tolist()
        support_levels = df.loc[lows, 'low'].dropna().tail(3).tolist()
        
        return {
            'resistance': resistance_levels,
            'support': support_levels
        }