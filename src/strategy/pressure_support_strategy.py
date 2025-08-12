#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
压力位支撑位交易策略

根据当前行情分析最近n个月是否超过了压力位，来判断买卖
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from ..models.models import TradeSignal, TradeAction, StockData
from ..utils.logger import LoggerMixin, log_strategy_analysis
from ..data.data_provider import DataManager


@dataclass
class SupportResistanceLevel:
    """支撑阻力位数据结构"""
    level: float
    strength: float  # 强度 (0-1)
    touch_count: int  # 触及次数
    last_touch: datetime
    level_type: str  # 'support' or 'resistance'


@dataclass
class MarketAnalysis:
    """市场分析结果"""
    symbol: str
    current_price: float
    trend: str  # 'bullish', 'bearish', 'sideways'
    support_levels: List[SupportResistanceLevel]
    resistance_levels: List[SupportResistanceLevel]
    volume_trend: str  # 'increasing', 'decreasing', 'stable'
    momentum: float  # 动量指标
    volatility: float  # 波动率
    analysis_time: datetime


class TechnicalAnalyzer:
    """技术分析器"""
    
    @staticmethod
    def find_support_resistance_levels(df: pd.DataFrame, window: int = 20, min_touches: int = 2) -> Tuple[List[SupportResistanceLevel], List[SupportResistanceLevel]]:
        """寻找支撑位和阻力位
        
        Args:
            df: 股票历史数据
            window: 分析窗口
            min_touches: 最小触及次数
            
        Returns:
            (支撑位列表, 阻力位列表)
        """
        if len(df) < window * 2:
            return [], []
            
        # 寻找局部高点和低点
        highs = TechnicalAnalyzer._find_peaks(df['high'].values, window)
        lows = TechnicalAnalyzer._find_valleys(df['low'].values, window)
        
        # 聚类相近的价格水平
        resistance_levels = TechnicalAnalyzer._cluster_levels(
            highs, df, 'resistance', min_touches
        )
        support_levels = TechnicalAnalyzer._cluster_levels(
            lows, df, 'support', min_touches
        )
        
        return support_levels, resistance_levels
    
    @staticmethod
    def _find_peaks(prices: np.ndarray, window: int) -> List[Tuple[int, float]]:
        """寻找价格峰值"""
        peaks = []
        for i in range(window, len(prices) - window):
            if all(prices[i] >= prices[i-j] for j in range(1, window+1)) and \
               all(prices[i] >= prices[i+j] for j in range(1, window+1)):
                peaks.append((i, prices[i]))
        return peaks
    
    @staticmethod
    def _find_valleys(prices: np.ndarray, window: int) -> List[Tuple[int, float]]:
        """寻找价格谷值"""
        valleys = []
        for i in range(window, len(prices) - window):
            if all(prices[i] <= prices[i-j] for j in range(1, window+1)) and \
               all(prices[i] <= prices[i+j] for j in range(1, window+1)):
                valleys.append((i, prices[i]))
        return valleys
    
    @staticmethod
    def _cluster_levels(points: List[Tuple[int, float]], df: pd.DataFrame, 
                       level_type: str, min_touches: int) -> List[SupportResistanceLevel]:
        """聚类价格水平"""
        if not points:
            return []
            
        # 按价格排序
        points.sort(key=lambda x: x[1])
        
        levels = []
        tolerance = 0.02  # 2%的价格容忍度
        
        i = 0
        while i < len(points):
            current_level = points[i][1]
            cluster = [points[i]]
            
            # 找到相近的价格点
            j = i + 1
            while j < len(points):
                if abs(points[j][1] - current_level) / current_level <= tolerance:
                    cluster.append(points[j])
                    j += 1
                else:
                    break
            
            # 如果触及次数足够，创建支撑/阻力位
            if len(cluster) >= min_touches:
                avg_price = np.mean([p[1] for p in cluster])
                strength = min(len(cluster) / 10.0, 1.0)  # 强度基于触及次数
                
                # 最后触及时间
                last_touch_idx = max([p[0] for p in cluster])
                last_touch = df.index[last_touch_idx] if last_touch_idx < len(df) else datetime.now()
                
                level = SupportResistanceLevel(
                    level=avg_price,
                    strength=strength,
                    touch_count=len(cluster),
                    last_touch=last_touch,
                    level_type=level_type
                )
                levels.append(level)
            
            i = j
        
        return levels
    
    @staticmethod
    def calculate_momentum(df: pd.DataFrame, period: int = 14) -> float:
        """计算动量指标"""
        if len(df) < period + 1:
            return 0.0
            
        current_price = df['close'].iloc[-1]
        past_price = df['close'].iloc[-(period+1)]
        
        return (current_price - past_price) / past_price
    
    @staticmethod
    def calculate_volume_trend(df: pd.DataFrame, period: int = 20) -> str:
        """计算成交量趋势"""
        if len(df) < period:
            return 'stable'
            
        recent_volume = df['volume'].iloc[-period//2:].mean()
        past_volume = df['volume'].iloc[-period:-period//2].mean()
        
        change_ratio = (recent_volume - past_volume) / past_volume
        
        if change_ratio > 0.2:
            return 'increasing'
        elif change_ratio < -0.2:
            return 'decreasing'
        else:
            return 'stable'
    
    @staticmethod
    def determine_trend(df: pd.DataFrame, period: int = 20) -> str:
        """判断价格趋势"""
        if len(df) < period:
            return 'sideways'
            
        # 使用移动平均线判断趋势
        ma_short = df['close'].rolling(window=period//2).mean().iloc[-1]
        ma_long = df['close'].rolling(window=period).mean().iloc[-1]
        current_price = df['close'].iloc[-1]
        
        if current_price > ma_short > ma_long:
            return 'bullish'
        elif current_price < ma_short < ma_long:
            return 'bearish'
        else:
            return 'sideways'


class PressureSupportStrategy(LoggerMixin):
    """压力位支撑位交易策略"""
    
    def __init__(self, config, data_manager: DataManager):
        self.config = config
        self.data_manager = data_manager
        
        # 策略参数
        self.analysis_period = config.strategy.analysis_period  # 分析周期（月）
        self.pressure_factor = config.strategy.pressure_factor  # 压力位因子
        self.support_factor = config.strategy.support_factor    # 支撑位因子
        self.volume_threshold = config.strategy.volume_threshold # 成交量阈值
        
        # 风险管理参数
        self.max_position_size = config.risk.max_position_size
        self.stop_loss = config.risk.stop_loss
        self.take_profit = config.risk.take_profit
        
        self.analyzer = TechnicalAnalyzer()
        
    async def analyze_market(self, symbol: str) -> Optional[MarketAnalysis]:
        """分析市场
        
        Args:
            symbol: 股票代码
            
        Returns:
            市场分析结果
        """
        try:
            # 获取历史数据
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=self.analysis_period * 30)).strftime('%Y-%m-%d')
            
            df = await self.data_manager.get_historical_data(symbol, start_date, end_date)
            
            if df.empty:
                self.logger.warning(f"无法获取{symbol}的历史数据")
                return None
            
            # 标准化列名
            df = self._standardize_dataframe(df)
            
            # 获取当前价格
            current_data = await self.data_manager.get_realtime_data([symbol])
            current_price = current_data.get(symbol, StockData(symbol, '', 0, 0, 0, 0, datetime.now())).current_price
            
            # 寻找支撑位和阻力位
            support_levels, resistance_levels = self.analyzer.find_support_resistance_levels(df)
            
            # 计算技术指标
            momentum = self.analyzer.calculate_momentum(df)
            volatility = df['close'].pct_change().std() * np.sqrt(252)  # 年化波动率
            trend = self.analyzer.determine_trend(df)
            volume_trend = self.analyzer.calculate_volume_trend(df)
            
            analysis = MarketAnalysis(
                symbol=symbol,
                current_price=current_price,
                trend=trend,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                volume_trend=volume_trend,
                momentum=momentum,
                volatility=volatility,
                analysis_time=datetime.now()
            )
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"分析市场{symbol}失败: {e}")
            return None
    
    async def generate_signal(self, symbol: str) -> Optional[TradeSignal]:
        """生成交易信号
        
        Args:
            symbol: 股票代码
            
        Returns:
            交易信号
        """
        analysis = await self.analyze_market(symbol)
        if not analysis:
            return None
        
        try:
            # 分析买卖信号
            action, confidence, reason = self._analyze_trade_signal(analysis)
            
            if action == TradeAction.HOLD:
                return None
            
            # 计算交易数量
            quantity = self._calculate_position_size(analysis.current_price)
            
            signal = TradeSignal(
                symbol=symbol,
                action=action,
                price=analysis.current_price,
                quantity=quantity,
                confidence=confidence,
                reason=reason,
                timestamp=datetime.now(),
                strategy="pressure_support_strategy"
            )
            
            # 记录策略分析日志
            log_strategy_analysis(symbol, action.value, {
                'price': analysis.current_price,
                'confidence': confidence,
                'reason': reason,
                'trend': analysis.trend,
                'momentum': analysis.momentum
            })
            
            return signal
            
        except Exception as e:
            self.logger.error(f"生成交易信号失败: {e}")
            return None
    
    def _analyze_trade_signal(self, analysis: MarketAnalysis) -> Tuple[TradeAction, float, str]:
        """分析交易信号
        
        Args:
            analysis: 市场分析结果
            
        Returns:
            (交易动作, 信心度, 原因)
        """
        current_price = analysis.current_price
        
        # 寻找最近的支撑位和阻力位
        nearest_support = self._find_nearest_level(current_price, analysis.support_levels, 'below')
        nearest_resistance = self._find_nearest_level(current_price, analysis.resistance_levels, 'above')
        
        # 买入信号分析
        buy_signals = []
        sell_signals = []
        
        # 1. 支撑位反弹买入信号
        if nearest_support:
            support_distance = (current_price - nearest_support.level) / nearest_support.level
            if 0 <= support_distance <= 0.02:  # 在支撑位附近2%
                confidence = nearest_support.strength * 0.8
                buy_signals.append((confidence, f"接近支撑位{nearest_support.level:.2f}反弹"))
        
        # 2. 突破阻力位买入信号
        if nearest_resistance:
            resistance_distance = (current_price - nearest_resistance.level) / nearest_resistance.level
            if 0.01 <= resistance_distance <= 0.05:  # 突破阻力位1-5%
                confidence = nearest_resistance.strength * 0.7
                if analysis.volume_trend == 'increasing':
                    confidence *= 1.2
                buy_signals.append((confidence, f"突破阻力位{nearest_resistance.level:.2f}"))
        
        # 3. 趋势买入信号
        if analysis.trend == 'bullish' and analysis.momentum > 0.05:
            confidence = min(analysis.momentum * 10, 0.8)
            buy_signals.append((confidence, "上升趋势强劲"))
        
        # 卖出信号分析
        # 1. 接近阻力位卖出信号
        if nearest_resistance:
            resistance_distance = (nearest_resistance.level - current_price) / current_price
            if 0 <= resistance_distance <= 0.02:  # 接近阻力位2%
                confidence = nearest_resistance.strength * 0.8
                sell_signals.append((confidence, f"接近阻力位{nearest_resistance.level:.2f}"))
        
        # 2. 跌破支撑位卖出信号
        if nearest_support:
            support_distance = (nearest_support.level - current_price) / nearest_support.level
            if 0.01 <= support_distance <= 0.05:  # 跌破支撑位1-5%
                confidence = nearest_support.strength * 0.9
                sell_signals.append((confidence, f"跌破支撑位{nearest_support.level:.2f}"))
        
        # 3. 趋势卖出信号
        if analysis.trend == 'bearish' and analysis.momentum < -0.05:
            confidence = min(abs(analysis.momentum) * 10, 0.8)
            sell_signals.append((confidence, "下降趋势强劲"))
        
        # 决策逻辑
        max_buy_confidence = max([s[0] for s in buy_signals], default=0)
        max_sell_confidence = max([s[0] for s in sell_signals], default=0)
        
        # 设置最小信心度阈值
        min_confidence = 0.6
        
        if max_buy_confidence > max_sell_confidence and max_buy_confidence >= min_confidence:
            best_buy_signal = max(buy_signals, key=lambda x: x[0])
            return TradeAction.BUY, best_buy_signal[0], best_buy_signal[1]
        elif max_sell_confidence > max_buy_confidence and max_sell_confidence >= min_confidence:
            best_sell_signal = max(sell_signals, key=lambda x: x[0])
            return TradeAction.SELL, best_sell_signal[0], best_sell_signal[1]
        else:
            return TradeAction.HOLD, 0.0, "无明确信号"
    
    def _find_nearest_level(self, current_price: float, levels: List[SupportResistanceLevel], 
                           direction: str) -> Optional[SupportResistanceLevel]:
        """寻找最近的支撑/阻力位
        
        Args:
            current_price: 当前价格
            levels: 支撑/阻力位列表
            direction: 'above' 或 'below'
            
        Returns:
            最近的支撑/阻力位
        """
        if not levels:
            return None
        
        if direction == 'above':
            # 寻找当前价格之上最近的阻力位
            above_levels = [level for level in levels if level.level > current_price]
            if above_levels:
                return min(above_levels, key=lambda x: x.level - current_price)
        else:  # below
            # 寻找当前价格之下最近的支撑位
            below_levels = [level for level in levels if level.level < current_price]
            if below_levels:
                return max(below_levels, key=lambda x: x.level)
        
        return None
    
    def _calculate_position_size(self, price: float) -> int:
        """计算仓位大小
        
        Args:
            price: 股票价格
            
        Returns:
            股票数量
        """
        if price <= 0:
            return 0
            
        # 基于最大仓位大小计算
        max_shares = int(self.max_position_size / price)
        
        # 确保是100的倍数（A股交易单位）
        return (max_shares // 100) * 100
    
    def _standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化数据框列名
        
        Args:
            df: 原始数据框
            
        Returns:
            标准化后的数据框
        """
        # 常见的列名映射
        column_mapping = {
            # Tushare格式
            'trade_date': 'date',
            'ts_code': 'symbol',
            'vol': 'volume',
            
            # Akshare格式
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            
            # 其他可能的格式
            'Open': 'open',
            'Close': 'close',
            'High': 'high',
            'Low': 'low',
            'Volume': 'volume'
        }
        
        # 重命名列
        df_copy = df.copy()
        for old_name, new_name in column_mapping.items():
            if old_name in df_copy.columns:
                df_copy = df_copy.rename(columns={old_name: new_name})
        
        # 确保必要的列存在
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in df_copy.columns:
                self.logger.warning(f"缺少必要列: {col}")
        
        return df_copy
    
    def get_strategy_info(self) -> Dict:
        """获取策略信息
        
        Returns:
            策略信息字典
        """
        return {
            'name': 'pressure_support_strategy',
            'description': '基于压力位和支撑位的交易策略',
            'parameters': {
                'analysis_period_months': self.analysis_period,
                'pressure_factor': self.pressure_factor,
                'support_factor': self.support_factor,
                'volume_threshold': self.volume_threshold,
                'max_position_size': self.max_position_size,
                'stop_loss': self.stop_loss,
                'take_profit': self.take_profit
            },
            'risk_management': {
                'position_sizing': 'fixed_amount',
                'stop_loss_enabled': True,
                'take_profit_enabled': True
            }
        }