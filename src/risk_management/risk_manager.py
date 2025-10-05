"""
Risk Manager - Quản lý rủi ro và position sizing
"""
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import math

from ..models import TradingSignal, AccountInfo, Position, OrderSide
from ..monitoring.logger import TradingLogger


@dataclass
class RiskConfig:
    """Cấu hình risk management"""
    max_risk_per_trade: float = 1.0  # % vốn tối đa mỗi lệnh
    max_total_risk: float = 5.0      # % tổng risk portfolio
    max_positions: int = 3           # Số positions tối đa
    max_drawdown: float = 10.0       # Max drawdown % trước khi dừng
    min_account_balance: float = 100  # Balance tối thiểu
    max_leverage: float = 5.0        # Leverage tối đa
    risk_reward_ratio: float = 2.0   # Tỷ lệ RR tối thiểu
    
    # Position sizing
    use_kelly_criterion: bool = False
    kelly_lookback: int = 20         # Số trades để tính Kelly
    max_kelly_fraction: float = 0.25 # Max Kelly fraction
    
    # Correlation limits
    max_correlated_positions: int = 2 # Max positions cùng hướng


@dataclass 
class RiskMetrics:
    """Metrics đánh giá rủi ro"""
    current_risk_pct: float
    available_risk_pct: float
    position_count: int
    total_exposure: float
    largest_position_pct: float
    correlation_risk: float
    drawdown_pct: float
    
    @property
    def is_safe_to_trade(self) -> bool:
        """Có an toàn để giao dịch không"""
        return (
            self.current_risk_pct < 90.0 and  # Chưa đến giới hạn risk
            self.drawdown_pct < 8.0 and       # Drawdown chưa quá cao
            self.position_count < 5            # Chưa quá nhiều positions
        )


