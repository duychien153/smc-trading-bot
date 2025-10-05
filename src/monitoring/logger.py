"""
Trading Logger - Hệ thống logging chuyên nghiệp cho trading bot
"""
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any
import json


class TradingLogger:
    """
    Logger chuyên dụng cho trading system
    
    Features:
    - Multiple log levels
    - File và console output
    - Trade-specific formatting
    - Performance metrics logging
    - Error tracking
    """
    
    def __init__(self, name: str, log_dir: str = "logs"):
        self.name = name
        self.log_dir = log_dir
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Thiết lập logger"""
        # Tạo logs directory
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Tạo logger
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.DEBUG)
        
        # Tránh duplicate handlers
        if logger.handlers:
            return logger
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler cho tất cả logs
        today = datetime.now().strftime('%Y-%m-%d')
        file_handler = logging.FileHandler(
            os.path.join(self.log_dir, f'trading_{today}.log')
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Error file handler
        error_handler = logging.FileHandler(
            os.path.join(self.log_dir, f'errors_{today}.log')
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
        
        return logger
    
    def debug(self, message: str, extra: Optional[Dict] = None):
        """Debug level logging"""
        self._log(logging.DEBUG, message, extra)
    
    def info(self, message: str, extra: Optional[Dict] = None):
        """Info level logging"""
        self._log(logging.INFO, message, extra)
    
    def warning(self, message: str, extra: Optional[Dict] = None):
        """Warning level logging"""
        self._log(logging.WARNING, message, extra)
    
    def error(self, message: str, extra: Optional[Dict] = None):
        """Error level logging"""
        self._log(logging.ERROR, message, extra)
    
    def critical(self, message: str, extra: Optional[Dict] = None):
        """Critical level logging"""
        self._log(logging.CRITICAL, message, extra)
    
    def trade_log(self, action: str, symbol: str, side: str, 
                  quantity: float, price: float, **kwargs):
        """Log giao dịch"""
        trade_data = {
            'action': action,
            'symbol': symbol, 
            'side': side,
            'quantity': quantity,
            'price': price,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        
        message = f"TRADE: {action} {side} {quantity} {symbol} @ ${price:.2f}"
        self.info(message, {'trade_data': trade_data})
    
    def signal_log(self, signal_type: str, symbol: str, confidence: float, 
                   reason: str, **kwargs):
        """Log tín hiệu trading"""
        signal_data = {
            'signal_type': signal_type,
            'symbol': symbol,
            'confidence': confidence,
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        
        message = f"SIGNAL: {signal_type} {symbol} ({confidence:.1f}%) - {reason}"
        self.info(message, {'signal_data': signal_data})
    
    def performance_log(self, metrics: Dict[str, Any]):
        """Log performance metrics"""
        message = "PERFORMANCE: " + " | ".join([
            f"{k}: {v}" for k, v in metrics.items()
        ])
        self.info(message, {'performance_data': metrics})
    
    def _log(self, level: int, message: str, extra: Optional[Dict] = None):
        """Internal logging method"""
        if extra:
            # Thêm extra data vào message nếu cần
            extra_str = json.dumps(extra, indent=2) if extra else ""
            full_message = f"{message}\nExtra: {extra_str}" if extra_str else message
        else:
            full_message = message
        
        self.logger.log(level, full_message)


# Global logger instance
default_logger = TradingLogger("SMCBot")

# Convenience functions
def log_info(message: str, extra: Optional[Dict] = None):
    """Quick info logging"""
    default_logger.info(message, extra)

def log_error(message: str, extra: Optional[Dict] = None):
    """Quick error logging"""
    default_logger.error(message, extra)

def log_trade(action: str, symbol: str, side: str, quantity: float, price: float, **kwargs):
    """Quick trade logging"""
    default_logger.trade_log(action, symbol, side, quantity, price, **kwargs)

def log_signal(signal_type: str, symbol: str, confidence: float, reason: str, **kwargs):
    """Quick signal logging"""
    default_logger.signal_log(signal_type, symbol, confidence, reason, **kwargs)