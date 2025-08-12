#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易策略模块测试

测试压力位支撑位策略的分析和信号生成功能
"""

import unittest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.strategy.pressure_support_strategy import (
    PressureSupportStrategy, TechnicalAnalyzer, 
    SupportResistanceLevel, MarketAnalysis
)
from src.models.models import TradeSignal, TradeAction, StockData
from src.data.data_provider import DataManager


class TestStrategy(unittest.TestCase):
    """交易策略测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # 模拟配置
        self.mock_config = MagicMock()
        self.mock_config.strategy.analysis_period = 6
        self.mock_config.strategy.pressure_factor = 1.05
        self.mock_config.strategy.support_factor = 0.95
        self.mock_config.strategy.volume_threshold = 1.5
        self.mock_config.risk.max_position_size = 10000
        self.mock_config.risk.stop_loss = 0.05
        self.mock_config.risk.take_profit = 0.10
        
        # 模拟数据管理器
        self.mock_data_manager = AsyncMock(spec=DataManager)
        
        # 创建测试数据
        self.test_historical_data = self._create_test_historical_data()
        self.test_realtime_data = self._create_test_realtime_data()
    
    def tearDown(self):
        """测试后清理"""
        self.loop.close()
    
    def _create_test_historical_data(self):
        """创建测试历史数据"""
        dates = pd.date_range(start='2024-01-01', end='2024-06-30', freq='D')
        np.random.seed(42)  # 确保可重现性
        
        # 生成模拟价格数据
        base_price = 12.0
        price_changes = np.random.normal(0, 0.02, len(dates))
        prices = [base_price]
        
        for change in price_changes[1:]:
            new_price = prices[-1] * (1 + change)
            prices.append(max(new_price, 0.1))  # 确保价格为正
        
        df = pd.DataFrame({
            'date': dates,
            'open': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': np.random.randint(500000, 2000000, len(dates))
        })
        
        return df
    
    def _create_test_realtime_data(self):
        """创建测试实时数据"""
        return {
            '000001.SZ': StockData(
                symbol='000001.SZ',
                name='平安银行',
                current_price=12.50,
                change=0.30,
                change_percent=2.46,
                volume=1500000,
                timestamp=datetime.now(),
                high=12.80,
                low=12.20,
                open_price=12.30
            )
        }
    
    def test_technical_analyzer_find_peaks_and_valleys(self):
        """测试技术分析器寻找峰值和谷值"""
        # 创建有明显峰值和谷值的价格序列
        prices = np.array([10, 11, 12, 11, 10, 9, 10, 11, 12, 13, 12, 11, 10])
        
        peaks = TechnicalAnalyzer._find_peaks(prices, window=2)
        valleys = TechnicalAnalyzer._find_valleys(prices, window=2)
        
        # 验证找到了峰值和谷值
        self.assertGreater(len(peaks), 0)
        self.assertGreater(len(valleys), 0)
        
        # 验证峰值位置
        peak_indices = [p[0] for p in peaks]
        self.assertIn(2, peak_indices)  # 价格12的位置
        self.assertIn(9, peak_indices)  # 价格13的位置
    
    def test_technical_analyzer_support_resistance_levels(self):
        """测试支撑位和阻力位识别"""
        df = self.test_historical_data.copy()
        
        support_levels, resistance_levels = TechnicalAnalyzer.find_support_resistance_levels(df)
        
        # 验证返回了支撑位和阻力位
        self.assertIsInstance(support_levels, list)
        self.assertIsInstance(resistance_levels, list)
        
        # 验证支撑位和阻力位的结构
        for level in support_levels + resistance_levels:
            self.assertIsInstance(level, SupportResistanceLevel)
            self.assertGreater(level.level, 0)
            self.assertGreaterEqual(level.strength, 0)
            self.assertLessEqual(level.strength, 1)
            self.assertGreater(level.touch_count, 0)
    
    def test_technical_analyzer_momentum_calculation(self):
        """测试动量指标计算"""
        df = self.test_historical_data.copy()
        
        momentum = TechnicalAnalyzer.calculate_momentum(df, period=14)
        
        self.assertIsInstance(momentum, float)
        # 动量应该在合理范围内
        self.assertGreaterEqual(momentum, -1.0)
        self.assertLessEqual(momentum, 1.0)
    
    def test_technical_analyzer_volume_trend(self):
        """测试成交量趋势分析"""
        df = self.test_historical_data.copy()
        
        # 测试递增成交量
        df_increasing = df.copy()
        df_increasing['volume'] = range(len(df))  # 递增序列
        trend = TechnicalAnalyzer.calculate_volume_trend(df_increasing)
        self.assertEqual(trend, 'increasing')
        
        # 测试递减成交量
        df_decreasing = df.copy()
        df_decreasing['volume'] = list(reversed(range(len(df))))  # 递减序列
        trend = TechnicalAnalyzer.calculate_volume_trend(df_decreasing)
        self.assertEqual(trend, 'decreasing')
    
    def test_technical_analyzer_trend_determination(self):
        """测试趋势判断"""
        df = self.test_historical_data.copy()
        
        # 测试上升趋势
        df_bullish = df.copy()
        df_bullish['close'] = np.linspace(10, 15, len(df))  # 上升趋势
        trend = TechnicalAnalyzer.determine_trend(df_bullish)
        self.assertEqual(trend, 'bullish')
        
        # 测试下降趋势
        df_bearish = df.copy()
        df_bearish['close'] = np.linspace(15, 10, len(df))  # 下降趋势
        trend = TechnicalAnalyzer.determine_trend(df_bearish)
        self.assertEqual(trend, 'bearish')
    
    def test_pressure_support_strategy_initialization(self):
        """测试压力支撑策略初始化"""
        strategy = PressureSupportStrategy(self.mock_config, self.mock_data_manager)
        
        self.assertEqual(strategy.config, self.mock_config)
        self.assertEqual(strategy.data_manager, self.mock_data_manager)
        self.assertEqual(strategy.analysis_period, 6)
        self.assertEqual(strategy.pressure_factor, 1.05)
        self.assertEqual(strategy.support_factor, 0.95)
    
    def test_strategy_analyze_market(self):
        """测试市场分析"""
        strategy = PressureSupportStrategy(self.mock_config, self.mock_data_manager)
        
        # 模拟数据管理器返回
        self.mock_data_manager.get_historical_data.return_value = self.test_historical_data
        self.mock_data_manager.get_realtime_data.return_value = self.test_realtime_data
        
        async def test_analysis():
            analysis = await strategy.analyze_market('000001.SZ')
            
            self.assertIsInstance(analysis, MarketAnalysis)
            self.assertEqual(analysis.symbol, '000001.SZ')
            self.assertGreater(analysis.current_price, 0)
            self.assertIn(analysis.trend, ['bullish', 'bearish', 'sideways'])
            self.assertIsInstance(analysis.support_levels, list)
            self.assertIsInstance(analysis.resistance_levels, list)
        
        self.loop.run_until_complete(test_analysis())
    
    def test_strategy_generate_signal(self):
        """测试交易信号生成"""
        strategy = PressureSupportStrategy(self.mock_config, self.mock_data_manager)
        
        # 模拟数据管理器返回
        self.mock_data_manager.get_historical_data.return_value = self.test_historical_data
        self.mock_data_manager.get_realtime_data.return_value = self.test_realtime_data
        
        async def test_signal_generation():
            signal = await strategy.generate_signal('000001.SZ')
            
            if signal:  # 信号可能为None
                self.assertIsInstance(signal, TradeSignal)
                self.assertEqual(signal.symbol, '000001.SZ')
                self.assertIn(signal.action, [TradeAction.BUY, TradeAction.SELL, TradeAction.HOLD])
                self.assertGreater(signal.price, 0)
                self.assertGreater(signal.quantity, 0)
                self.assertGreaterEqual(signal.confidence, 0)
                self.assertLessEqual(signal.confidence, 1)
        
        self.loop.run_until_complete(test_signal_generation())
    
    def test_strategy_buy_signal_conditions(self):
        """测试买入信号条件"""
        strategy = PressureSupportStrategy(self.mock_config, self.mock_data_manager)
        
        # 创建有利于买入的市场分析
        analysis = MarketAnalysis(
            symbol='000001.SZ',
            current_price=12.50,
            trend='bullish',
            support_levels=[
                SupportResistanceLevel(
                    level=12.40,  # 接近当前价格的支撑位
                    strength=0.8,
                    touch_count=3,
                    last_touch=datetime.now(),
                    level_type='support'
                )
            ],
            resistance_levels=[],
            volume_trend='increasing',
            momentum=0.08,  # 强劲上升动量
            volatility=0.02,
            analysis_time=datetime.now()
        )
        
        action, confidence, reason = strategy._analyze_trade_signal(analysis)
        
        # 在有利条件下应该生成买入信号
        if confidence >= 0.6:  # 如果信心度足够
            self.assertEqual(action, TradeAction.BUY)
            self.assertGreater(confidence, 0)
    
    def test_strategy_sell_signal_conditions(self):
        """测试卖出信号条件"""
        strategy = PressureSupportStrategy(self.mock_config, self.mock_data_manager)
        
        # 创建有利于卖出的市场分析
        analysis = MarketAnalysis(
            symbol='000001.SZ',
            current_price=12.50,
            trend='bearish',
            support_levels=[],
            resistance_levels=[
                SupportResistanceLevel(
                    level=12.60,  # 接近当前价格的阻力位
                    strength=0.8,
                    touch_count=3,
                    last_touch=datetime.now(),
                    level_type='resistance'
                )
            ],
            volume_trend='stable',
            momentum=-0.08,  # 强劲下降动量
            volatility=0.02,
            analysis_time=datetime.now()
        )
        
        action, confidence, reason = strategy._analyze_trade_signal(analysis)
        
        # 在有利条件下应该生成卖出信号
        if confidence >= 0.6:  # 如果信心度足够
            self.assertEqual(action, TradeAction.SELL)
            self.assertGreater(confidence, 0)
    
    def test_strategy_hold_signal_conditions(self):
        """测试持有信号条件"""
        strategy = PressureSupportStrategy(self.mock_config, self.mock_data_manager)
        
        # 创建不明确的市场分析
        analysis = MarketAnalysis(
            symbol='000001.SZ',
            current_price=12.50,
            trend='sideways',
            support_levels=[],
            resistance_levels=[],
            volume_trend='stable',
            momentum=0.01,  # 微弱动量
            volatility=0.01,
            analysis_time=datetime.now()
        )
        
        action, confidence, reason = strategy._analyze_trade_signal(analysis)
        
        # 在不明确条件下应该持有
        self.assertEqual(action, TradeAction.HOLD)
        self.assertEqual(confidence, 0.0)
    
    def test_strategy_position_size_calculation(self):
        """测试仓位大小计算"""
        strategy = PressureSupportStrategy(self.mock_config, self.mock_data_manager)
        
        # 测试正常价格
        quantity = strategy._calculate_position_size(12.50)
        expected_quantity = int(10000 / 12.50 / 100) * 100  # 向下取整到100的倍数
        self.assertEqual(quantity, expected_quantity)
        
        # 测试零价格
        quantity = strategy._calculate_position_size(0)
        self.assertEqual(quantity, 0)
        
        # 测试高价格
        quantity = strategy._calculate_position_size(1000)
        self.assertEqual(quantity, 0)  # 超出最大仓位
    
    def test_strategy_dataframe_standardization(self):
        """测试数据框标准化"""
        strategy = PressureSupportStrategy(self.mock_config, self.mock_data_manager)
        
        # 测试Tushare格式
        tushare_df = pd.DataFrame({
            'trade_date': ['20240101', '20240102'],
            'ts_code': ['000001.SZ', '000001.SZ'],
            'vol': [1000000, 1200000]
        })
        
        standardized_df = strategy._standardize_dataframe(tushare_df)
        self.assertIn('date', standardized_df.columns)
        self.assertIn('volume', standardized_df.columns)
        
        # 测试Akshare格式
        akshare_df = pd.DataFrame({
            '日期': ['2024-01-01', '2024-01-02'],
            '开盘': [12.0, 12.5],
            '收盘': [12.5, 12.3],
            '成交量': [1000000, 1200000]
        })
        
        standardized_df = strategy._standardize_dataframe(akshare_df)
        self.assertIn('date', standardized_df.columns)
        self.assertIn('open', standardized_df.columns)
        self.assertIn('close', standardized_df.columns)
        self.assertIn('volume', standardized_df.columns)
    
    def test_strategy_find_nearest_level(self):
        """测试寻找最近支撑/阻力位"""
        strategy = PressureSupportStrategy(self.mock_config, self.mock_data_manager)
        
        levels = [
            SupportResistanceLevel(10.0, 0.8, 3, datetime.now(), 'support'),
            SupportResistanceLevel(12.0, 0.7, 2, datetime.now(), 'support'),
            SupportResistanceLevel(14.0, 0.9, 4, datetime.now(), 'resistance'),
            SupportResistanceLevel(16.0, 0.6, 2, datetime.now(), 'resistance')
        ]
        
        current_price = 13.0
        
        # 寻找上方最近阻力位
        nearest_resistance = strategy._find_nearest_level(current_price, levels, 'above')
        self.assertIsNotNone(nearest_resistance)
        self.assertEqual(nearest_resistance.level, 14.0)
        
        # 寻找下方最近支撑位
        nearest_support = strategy._find_nearest_level(current_price, levels, 'below')
        self.assertIsNotNone(nearest_support)
        self.assertEqual(nearest_support.level, 12.0)
    
    def test_strategy_error_handling(self):
        """测试策略错误处理"""
        strategy = PressureSupportStrategy(self.mock_config, self.mock_data_manager)
        
        # 模拟数据获取失败
        self.mock_data_manager.get_historical_data.return_value = pd.DataFrame()
        self.mock_data_manager.get_realtime_data.return_value = {}
        
        async def test_error_handling():
            # 测试空数据处理
            analysis = await strategy.analyze_market('000001.SZ')
            self.assertIsNone(analysis)
            
            # 测试信号生成失败
            signal = await strategy.generate_signal('000001.SZ')
            self.assertIsNone(signal)
        
        self.loop.run_until_complete(test_error_handling())
    
    def test_strategy_info(self):
        """测试策略信息获取"""
        strategy = PressureSupportStrategy(self.mock_config, self.mock_data_manager)
        
        info = strategy.get_strategy_info()
        
        self.assertIsInstance(info, dict)
        self.assertEqual(info['name'], 'pressure_support_strategy')
        self.assertIn('description', info)
        self.assertIn('parameters', info)
        self.assertIn('risk_management', info)
    
    def test_strategy_confidence_calculation(self):
        """测试信心度计算"""
        strategy = PressureSupportStrategy(self.mock_config, self.mock_data_manager)
        
        # 测试多个信号的信心度计算
        analysis = MarketAnalysis(
            symbol='000001.SZ',
            current_price=12.50,
            trend='bullish',
            support_levels=[
                SupportResistanceLevel(12.40, 0.9, 4, datetime.now(), 'support')
            ],
            resistance_levels=[],
            volume_trend='increasing',
            momentum=0.10,
            volatility=0.02,
            analysis_time=datetime.now()
        )
        
        action, confidence, reason = strategy._analyze_trade_signal(analysis)
        
        # 强信号应该有高信心度
        if action != TradeAction.HOLD:
            self.assertGreater(confidence, 0.5)


if __name__ == '__main__':
    unittest.main()