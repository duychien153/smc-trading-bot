"""
Base models và data types cho trading system
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
import pandas as pd


class OrderSide(Enum):
    """Hướng lệnh"""
    BUY = "Buy"
    SELL = "Sell"


class OrderType(Enum):
    """Loại lệnh"""
    MARKET = "Market"
    LIMIT = "Limit" 
    STOP = "Stop"
    STOP_LIMIT = "StopLimit"


class OrderStatus(Enum):
    """Trạng thái lệnh"""
    NEW = "New"
    PARTIALLY_FILLED = "PartiallyFilled"
    FILLED = "Filled"
    CANCELLED = "Cancelled"
    REJECTED = "Rejected"


class SignalType(Enum):
    """Loại tín hiệu trading"""
    LONG = "LONG"
    SHORT = "SHORT"
    CLOSE_LONG = "CLOSE_LONG"
    CLOSE_SHORT = "CLOSE_SHORT" 
    HOLD = "HOLD"


class MarketStructure(Enum):
    """Cấu trúc thị trường SMC"""
    BULLISH_BOS = "BULLISH_BOS"
    BEARISH_BOS = "BEARISH_BOS"
    BULLISH_CHOCH = "BULLISH_CHOCH"
    BEARISH_CHOCH = "BEARISH_CHOCH"
    NEUTRAL = "NEUTRAL"


@dataclass
class Candle:
    """Dữ liệu nến"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str


@dataclass  
class OrderBlock:
    """Order Block SMC"""
    type: str  # BULLISH_OB, BEARISH_OB
    high: float
    low: float
    timestamp: datetime
    volume: float
    confidence: float


@dataclass
class FairValueGap:
    """Fair Value Gap"""
    type: str  # BULLISH_FVG, BEARISH_FVG
    high: float
    low: float
    timestamp: datetime
    filled: bool = False


@dataclass
class TradingSignal:
    """Tín hiệu trading"""
    signal_type: SignalType
    symbol: str
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    confidence: float = 0.0
    reason: str = ""
    timestamp: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Position:
    """Vị thế giao dịch"""
    symbol: str
    side: OrderSide
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    timestamp: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


@dataclass
class Order:
    """Lệnh giao dịch"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.NEW
    filled_quantity: float = 0.0
    avg_fill_price: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class Trade:
    """Giao dịch đã thực hiện"""
    trade_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    commission: float
    timestamp: datetime
    order_id: str


@dataclass
class AccountInfo:
    """Thông tin tài khoản"""
    total_balance: float
    available_balance: float
    unrealized_pnl: float
    margin_used: float
    positions: List[Position]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class MarketData:
    """Dữ liệu thị trường"""
    symbol: str
    current_price: float
    bid: float
    ask: float
    volume_24h: float
    change_24h: float
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class BacktestResult:
    """Kết quả backtest"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    
    @property
    def total_return(self) -> float:
        """Tổng lợi nhuận %"""
        return (self.final_capital - self.initial_capital) / self.initial_capital * 100


class TradingMode(Enum):
    """Chế độ trading"""
    PAPER = "paper"      # Paper trading - không đặt lệnh thật
    LIVE = "live"        # Live trading - đặt lệnh thật
    BACKTEST = "backtest"  # Backtest với dữ liệu lịch sử