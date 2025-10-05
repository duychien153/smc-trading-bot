"""
Performance Metrics - Theo dõi hiệu suất trading
"""
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import pandas as pd
import numpy as np

from ..models import Trade, BacktestResult
from .logger import TradingLogger


@dataclass
class PerformanceSnapshot:
    """Snapshot hiệu suất tại một thời điểm"""
    timestamp: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: float
    unrealized_pnl: float
    balance: float
    max_drawdown: float
    win_rate: float
    avg_win: float
    avg_loss: float
    sharpe_ratio: float
    
    @property
    def profit_factor(self) -> float:
        """Profit Factor = Tổng lãi / Tổng lỗ"""
        if self.losing_trades == 0:
            return float('inf') if self.winning_trades > 0 else 0
        
        total_wins = self.winning_trades * self.avg_win
        total_losses = abs(self.losing_trades * self.avg_loss)
        return total_wins / total_losses if total_losses > 0 else 0


class PerformanceMetrics:
    """
    Theo dõi và tính toán metrics hiệu suất trading
    
    Features:
    - Real-time P&L tracking
    - Win rate calculation  
    - Drawdown monitoring
    - Sharpe ratio
    - Risk-adjusted returns
    """
    
    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.logger = TradingLogger("Metrics")
        
        # Trade history
        self.trades: List[Trade] = []
        self.balance_history: List[Tuple[datetime, float]] = []
        self.drawdown_history: List[Tuple[datetime, float]] = []
        
        # Running metrics
        self.peak_balance = initial_balance
        self.max_drawdown = 0.0
        self.start_time = datetime.now()
        
        # Add initial balance point
        self.balance_history.append((self.start_time, initial_balance))
    
    def add_trade(self, trade: Trade, current_balance: float):
        """Thêm trade mới và cập nhật metrics"""
        self.trades.append(trade)
        self.current_balance = current_balance
        
        # Update balance history
        self.balance_history.append((trade.timestamp, current_balance))
        
        # Update peak and drawdown
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
        
        current_drawdown = (self.peak_balance - current_balance) / self.peak_balance
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
        
        self.drawdown_history.append((trade.timestamp, current_drawdown))
        
        # Log trade
        pnl = self._calculate_trade_pnl(trade)
        self.logger.trade_log(
            "FILL",
            trade.symbol,
            trade.side.value,
            trade.quantity,
            trade.price,
            pnl=pnl,
            balance=current_balance
        )
    
    def get_current_metrics(self) -> PerformanceSnapshot:
        """Lấy metrics hiện tại"""
        if not self.trades:
            return PerformanceSnapshot(
                timestamp=datetime.now(),
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                total_pnl=0,
                unrealized_pnl=0,
                balance=self.current_balance,
                max_drawdown=0,
                win_rate=0,
                avg_win=0,
                avg_loss=0,
                sharpe_ratio=0
            )
        
        # Tính toán basic metrics
        winning_trades = 0
        losing_trades = 0
        total_wins = 0
        total_losses = 0
        
        for trade in self.trades:
            pnl = self._calculate_trade_pnl(trade)
            if pnl > 0:
                winning_trades += 1
                total_wins += pnl
            elif pnl < 0:
                losing_trades += 1
                total_losses += abs(pnl)
        
        total_trades = len(self.trades)
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        avg_win = total_wins / winning_trades if winning_trades > 0 else 0
        avg_loss = total_losses / losing_trades if losing_trades > 0 else 0
        
        total_pnl = self.current_balance - self.initial_balance
        sharpe_ratio = self._calculate_sharpe_ratio()
        
        return PerformanceSnapshot(
            timestamp=datetime.now(),
            total_trades=total_trades,
            winning_trades=winning_trades, 
            losing_trades=losing_trades,
            total_pnl=total_pnl,
            unrealized_pnl=0,  # TODO: Calculate from open positions
            balance=self.current_balance,
            max_drawdown=self.max_drawdown * 100,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            sharpe_ratio=sharpe_ratio
        )
    
    def get_daily_summary(self) -> Dict:
        """Tóm tắt hiệu suất hôm nay"""
        today = datetime.now().date()
        today_trades = [
            trade for trade in self.trades 
            if trade.timestamp.date() == today
        ]
        
        if not today_trades:
            return {
                'date': today.isoformat(),
                'trades': 0,
                'pnl': 0,
                'win_rate': 0
            }
        
        total_pnl = sum(self._calculate_trade_pnl(trade) for trade in today_trades)
        winning_trades = sum(1 for trade in today_trades if self._calculate_trade_pnl(trade) > 0)
        win_rate = (winning_trades / len(today_trades)) * 100
        
        return {
            'date': today.isoformat(),
            'trades': len(today_trades),
            'pnl': total_pnl,
            'win_rate': win_rate,
            'balance': self.current_balance
        }
    
    def get_performance_report(self) -> str:
        """Báo cáo hiệu suất formatted"""
        metrics = self.get_current_metrics()
        
        report = f"""
📊 PERFORMANCE REPORT - {metrics.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}
💰 Balance: ${metrics.balance:,.2f} (Start: ${self.initial_balance:,.2f})
📈 Total P&L: ${metrics.total_pnl:,.2f} ({(metrics.total_pnl/self.initial_balance)*100:+.2f}%)
📊 Total Trades: {metrics.total_trades} (Win: {metrics.winning_trades}, Loss: {metrics.losing_trades})
🎯 Win Rate: {metrics.win_rate:.1f}%
💵 Avg Win: ${metrics.avg_win:.2f} | Avg Loss: ${metrics.avg_loss:.2f}
📉 Max Drawdown: {metrics.max_drawdown:.2f}%
⚡ Sharpe Ratio: {metrics.sharpe_ratio:.2f}
🔥 Profit Factor: {metrics.profit_factor:.2f}
⏱️ Runtime: {datetime.now() - self.start_time}
"""
        return report
    
    def _calculate_trade_pnl(self, trade: Trade) -> float:
        """Tính P&L của một trade"""
        # TODO: Implement based on position tracking
        # For now, assume simple calculation
        return 0.0
    
    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Tính Sharpe Ratio"""
        if len(self.balance_history) < 2:
            return 0.0
        
        # Tính returns
        balances = [balance for _, balance in self.balance_history]
        returns = pd.Series(balances).pct_change().dropna()
        
        if returns.empty or returns.std() == 0:
            return 0.0
        
        # Annualized metrics
        mean_return = returns.mean() * 252  # Daily to annual
        volatility = returns.std() * np.sqrt(252)
        
        return (mean_return - risk_free_rate) / volatility if volatility > 0 else 0.0
    
    def export_trades_to_csv(self, filename: Optional[str] = None) -> str:
        """Export trades ra CSV file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"logs/trades_{timestamp}.csv"
        
        if not self.trades:
            self.logger.warning("Không có trades để export")
            return filename
        
        # Convert trades to DataFrame
        trades_data = []
        for trade in self.trades:
            trades_data.append({
                'timestamp': trade.timestamp,
                'symbol': trade.symbol,
                'side': trade.side.value,
                'quantity': trade.quantity,
                'price': trade.price,
                'commission': trade.commission,
                'pnl': self._calculate_trade_pnl(trade)
            })
        
        df = pd.DataFrame(trades_data)
        df.to_csv(filename, index=False)
        
        self.logger.info(f"Exported {len(trades_data)} trades to {filename}")
        return filename
    
    def reset_metrics(self):
        """Reset tất cả metrics"""
        self.trades.clear()
        self.balance_history.clear()
        self.drawdown_history.clear()
        self.current_balance = self.initial_balance
        self.peak_balance = self.initial_balance
        self.max_drawdown = 0.0
        self.start_time = datetime.now()
        self.balance_history.append((self.start_time, self.initial_balance))
        
        self.logger.info("Reset performance metrics")


# Singleton instance
performance_tracker = PerformanceMetrics()