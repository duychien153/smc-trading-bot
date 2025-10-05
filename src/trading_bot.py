"""
Main Trading Bot v2.0 - Orchestrator kết nối tất cả modules
"""
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import os
from dataclasses import dataclass

from src.data_feed.market_data import MarketDataFeed
from src.strategy.smc_strategy import SMCStrategy
from src.risk_management.risk_manager import RiskManager, RiskConfig
from src.order_manager.order_manager import OrderManager
from src.monitoring.logger import TradingLogger
from src.monitoring.metrics import PerformanceMetrics
from src.models import TradingMode, AccountInfo, TradingSignal


@dataclass
class BotConfig:
    """Cấu hình cho trading bot"""
    # API Settings
    api_key: str
    api_secret: str
    testnet: bool = True
    
    # Trading Settings  
    symbol: str = "BTCUSDT"
    trading_mode: TradingMode = TradingMode.PAPER
    update_interval: int = 15  # giây
    
    # Strategy Config
    strategy_config: Dict = None
    risk_config: RiskConfig = None
    
    # Bot Behavior
    auto_trade: bool = False
    max_daily_trades: int = 10
    trading_hours: tuple = (0, 24)  # 24/7


class TradingBotV2:
    """
    Trading Bot v2.0 - Professional Architecture
    
    Kết nối tất cả modules:
    - Data Feed: Real-time market data
    - Strategy: SMC signal generation  
    - Risk Manager: Position sizing & risk control
    - Order Manager: Order execution & tracking
    - Monitoring: Logging & performance metrics
    """
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.logger = TradingLogger("TradingBotV2")
        
        # Bot state
        self.is_running = False
        self.last_signal_time = None
        self.daily_trades = 0
        self.daily_reset_time = datetime.now().date()
        
        # Initialize modules
        self._initialize_modules()
        
        self.logger.info(f"🚀 Trading Bot v2.0 initialized - Mode: {config.trading_mode.value}")
    
    def _initialize_modules(self):
        """Khởi tạo tất cả modules"""
        try:
            # Data Feed
            self.data_feed = MarketDataFeed(
                self.config.api_key,
                self.config.api_secret,
                self.config.testnet
            )
            
            # Strategy
            strategy_config = self.config.strategy_config or {
                'required_history': 100,
                'min_confidence': 75.0,
                'stop_loss_pct': 1.5,
                'take_profit_pct': 2.5
            }
            
            self.strategy = SMCStrategy(self.config.symbol, strategy_config)
            
            # Risk Manager
            risk_config = self.config.risk_config or RiskConfig()
            self.risk_manager = RiskManager(risk_config)
            
            # Order Manager
            self.order_manager = OrderManager(
                self.config.api_key,
                self.config.api_secret,
                self.config.testnet,
                self.config.trading_mode
            )
            
            # Performance Metrics
            initial_balance = 10000.0 if self.config.trading_mode == TradingMode.PAPER else None
            self.performance = PerformanceMetrics(initial_balance)
            
            self.logger.info("✅ Tất cả modules đã được khởi tạo")
            
        except Exception as e:
            self.logger.error(f"❌ Lỗi khởi tạo modules: {e}")
            raise
    
    def start(self):
        """Bắt đầu trading bot"""
        if self.is_running:
            self.logger.warning("Bot đã đang chạy")
            return
        
        self.is_running = True
        self.logger.info("🚀 Bắt đầu Trading Bot v2.0")
        
        # Start main loop in thread
        self.main_thread = threading.Thread(target=self._main_loop, daemon=True)
        self.main_thread.start()
        
        # Start data feed updates
        self.data_feed.start_real_time_updates([self.config.symbol])
        
        self.logger.info("✅ Trading bot đã khởi động")
    
    def stop(self):
        """Dừng trading bot"""
        self.is_running = False
        self.data_feed.stop_real_time_updates()
        
        if hasattr(self, 'main_thread'):
            self.main_thread.join()
        
        self.logger.info("🛑 Trading bot đã dừng")
    
    def _main_loop(self):
        """Vòng lặp chính của bot"""
        self.logger.info("📊 Bắt đầu main trading loop")
        
        while self.is_running:
            try:
                # Reset daily counter
                self._check_daily_reset()
                
                # Check trading hours
                if not self._is_trading_hours():
                    time.sleep(60)
                    continue
                
                # Get market data
                candles = self.data_feed.get_candles(
                    self.config.symbol, 
                    self.strategy.get_timeframe(),
                    self.strategy.get_required_history()
                )
                
                market_data = self.data_feed.get_market_data(self.config.symbol)
                
                if candles.empty or not market_data:
                    self.logger.warning("Không có dữ liệu thị trường")
                    time.sleep(self.config.update_interval)
                    continue
                
                # Process signal
                signal = self.strategy.process_signal(candles, market_data)
                
                if signal and self.config.auto_trade:
                    self._handle_trading_signal(signal)
                
                # Log status periodically
                self._log_status()
                
                time.sleep(self.config.update_interval)
                
            except Exception as e:
                self.logger.error(f"Lỗi trong main loop: {e}")
                time.sleep(30)  # Wait before retry
    
    def _handle_trading_signal(self, signal: TradingSignal):
        """Xử lý trading signal"""
        try:
            # Check daily limits
            if self.daily_trades >= self.config.max_daily_trades:
                self.logger.warning(f"Đã đạt giới hạn trades hôm nay: {self.daily_trades}")
                return
            
            # Check signal timing (avoid spam)
            if (self.last_signal_time and 
                datetime.now() - self.last_signal_time < timedelta(minutes=5)):
                return
            
            # Get account info
            account_info = self._get_account_info()
            if not account_info:
                self.logger.error("Không lấy được thông tin tài khoản")
                return
            
            # Calculate position size
            position_size, risk_analysis = self.risk_manager.calculate_position_size(
                signal, account_info
            )
            
            if position_size <= 0:
                self.logger.warning(f"Position size không hợp lệ: {position_size}")
                return
            
            # Validate risk
            is_valid, reason = self.risk_manager.validate_risk_before_trade(
                position_size, signal, account_info
            )
            
            if not is_valid:
                self.logger.warning(f"Risk validation failed: {reason}")
                return
            
            # Execute order
            success = self._execute_signal(signal, position_size)
            
            if success:
                self.daily_trades += 1
                self.last_signal_time = datetime.now()
                
                self.logger.info(f"✅ Signal executed successfully - Daily trades: {self.daily_trades}")
            
        except Exception as e:
            self.logger.error(f"Lỗi handle signal: {e}")
    
    def _execute_signal(self, signal: TradingSignal, position_size: float) -> bool:
        """Thực thi signal"""
        try:
            from src.models import OrderSide
            
            # Determine order side
            if signal.signal_type.value == "LONG":
                side = OrderSide.BUY
            elif signal.signal_type.value == "SHORT":
                side = OrderSide.SELL
            else:
                return False
            
            # Place order
            order = self.order_manager.place_market_order(
                symbol=signal.symbol,
                side=side,
                quantity=position_size,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit
            )
            
            if order:
                self.logger.info(
                    f"🎯 Order placed: {side.value} {position_size} {signal.symbol} "
                    f"@ ${signal.entry_price:.2f} (Confidence: {signal.confidence:.1f}%)"
                )
                
                # Log to performance metrics
                self.performance.add_trade(None, 0)  # Will update when filled
                
                return True
            else:
                self.logger.error("Không thể đặt lệnh")
                return False
                
        except Exception as e:
            self.logger.error(f"Lỗi execute signal: {e}")
            return False
    
    def _get_account_info(self) -> Optional[AccountInfo]:
        """Lấy thông tin tài khoản"""
        try:
            if self.config.trading_mode == TradingMode.PAPER:
                # Paper trading account
                positions = self.order_manager.get_positions()
                return AccountInfo(
                    total_balance=self.order_manager.paper_balance,
                    available_balance=self.order_manager.paper_balance,
                    unrealized_pnl=0.0,
                    margin_used=0.0,
                    positions=positions
                )
            else:
                # Real account - implement API call
                # TODO: Implement real account info retrieval
                return None
                
        except Exception as e:
            self.logger.error(f"Lỗi get account info: {e}")
            return None
    
    def _check_daily_reset(self):
        """Reset daily counters"""
        current_date = datetime.now().date()
        if current_date != self.daily_reset_time:
            self.daily_trades = 0
            self.daily_reset_time = current_date
            self.logger.info("🔄 Reset daily counters")
    
    def _is_trading_hours(self) -> bool:
        """Kiểm tra giờ giao dịch"""
        current_hour = datetime.now().hour
        start_hour, end_hour = self.config.trading_hours
        
        if start_hour <= end_hour:
            return start_hour <= current_hour < end_hour
        else:
            return current_hour >= start_hour or current_hour < end_hour
    
    def _log_status(self):
        """Log trạng thái bot định kỳ"""
        # Log every 5 minutes
        if int(time.time()) % 300 == 0:
            
            # Get current metrics
            account_info = self._get_account_info()
            if account_info:
                risk_metrics = self.risk_manager.get_risk_metrics(account_info)
                
                self.logger.info(
                    f"📊 Status: Balance=${account_info.total_balance:.2f} | "
                    f"Positions={len(account_info.positions)} | "
                    f"Daily Trades={self.daily_trades} | "
                    f"Risk={risk_metrics.current_risk_pct:.1f}%"
                )
    
    def get_bot_status(self) -> Dict:
        """Lấy trạng thái bot"""
        account_info = self._get_account_info()
        
        return {
            'is_running': self.is_running,
            'trading_mode': self.config.trading_mode.value,
            'symbol': self.config.symbol,
            'daily_trades': self.daily_trades,
            'auto_trade': self.config.auto_trade,
            'balance': account_info.total_balance if account_info else 0,
            'positions': len(account_info.positions) if account_info else 0,
            'strategy_info': self.strategy.get_strategy_info(),
            'last_signal_time': self.last_signal_time.isoformat() if self.last_signal_time else None
        }
    
    def get_performance_report(self) -> str:
        """Lấy báo cáo hiệu suất"""
        return self.performance.get_performance_report()
    
    def force_signal_check(self):
        """Force check signal (for testing)"""
        self.logger.info("🔍 Force checking signal...")
        
        candles = self.data_feed.get_candles(
            self.config.symbol,
            self.strategy.get_timeframe(), 
            self.strategy.get_required_history()
        )
        
        market_data = self.data_feed.get_market_data(self.config.symbol)
        
        if not candles.empty and market_data:
            signal = self.strategy.process_signal(candles, market_data)
            
            if signal:
                self.logger.info(f"🎯 Signal found: {signal.signal_type.value} ({signal.confidence:.1f}%)")
                return signal
            else:
                self.logger.info("⏳ No signal detected")
        
        return None


def create_bot_from_env() -> TradingBotV2:
    """Tạo bot từ environment variables"""
    from dotenv import load_dotenv
    load_dotenv()
    
    config = BotConfig(
        api_key=os.getenv("API_KEY"),
        api_secret=os.getenv("API_SECRET"),
        testnet=True,
        symbol=os.getenv("SYMBOL", "BTCUSDT"),
        trading_mode=TradingMode.PAPER,  # Start with paper trading
        auto_trade=os.getenv("AUTO_TRADE", "false").lower() == "true"
    )
    
    return TradingBotV2(config)