class RiskManager:
    """
    Quản lý rủi ro toàn diện cho trading system
    
    Features:
    - Position sizing dựa trên risk %
    - Portfolio risk monitoring  
    - Drawdown protection
    - Correlation analysis
    - Kelly Criterion (optional)
    """
    
    def __init__(self, config: RiskConfig = None):
        self.config = config or RiskConfig()
        self.logger = TradingLogger("RiskManager")
        
        # Risk tracking
        self.trade_history = []
        self.peak_balance = 0.0
        self.current_drawdown = 0.0
        
        self.logger.info("Khởi tạo Risk Manager")
    
    def calculate_position_size(
        self, 
        signal: TradingSignal, 
        account_info: AccountInfo
    ) -> Tuple[float, Dict]:
        """
        Tính kích thước position dựa trên risk management
        
        Args:
            signal: Trading signal với SL/TP
            account_info: Thông tin tài khoản
            
        Returns:
            Tuple[position_size, risk_analysis]
        """
        try:
            # Basic validation
            if not self._validate_signal(signal):
                return 0.0, {"error": "Invalid signal"}
            
            if not self._validate_account(account_info):
                return 0.0, {"error": "Invalid account info"}
            
            # Risk calculations
            available_balance = account_info.available_balance
            entry_price = signal.entry_price
            stop_loss = signal.stop_loss
            
            # Calculate risk per unit
            if signal.signal_type.value == "LONG":
                risk_per_unit = abs(entry_price - stop_loss)
            else:  # SHORT
                risk_per_unit = abs(stop_loss - entry_price)
            
            if risk_per_unit <= 0:
                return 0.0, {"error": "Invalid stop loss"}
            
            # Position sizing methods
            if self.config.use_kelly_criterion:
                position_size = self._calculate_kelly_size(
                    available_balance, entry_price, risk_per_unit
                )
            else:
                position_size = self._calculate_fixed_risk_size(
                    available_balance, entry_price, risk_per_unit
                )
            
            # Apply limits và filters
            position_size = self._apply_risk_limits(
                position_size, entry_price, available_balance, account_info
            )
            
            # Risk analysis
            risk_analysis = self._analyze_position_risk(
                position_size, entry_price, risk_per_unit, available_balance
            )
            
            self.logger.info(
                f"Position size: {position_size:.6f} | "
                f"Risk: ${position_size * risk_per_unit:.2f} | "
                f"Risk %: {risk_analysis['risk_pct']:.2f}%"
            )
            
            return position_size, risk_analysis
            
        except Exception as e:
            self.logger.error(f"Lỗi tính position size: {e}")
            return 0.0, {"error": str(e)}
    
    def validate_risk_before_trade(
        self, 
        position_size: float, 
        signal: TradingSignal, 
        account_info: AccountInfo
    ) -> Tuple[bool, str]:
        """
        Validate risk trước khi đặt lệnh
        
        Returns:
            Tuple[is_valid, reason]
        """
        try:
            # Check account balance
            min_balance = self.config.min_account_balance
            if account_info.available_balance < min_balance:
                return False, f"Balance quá thấp: ${account_info.available_balance:.2f} < ${min_balance}"
            
            # Check max positions
            if len(account_info.positions) >= self.config.max_positions:
                return False, f"Quá nhiều positions: {len(account_info.positions)}/{self.config.max_positions}"
            
            # Check drawdown
            current_drawdown = self._calculate_current_drawdown(account_info)
            if current_drawdown > self.config.max_drawdown:
                return False, f"Drawdown quá cao: {current_drawdown:.1f}% > {self.config.max_drawdown}%"
            
            # Check risk per trade
            entry_price = signal.entry_price
            stop_loss = signal.stop_loss
            risk_per_unit = abs(entry_price - stop_loss)
            trade_risk = position_size * risk_per_unit
            risk_pct = (trade_risk / account_info.available_balance) * 100
            
            if risk_pct > self.config.max_risk_per_trade:
                return False, f"Risk quá cao: {risk_pct:.1f}% > {self.config.max_risk_per_trade}%"
            
            # Check total portfolio risk
            total_risk = self._calculate_portfolio_risk(account_info, trade_risk)
            if total_risk > self.config.max_total_risk:
                return False, f"Total risk quá cao: {total_risk:.1f}% > {self.config.max_total_risk}%"
            
            # Check R:R ratio
            if signal.take_profit:
                rr_ratio = self._calculate_rr_ratio(signal)
                if rr_ratio < self.config.risk_reward_ratio:
                    return False, f"R:R ratio thấp: {rr_ratio:.1f} < {self.config.risk_reward_ratio}"
            
            return True, "Risk validation passed"
            
        except Exception as e:
            return False, f"Lỗi validate risk: {e}"
    
    def get_risk_metrics(self, account_info: AccountInfo) -> RiskMetrics:
        """Lấy metrics rủi ro hiện tại"""
        try:
            total_balance = account_info.total_balance
            current_risk = self._calculate_portfolio_risk(account_info)
            available_risk = self.config.max_total_risk - current_risk
            
            # Position metrics
            position_count = len(account_info.positions)
            total_exposure = sum(
                pos.size * pos.current_price for pos in account_info.positions
            )
            
            largest_position = max(
                [pos.size * pos.current_price for pos in account_info.positions] + [0]
            )
            largest_position_pct = (largest_position / total_balance) * 100 if total_balance > 0 else 0
            
            # Drawdown
            drawdown = self._calculate_current_drawdown(account_info)
            
            return RiskMetrics(
                current_risk_pct=current_risk,
                available_risk_pct=available_risk,
                position_count=position_count,
                total_exposure=total_exposure,
                largest_position_pct=largest_position_pct,
                correlation_risk=0.0,  # TODO: Implement correlation analysis
                drawdown_pct=drawdown
            )
            
        except Exception as e:
            self.logger.error(f"Lỗi get risk metrics: {e}")
            return RiskMetrics(0, 0, 0, 0, 0, 0, 0)
    
    def _calculate_fixed_risk_size(
        self, 
        balance: float, 
        entry_price: float, 
        risk_per_unit: float
    ) -> float:
        """Tính position size theo fixed risk %"""
        risk_amount = balance * (self.config.max_risk_per_trade / 100)
        return risk_amount / risk_per_unit
    
    def _calculate_kelly_size(
        self, 
        balance: float, 
        entry_price: float, 
        risk_per_unit: float
    ) -> float:
        """Tính position size theo Kelly Criterion"""
        if len(self.trade_history) < self.config.kelly_lookback:
            # Fallback to fixed risk
            return self._calculate_fixed_risk_size(balance, entry_price, risk_per_unit)
        
        # Calculate Kelly fraction
        recent_trades = self.trade_history[-self.config.kelly_lookback:]
        wins = [t for t in recent_trades if t['pnl'] > 0]
        losses = [t for t in recent_trades if t['pnl'] < 0]
        
        if not wins or not losses:
            return self._calculate_fixed_risk_size(balance, entry_price, risk_per_unit)
        
        win_rate = len(wins) / len(recent_trades)
        avg_win = sum(t['pnl'] for t in wins) / len(wins)
        avg_loss = abs(sum(t['pnl'] for t in losses) / len(losses))
        
        # Kelly formula: f = (bp - q) / b
        # where b = avg_win/avg_loss, p = win_rate, q = 1-win_rate
        b = avg_win / avg_loss if avg_loss > 0 else 1
        kelly_fraction = (b * win_rate - (1 - win_rate)) / b
        
        # Apply limits
        kelly_fraction = max(0, min(kelly_fraction, self.config.max_kelly_fraction))
        
        # Convert to position size
        risk_amount = balance * kelly_fraction
        return risk_amount / risk_per_unit
    
    def _apply_risk_limits(
        self, 
        position_size: float, 
        entry_price: float, 
        balance: float,
        account_info: AccountInfo
    ) -> float:
        """Apply các giới hạn risk"""
        
        # Minimum size
        min_size = 0.001  # BTC minimum
        position_size = max(position_size, min_size)
        
        # Maximum position value (leverage limit)
        max_position_value = balance * self.config.max_leverage
        max_size_by_leverage = max_position_value / entry_price
        position_size = min(position_size, max_size_by_leverage)
        
        # Round to appropriate precision
        return round(position_size, 6)
    
    def _validate_signal(self, signal: TradingSignal) -> bool:
        """Validate trading signal"""
        if not signal:
            return False
        
        if signal.entry_price <= 0:
            return False
            
        if not signal.stop_loss or signal.stop_loss <= 0:
            return False
        
        # Check SL direction
        if signal.signal_type.value == "LONG" and signal.stop_loss >= signal.entry_price:
            return False
        
        if signal.signal_type.value == "SHORT" and signal.stop_loss <= signal.entry_price:
            return False
        
        return True
    
    def _validate_account(self, account_info: AccountInfo) -> bool:
        """Validate account info"""
        return (
            account_info and
            account_info.available_balance > 0 and
            account_info.total_balance > 0
        )
    
    def _calculate_rr_ratio(self, signal: TradingSignal) -> float:
        """Tính Risk:Reward ratio"""
        if not signal.take_profit:
            return 0.0
        
        entry = signal.entry_price
        sl = signal.stop_loss
        tp = signal.take_profit
        
        if signal.signal_type.value == "LONG":
            risk = entry - sl
            reward = tp - entry
        else:
            risk = sl - entry
            reward = entry - tp
        
        return reward / risk if risk > 0 else 0.0
    
    def _calculate_portfolio_risk(self, account_info: AccountInfo, additional_risk: float = 0) -> float:
        """Tính tổng risk của portfolio"""
        total_risk = additional_risk
        
        for pos in account_info.positions:
            # Estimate risk based on position size (simplified)
            position_value = pos.size * pos.current_price
            estimated_risk = position_value * 0.02  # Assume 2% risk per position
            total_risk += estimated_risk
        
        return (total_risk / account_info.total_balance) * 100 if account_info.total_balance > 0 else 0
    
    def _calculate_current_drawdown(self, account_info: AccountInfo) -> float:
        """Tính drawdown hiện tại"""
        if account_info.total_balance > self.peak_balance:
            self.peak_balance = account_info.total_balance
        
        if self.peak_balance > 0:
            self.current_drawdown = ((self.peak_balance - account_info.total_balance) / self.peak_balance) * 100
        
        return self.current_drawdown
    
    def _analyze_position_risk(
        self, 
        position_size: float, 
        entry_price: float, 
        risk_per_unit: float, 
        balance: float
    ) -> Dict:
        """Phân tích risk của position"""
        
        position_value = position_size * entry_price
        risk_amount = position_size * risk_per_unit
        risk_pct = (risk_amount / balance) * 100
        
        return {
            'position_size': position_size,
            'position_value': position_value,
            'risk_amount': risk_amount,
            'risk_pct': risk_pct,
            'position_pct_of_balance': (position_value / balance) * 100
        }
    
    def add_trade_result(self, pnl: float, trade_info: Dict):
        """Thêm kết quả trade để tính Kelly"""
        self.trade_history.append({
            'pnl': pnl,
            'timestamp': trade_info.get('timestamp'),
            'symbol': trade_info.get('symbol'),
        })
        
        # Giữ lại history limit
        if len(self.trade_history) > self.config.kelly_lookback * 2:
            self.trade_history = self.trade_history[-self.config.kelly_lookback:]