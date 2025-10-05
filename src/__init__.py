"""
SMC Trading Bot - Professional Trading System
============================================

Kiến trúc modular cho trading bot sử dụng Smart Money Concept.

Modules:
- data_feed: Real-time market data management
- strategy: Trading strategy logic và signals  
- risk_management: Position sizing và risk controls
- order_manager: Order execution và tracking
- backtest: Historical testing engine
- monitoring: Logging, metrics và alerts

Author: SMC Trading Team
Version: 2.0.0
"""

__version__ = "2.0.0"
__author__ = "SMC Trading Team"

# Import main components
from .data_feed.market_data import MarketDataFeed
from .strategy.base_strategy import BaseStrategy
from .strategy.smc_strategy import SMCStrategy
from .risk_management.risk_manager import RiskManager
from .order_manager.order_manager import OrderManager
from .monitoring.logger import TradingLogger
from .monitoring.metrics import PerformanceMetrics

__all__ = [
    'MarketDataFeed',
    'BaseStrategy', 
    'SMCStrategy',
    'RiskManager',
    'OrderManager',
    'TradingLogger',
    'PerformanceMetrics'
]