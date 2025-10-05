"""
SMC Strategy - Smart Money Concept Implementation
"""
from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np
from datetime import datetime

from .base_strategy import BaseStrategy
from ..models import TradingSignal, SignalType, MarketData, MarketStructure, OrderBlock, FairValueGap
from ..monitoring.logger import TradingLogger


class SMCStrategy(BaseStrategy):
    """
    Smart Money Concept Trading Strategy
    
    Features:
    - Market Structure Analysis (BOS/CHoCH)
    - Order Block Detection
    - Fair Value Gap Analysis  
    - Multi-timeframe confluence
    - Risk-based signal generation
    """
    
    def __init__(self, symbol: str, config: Dict[str, Any] = None):
        default_config = {
            'required_history': 200,
            'timeframe': '15',
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'sma_short': 20,
            'sma_long': 50,
            'ob_strength_multiplier': 2.0,  # Order block strength
            'min_confidence': 75.0,
            'stop_loss_pct': 1.5,
            'take_profit_pct': 2.5,
            'swing_window': 5
        }
        
        if config:
            default_config.update(config)
        
        super().__init__("SMC", symbol, default_config)
        
        # SMC specific data
        self.market_structure = MarketStructure.NEUTRAL
        self.order_blocks: List[OrderBlock] = []
        self.fair_value_gaps: List[FairValueGap] = []
        
        # Indicators
        self.rsi_values: pd.Series = pd.Series()
        self.sma_short: pd.Series = pd.Series()
        self.sma_long: pd.Series = pd.Series()
    
    def update_data(self, candles: pd.DataFrame, market_data: MarketData):
        """Cập nhật dữ liệu và tính toán indicators"""
        self.candle_data = candles.copy()
        self.market_data = market_data
        
        if len(candles) < self.config['required_history']:
            self.logger.warning(f"Không đủ dữ liệu: {len(candles)}/{self.config['required_history']}")
            return
        
        # Tính indicators
        self._calculate_indicators()
        
        # SMC Analysis
        self._analyze_market_structure()
        self._detect_order_blocks()
        self._detect_fair_value_gaps()
    
    def generate_signal(self) -> Optional[TradingSignal]:
        """Tạo tín hiệu SMC với confluence analysis"""
        if self.candle_data.empty or self.market_data is None:
            return None
        
        current_price = self.market_data.current_price
        current_rsi = self.rsi_values.iloc[-1] if not self.rsi_values.empty else 50
        
        # Confluence factors
        structure_factor = self._get_structure_factor()
        rsi_factor = self._get_rsi_factor(current_rsi)
        trend_factor = self._get_trend_factor(current_price)
        order_block_factor = self._get_order_block_factor(current_price)
        fvg_factor = self._get_fvg_factor(current_price)
        
        # LONG Signal Analysis
        long_confluence = (
            structure_factor['bullish'] +
            rsi_factor['bullish'] +
            trend_factor['bullish'] + 
            order_block_factor['bullish'] +
            fvg_factor['bullish']
        )
        
        # SHORT Signal Analysis
        short_confluence = (
            structure_factor['bearish'] +
            rsi_factor['bearish'] +
            trend_factor['bearish'] +
            order_block_factor['bearish'] +
            fvg_factor['bearish']
        )
        
        # Tính confidence (max 5 factors = 100%)
        long_confidence = (long_confluence / 5) * 100
        short_confidence = (short_confluence / 5) * 100
        
        # Tạo signal nếu đủ confluence
        min_confidence = self.config['min_confidence']
        
        if long_confidence >= min_confidence and long_confidence > short_confidence:
            return self._create_long_signal(current_price, long_confidence)
        
        elif short_confidence >= min_confidence and short_confidence > long_confidence:
            return self._create_short_signal(current_price, short_confidence)
        
        return None
    
    def _calculate_indicators(self):
        """Tính toán các indicators"""
        if self.candle_data.empty:
            return
        
        closes = self.candle_data['close']
        
        # RSI
        self.rsi_values = self.calculate_rsi(closes, self.config['rsi_period'])
        
        # Moving Averages
        self.sma_short = self.calculate_sma(closes, self.config['sma_short'])
        self.sma_long = self.calculate_sma(closes, self.config['sma_long'])
    
    def _analyze_market_structure(self):
        """Phân tích cấu trúc thị trường - BOS/CHoCH detection"""
        if len(self.candle_data) < self.config['swing_window'] * 2:
            return
        
        df = self.candle_data.copy()
        window = self.config['swing_window']
        
        # Tìm swing highs và lows
        highs_condition = df['high'].rolling(window=window, center=True).max() == df['high']
        lows_condition = df['low'].rolling(window=window, center=True).min() == df['low']
        
        swing_highs = df.loc[highs_condition, 'high'].dropna()
        swing_lows = df.loc[lows_condition, 'low'].dropna()
        
        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            latest_high = swing_highs.iloc[-1]
            prev_high = swing_highs.iloc[-2]
            latest_low = swing_lows.iloc[-1]
            prev_low = swing_lows.iloc[-2]
            
            # BOS Logic
            if latest_high > prev_high and latest_low > prev_low:
                self.market_structure = MarketStructure.BULLISH_BOS
            elif latest_high < prev_high and latest_low < prev_low:
                self.market_structure = MarketStructure.BEARISH_BOS
            else:
                self.market_structure = MarketStructure.NEUTRAL
    
    def _detect_order_blocks(self):
        """Phát hiện Order Blocks"""
        self.order_blocks.clear()
        
        if len(self.candle_data) < 10:
            return
        
        df = self.candle_data.copy()
        multiplier = self.config['ob_strength_multiplier']
        
        for i in range(5, len(df) - 5):
            candle = df.iloc[i]
            
            # Bullish Order Block
            if candle['close'] > candle['open']:  # Green candle
                candle_size = candle['close'] - candle['open']
                avg_size = df.iloc[i-5:i]['close'].subtract(df.iloc[i-5:i]['open']).abs().std()
                
                if candle_size > avg_size * multiplier:
                    # Check impulse move after
                    future_high = df.iloc[i+1:i+6]['high'].max()
                    if future_high > candle['high'] * 1.01:  # 1% impulse
                        
                        ob = OrderBlock(
                            type='BULLISH_OB',
                            high=candle['high'],
                            low=candle['low'],
                            timestamp=df.iloc[i]['timestamp'] if 'timestamp' in df.columns else datetime.now(),
                            volume=candle.get('volume', 0),
                            confidence=min(candle_size / (avg_size * multiplier), 1.0) * 100
                        )
                        self.order_blocks.append(ob)
            
            # Bearish Order Block  
            elif candle['close'] < candle['open']:  # Red candle
                candle_size = candle['open'] - candle['close']
                avg_size = df.iloc[i-5:i]['open'].subtract(df.iloc[i-5:i]['close']).abs().std()
                
                if candle_size > avg_size * multiplier:
                    # Check impulse move after
                    future_low = df.iloc[i+1:i+6]['low'].min()
                    if future_low < candle['low'] * 0.99:  # 1% impulse
                        
                        ob = OrderBlock(
                            type='BEARISH_OB',
                            high=candle['high'],
                            low=candle['low'],
                            timestamp=df.iloc[i]['timestamp'] if 'timestamp' in df.columns else datetime.now(),
                            volume=candle.get('volume', 0),
                            confidence=min(candle_size / (avg_size * multiplier), 1.0) * 100
                        )
                        self.order_blocks.append(ob)
        
        # Giữ lại 3 OB gần nhất
        self.order_blocks = self.order_blocks[-3:]
    
    def _detect_fair_value_gaps(self):
        """Phát hiện Fair Value Gaps"""
        self.fair_value_gaps.clear()
        
        if len(self.candle_data) < 3:
            return
        
        df = self.candle_data.copy()
        
        for i in range(1, len(df) - 1):
            candle_before = df.iloc[i-1]
            candle_current = df.iloc[i]
            candle_after = df.iloc[i+1]
            
            # Bullish FVG
            if (candle_before['low'] > candle_after['high'] and
                candle_current['close'] > candle_current['open']):
                
                fvg = FairValueGap(
                    type='BULLISH_FVG',
                    high=candle_before['low'],
                    low=candle_after['high'],
                    timestamp=df.iloc[i]['timestamp'] if 'timestamp' in df.columns else datetime.now()
                )
                self.fair_value_gaps.append(fvg)
            
            # Bearish FVG
            elif (candle_before['high'] < candle_after['low'] and
                  candle_current['close'] < candle_current['open']):
                
                fvg = FairValueGap(
                    type='BEARISH_FVG',
                    high=candle_after['low'],
                    low=candle_before['high'],
                    timestamp=df.iloc[i]['timestamp'] if 'timestamp' in df.columns else datetime.now()
                )
                self.fair_value_gaps.append(fvg)
        
        # Giữ lại 2 FVG gần nhất
        self.fair_value_gaps = self.fair_value_gaps[-2:]
    
    def _get_structure_factor(self) -> Dict[str, float]:
        """Đánh giá factor từ market structure"""
        if self.market_structure == MarketStructure.BULLISH_BOS:
            return {'bullish': 1.0, 'bearish': 0.0}
        elif self.market_structure == MarketStructure.BEARISH_BOS:
            return {'bullish': 0.0, 'bearish': 1.0}
        else:
            return {'bullish': 0.0, 'bearish': 0.0}
    
    def _get_rsi_factor(self, current_rsi: float) -> Dict[str, float]:
        """Đánh giá factor từ RSI"""
        overbought = self.config['rsi_overbought']
        oversold = self.config['rsi_oversold']
        
        if current_rsi < oversold:
            return {'bullish': 1.0, 'bearish': 0.0}
        elif current_rsi > overbought:
            return {'bullish': 0.0, 'bearish': 1.0}
        elif 30 < current_rsi < 70:
            # Neutral zone - partial credit
            return {'bullish': 0.5, 'bearish': 0.5}
        else:
            return {'bullish': 0.0, 'bearish': 0.0}
    
    def _get_trend_factor(self, current_price: float) -> Dict[str, float]:
        """Đánh giá factor từ trend (SMA)"""
        if self.sma_short.empty or self.sma_long.empty:
            return {'bullish': 0.0, 'bearish': 0.0}
        
        sma_short = self.sma_short.iloc[-1]
        sma_long = self.sma_long.iloc[-1]
        
        if current_price > sma_short > sma_long:
            return {'bullish': 1.0, 'bearish': 0.0}
        elif current_price < sma_short < sma_long:
            return {'bullish': 0.0, 'bearish': 1.0}
        else:
            return {'bullish': 0.0, 'bearish': 0.0}
    
    def _get_order_block_factor(self, current_price: float) -> Dict[str, float]:
        """Đánh giá factor từ Order Blocks"""
        bullish_obs = [ob for ob in self.order_blocks if ob.type == 'BULLISH_OB']
        bearish_obs = [ob for ob in self.order_blocks if ob.type == 'BEARISH_OB']
        
        # Check if price near any OB
        near_bullish = any(
            ob.low <= current_price <= ob.high 
            for ob in bullish_obs
        )
        
        near_bearish = any(
            ob.low <= current_price <= ob.high
            for ob in bearish_obs
        )
        
        if near_bullish and bullish_obs:
            return {'bullish': 1.0, 'bearish': 0.0}
        elif near_bearish and bearish_obs:
            return {'bullish': 0.0, 'bearish': 1.0}
        elif bullish_obs and not bearish_obs:
            return {'bullish': 0.5, 'bearish': 0.0}
        elif bearish_obs and not bullish_obs:
            return {'bullish': 0.0, 'bearish': 0.5}
        else:
            return {'bullish': 0.0, 'bearish': 0.0}
    
    def _get_fvg_factor(self, current_price: float) -> Dict[str, float]:
        """Đánh giá factor từ Fair Value Gaps"""
        if not self.fair_value_gaps:
            return {'bullish': 0.0, 'bearish': 0.0}
        
        # Check if price in any FVG
        in_bullish_fvg = any(
            fvg.low <= current_price <= fvg.high and fvg.type == 'BULLISH_FVG' and not fvg.filled
            for fvg in self.fair_value_gaps
        )
        
        in_bearish_fvg = any(
            fvg.low <= current_price <= fvg.high and fvg.type == 'BEARISH_FVG' and not fvg.filled
            for fvg in self.fair_value_gaps
        )
        
        if in_bullish_fvg:
            return {'bullish': 1.0, 'bearish': 0.0}
        elif in_bearish_fvg:
            return {'bullish': 0.0, 'bearish': 1.0}
        else:
            return {'bullish': 0.0, 'bearish': 0.0}
    
    def _create_long_signal(self, entry_price: float, confidence: float) -> TradingSignal:
        """Tạo LONG signal"""
        stop_loss = entry_price * (1 - self.config['stop_loss_pct'] / 100)
        take_profit = entry_price * (1 + self.config['take_profit_pct'] / 100)
        
        reason_parts = []
        if self.market_structure == MarketStructure.BULLISH_BOS:
            reason_parts.append("Bullish BOS")
        if any(ob.type == 'BULLISH_OB' for ob in self.order_blocks):
            reason_parts.append("Bullish OB")
        if self.sma_short.iloc[-1] > self.sma_long.iloc[-1]:
            reason_parts.append("Uptrend")
        
        reason = " + ".join(reason_parts) if reason_parts else "SMC Confluence"
        
        return TradingSignal(
            signal_type=SignalType.LONG,
            symbol=self.symbol,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            reason=reason,
            metadata={
                'market_structure': self.market_structure.value,
                'order_blocks': len(self.order_blocks),
                'fair_value_gaps': len(self.fair_value_gaps),
                'rsi': self.rsi_values.iloc[-1] if not self.rsi_values.empty else None
            }
        )
    
    def _create_short_signal(self, entry_price: float, confidence: float) -> TradingSignal:
        """Tạo SHORT signal"""
        stop_loss = entry_price * (1 + self.config['stop_loss_pct'] / 100)
        take_profit = entry_price * (1 - self.config['take_profit_pct'] / 100)
        
        reason_parts = []
        if self.market_structure == MarketStructure.BEARISH_BOS:
            reason_parts.append("Bearish BOS")
        if any(ob.type == 'BEARISH_OB' for ob in self.order_blocks):
            reason_parts.append("Bearish OB")
        if self.sma_short.iloc[-1] < self.sma_long.iloc[-1]:
            reason_parts.append("Downtrend")
        
        reason = " + ".join(reason_parts) if reason_parts else "SMC Confluence"
        
        return TradingSignal(
            signal_type=SignalType.SHORT,
            symbol=self.symbol,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            reason=reason,
            metadata={
                'market_structure': self.market_structure.value,
                'order_blocks': len(self.order_blocks),
                'fair_value_gaps': len(self.fair_value_gaps),
                'rsi': self.rsi_values.iloc[-1] if not self.rsi_values.empty else None
            }
        )