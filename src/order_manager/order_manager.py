"""
Order Manager - Quản lý đặt lệnh và theo dõi fills
"""
import time
import uuid
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from pybit.unified_trading import HTTP

from ..models import (
    Order, OrderSide, OrderType, OrderStatus, 
    TradingSignal, Trade, Position, TradingMode
)
from ..monitoring.logger import TradingLogger


class OrderManager:
    """
    Quản lý orders toàn diện
    
    Features:
    - Place/cancel/modify orders
    - Track order status và fills
    - Handle partial fills
    - Retry mechanism
    - Paper trading support
    - Order validation
    """
    
    def __init__(
        self, 
        api_key: str, 
        api_secret: str, 
        testnet: bool = True,
        trading_mode: TradingMode = TradingMode.LIVE
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.trading_mode = trading_mode
        self.session = None
        self.logger = TradingLogger("OrderManager")
        
        # Order tracking
        self.active_orders: Dict[str, Order] = {}
        self.completed_orders: Dict[str, Order] = {}
        self.trades: List[Trade] = []
        
        # Paper trading
        self.paper_balance = 10000.0
        self.paper_positions: Dict[str, Position] = {}
        
        # Callbacks
        self.fill_callbacks: List[Callable] = []
        self.order_callbacks: List[Callable] = []
        
        if trading_mode != TradingMode.PAPER:
            self._connect()
        
        self.logger.info(f"Khởi tạo Order Manager - Mode: {trading_mode.value}")
    
    def _connect(self):
        """Kết nối Bybit API"""
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
    
    def place_market_order(
        self, 
        symbol: str, 
        side: OrderSide, 
        quantity: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Optional[Order]:
        """
        Đặt lệnh market
        
        Args:
            symbol: Cặp giao dịch
            side: BUY hoặc SELL
            quantity: Số lượng
            stop_loss: Giá stop loss
            take_profit: Giá take profit
            
        Returns:
            Order object nếu thành công
        """
        try:
            # Validate order
            if not self._validate_order_params(symbol, side, quantity):
                return None
            
            if self.trading_mode == TradingMode.PAPER:
                return self._place_paper_order(symbol, side, OrderType.MARKET, quantity)
            
            # Real order placement
            order_id = str(uuid.uuid4())
            
            # Place main order
            response = self._retry_api_call(
                self.session.place_order,
                category="linear",
                symbol=symbol,
                side=side.value,
                orderType="Market",
                qty=str(quantity)
            )
            
            if not response or response.get('retCode') != 0:
                self.logger.error(f"Lỗi đặt lệnh market: {response}")
                return None
            
            # Create order object
            order = Order(
                order_id=response['result']['orderId'],
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                quantity=quantity,
                status=OrderStatus.NEW
            )
            
            self.active_orders[order.order_id] = order
            
            self.logger.info(f"✅ Market order placed: {side.value} {quantity} {symbol}")
            
            # Place SL/TP orders after a delay
            if stop_loss or take_profit:
                time.sleep(2)  # Wait for main order to fill
                self._place_conditional_orders(order, stop_loss, take_profit)
            
            return order
            
        except Exception as e:
            self.logger.error(f"Lỗi place market order: {e}")
            return None
    
    def place_limit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        price: float
    ) -> Optional[Order]:
        """Đặt lệnh limit"""
        try:
            if not self._validate_order_params(symbol, side, quantity, price):
                return None
            
            if self.trading_mode == TradingMode.PAPER:
                return self._place_paper_order(symbol, side, OrderType.LIMIT, quantity, price)
            
            response = self._retry_api_call(
                self.session.place_order,
                category="linear",
                symbol=symbol,
                side=side.value,
                orderType="Limit",
                qty=str(quantity),
                price=str(price)
            )
            
            if not response or response.get('retCode') != 0:
                self.logger.error(f"Lỗi đặt lệnh limit: {response}")
                return None
            
            order = Order(
                order_id=response['result']['orderId'],
                symbol=symbol,
                side=side,
                order_type=OrderType.LIMIT,
                quantity=quantity,
                price=price,
                status=OrderStatus.NEW
            )
            
            self.active_orders[order.order_id] = order
            
            self.logger.info(f"✅ Limit order placed: {side.value} {quantity} {symbol} @ ${price}")
            return order
            
        except Exception as e:
            self.logger.error(f"Lỗi place limit order: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        try:
            if order_id not in self.active_orders:
                self.logger.warning(f"Order {order_id} không tồn tại")
                return False
            
            order = self.active_orders[order_id]
            
            if self.trading_mode == TradingMode.PAPER:
                return self._cancel_paper_order(order_id)
            
            response = self._retry_api_call(
                self.session.cancel_order,
                category="linear",
                symbol=order.symbol,
                orderId=order_id
            )
            
            if response and response.get('retCode') == 0:
                order.status = OrderStatus.CANCELLED
                self.completed_orders[order_id] = order
                del self.active_orders[order_id]
                
                self.logger.info(f"✅ Order cancelled: {order_id}")
                return True
            else:
                self.logger.error(f"Lỗi cancel order: {response}")
                return False
                
        except Exception as e:
            self.logger.error(f"Lỗi cancel order: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Optional[Order]:
        """Lấy trạng thái order"""
        if order_id in self.active_orders:
            order = self.active_orders[order_id]
            
            if self.trading_mode == TradingMode.PAPER:
                return order
            
            # Update từ API
            self._update_order_status(order)
            return order
        
        elif order_id in self.completed_orders:
            return self.completed_orders[order_id]
        
        return None
    
    def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Lấy danh sách positions"""
        try:
            if self.trading_mode == TradingMode.PAPER:
                positions = list(self.paper_positions.values())
                if symbol:
                    positions = [p for p in positions if p.symbol == symbol]
                return positions
            
            response = self._retry_api_call(
                self.session.get_positions,
                category="linear",
                symbol=symbol
            )
            
            if not response or response.get('retCode') != 0:
                return []
            
            positions = []
            for pos_data in response['result']['list']:
                if float(pos_data['size']) > 0:
                    position = Position(
                        symbol=pos_data['symbol'],
                        side=OrderSide.BUY if pos_data['side'] == 'Buy' else OrderSide.SELL,
                        size=float(pos_data['size']),
                        entry_price=float(pos_data['avgPrice']),
                        current_price=float(pos_data['markPrice']),
                        unrealized_pnl=float(pos_data['unrealisedPnl']),
                        timestamp=datetime.now()
                    )
                    positions.append(position)
            
            return positions
            
        except Exception as e:
            self.logger.error(f"Lỗi get positions: {e}")
            return []
    
    def close_position(self, symbol: str, quantity: Optional[float] = None) -> bool:
        """Đóng position"""
        try:
            positions = self.get_positions(symbol)
            if not positions:
                self.logger.warning(f"Không có position để close: {symbol}")
                return False
            
            position = positions[0]  # Assume 1 position per symbol
            close_quantity = quantity or position.size
            
            # Determine close side
            close_side = OrderSide.SELL if position.side == OrderSide.BUY else OrderSide.BUY
            
            # Place close order
            close_order = self.place_market_order(symbol, close_side, close_quantity)
            
            if close_order:
                self.logger.info(f"✅ Position closed: {symbol} {close_quantity}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Lỗi close position: {e}")
            return False
    
    def _place_paper_order(
        self, 
        symbol: str, 
        side: OrderSide, 
        order_type: OrderType, 
        quantity: float, 
        price: Optional[float] = None
    ) -> Order:
        """Đặt lệnh paper trading"""
        
        order_id = f"paper_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # For market orders, use current "market price"
        if order_type == OrderType.MARKET:
            # Simulate market price (simplified)
            current_price = 50000.0  # Should get from data feed
            fill_price = current_price
        else:
            fill_price = price
        
        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            status=OrderStatus.FILLED,  # Paper orders fill immediately
            filled_quantity=quantity,
            avg_fill_price=fill_price
        )
        
        # Create paper trade
        trade = Trade(
            trade_id=f"trade_{order_id}",
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=fill_price,
            commission=quantity * fill_price * 0.0006,  # 0.06% commission
            timestamp=datetime.now(),
            order_id=order_id
        )
        
        self.trades.append(trade)
        self.completed_orders[order_id] = order
        
        # Update paper position
        self._update_paper_position(trade)
        
        self.logger.info(f"📄 Paper order filled: {side.value} {quantity} {symbol} @ ${fill_price}")
        
        return order
    
    def _cancel_paper_order(self, order_id: str) -> bool:
        """Cancel paper order"""
        if order_id in self.active_orders:
            order = self.active_orders[order_id]
            order.status = OrderStatus.CANCELLED
            self.completed_orders[order_id] = order
            del self.active_orders[order_id]
            return True
        return False
    
    def _update_paper_position(self, trade: Trade):
        """Cập nhật paper position"""
        symbol = trade.symbol
        
        if symbol not in self.paper_positions:
            # New position
            side = trade.side
            self.paper_positions[symbol] = Position(
                symbol=symbol,
                side=side,
                size=trade.quantity,
                entry_price=trade.price,
                current_price=trade.price,
                unrealized_pnl=0.0,
                timestamp=trade.timestamp
            )
        else:
            # Update existing position
            pos = self.paper_positions[symbol]
            
            if pos.side == trade.side:
                # Add to position
                total_value = pos.size * pos.entry_price + trade.quantity * trade.price
                pos.size += trade.quantity
                pos.entry_price = total_value / pos.size
            else:
                # Reduce or reverse position
                if trade.quantity >= pos.size:
                    # Close or reverse
                    remaining = trade.quantity - pos.size
                    if remaining > 0:
                        # Reverse position
                        pos.side = trade.side
                        pos.size = remaining
                        pos.entry_price = trade.price
                    else:
                        # Close position
                        del self.paper_positions[symbol]
                else:
                    # Partial close
                    pos.size -= trade.quantity
    
    def _place_conditional_orders(
        self, 
        main_order: Order, 
        stop_loss: Optional[float], 
        take_profit: Optional[float]
    ):
        """Đặt SL/TP orders"""
        try:
            if not stop_loss and not take_profit:
                return
            
            opposite_side = OrderSide.SELL if main_order.side == OrderSide.BUY else OrderSide.BUY
            
            # Stop Loss
            if stop_loss:
                sl_response = self._retry_api_call(
                    self.session.place_order,
                    category="linear",
                    symbol=main_order.symbol,
                    side=opposite_side.value,
                    orderType="Market",
                    qty=str(main_order.quantity),
                    stopLoss=str(stop_loss),
                    reduceOnly=True
                )
                
                if sl_response and sl_response.get('retCode') == 0:
                    self.logger.info(f"✅ Stop Loss placed @ ${stop_loss}")
            
            # Take Profit  
            if take_profit:
                tp_response = self._retry_api_call(
                    self.session.place_order,
                    category="linear",
                    symbol=main_order.symbol,
                    side=opposite_side.value,
                    orderType="Market", 
                    qty=str(main_order.quantity),
                    takeProfit=str(take_profit),
                    reduceOnly=True
                )
                
                if tp_response and tp_response.get('retCode') == 0:
                    self.logger.info(f"✅ Take Profit placed @ ${take_profit}")
                    
        except Exception as e:
            self.logger.error(f"Lỗi place conditional orders: {e}")
    
    def _update_order_status(self, order: Order):
        """Cập nhật order status từ API"""
        try:
            response = self._retry_api_call(
                self.session.get_open_orders,
                category="linear",
                symbol=order.symbol,
                orderId=order.order_id
            )
            
            if response and response.get('retCode') == 0:
                orders_data = response['result']['list']
                
                if orders_data:
                    order_data = orders_data[0]
                    order.status = OrderStatus(order_data['orderStatus'])
                    order.filled_quantity = float(order_data.get('cumExecQty', 0))
                    
                    if order.filled_quantity > 0:
                        order.avg_fill_price = float(order_data.get('avgPrice', 0))
                    
                    # Move to completed if filled or cancelled
                    if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                        self.completed_orders[order.order_id] = order
                        if order.order_id in self.active_orders:
                            del self.active_orders[order.order_id]
                
        except Exception as e:
            self.logger.error(f"Lỗi update order status: {e}")
    
    def _validate_order_params(
        self, 
        symbol: str, 
        side: OrderSide, 
        quantity: float, 
        price: Optional[float] = None
    ) -> bool:
        """Validate order parameters"""
        
        if not symbol or quantity <= 0:
            return False
        
        if quantity < 0.001:  # Min BTC size
            self.logger.warning(f"Quantity quá nhỏ: {quantity}")
            return False
        
        if price and price <= 0:
            return False
        
        return True
    
    def _retry_api_call(self, func, max_retries: int = 3, **kwargs):
        """Retry API call"""
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    time.sleep(2 ** attempt)
                
                result = func(**kwargs)
                return result
                
            except Exception as e:
                self.logger.warning(f"API call attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
        
        return None
    
    def add_fill_callback(self, callback: Callable):
        """Thêm callback khi order được fill"""
        self.fill_callbacks.append(callback)
    
    def get_trading_summary(self) -> Dict:
        """Tóm tắt trading activity"""
        active_count = len(self.active_orders)
        completed_count = len(self.completed_orders)
        trades_count = len(self.trades)
        
        total_pnl = sum(
            (trade.price * trade.quantity * (1 if trade.side == OrderSide.BUY else -1)) 
            - trade.commission
            for trade in self.trades
        )
        
        return {
            'active_orders': active_count,
            'completed_orders': completed_count,
            'total_trades': trades_count,
            'total_pnl': total_pnl,
            'trading_mode': self.trading_mode.value,
            'positions': len(self.paper_positions) if self.trading_mode == TradingMode.PAPER else 'N/A'
        }