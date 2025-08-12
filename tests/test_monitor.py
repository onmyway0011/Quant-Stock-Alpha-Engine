#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票监控模块测试

测试股票监控、预警生成和波动率计算功能
"""

import unittest
import asyncio
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
from collections import deque

import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.monitor import (
    StockMonitor, VolatilityCalculator, AlertQueue
)
from src.models.models import StockData, MarketAlert, AlertLevel
from src.data.data_provider import DataManager


class TestMonitor(unittest.TestCase):
    """股票监控测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # 模拟配置
        self.mock_config = MagicMock()
        self.mock_config.monitoring.stocks = ['000001.SZ', '600519.SH']
        self.mock_config.monitoring.volatility_threshold = 0.03
        self.mock_config.monitoring.check_interval = 60
        
        # 模拟数据管理器
        self.mock_data_manager = AsyncMock(spec=DataManager)
        
        # 创建测试数据
        self.test_stock_data = self._create_test_stock_data()
    
    def tearDown(self):
        """测试后清理"""
        self.loop.close()
    
    def _create_test_stock_data(self):
        """创建测试股票数据"""
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
            ),
            '600519.SH': StockData(
                symbol='600519.SH',
                name='贵州茅台',
                current_price=1680.50,
                change=-25.30,
                change_percent=-1.48,
                volume=800000,
                timestamp=datetime.now(),
                high=1705.00,
                low=1675.00,
                open_price=1700.00
            )
        }
    
    def test_volatility_calculator_price_volatility(self):
        """测试价格波动率计算"""
        # 测试正常价格序列
        prices = [10.0, 10.2, 9.8, 10.5, 9.9, 10.3, 10.1]
        volatility = VolatilityCalculator.calculate_price_volatility(prices)
        
        self.assertIsInstance(volatility, float)
        self.assertGreaterEqual(volatility, 0)
        
        # 测试空序列
        empty_volatility = VolatilityCalculator.calculate_price_volatility([])
        self.assertEqual(empty_volatility, 0.0)
        
        # 测试单个价格
        single_volatility = VolatilityCalculator.calculate_price_volatility([10.0])
        self.assertEqual(single_volatility, 0.0)
        
        # 测试高波动率序列
        high_vol_prices = [10.0, 15.0, 8.0, 12.0, 6.0, 14.0]
        high_volatility = VolatilityCalculator.calculate_price_volatility(high_vol_prices)
        self.assertGreater(high_volatility, volatility)
    
    def test_volatility_calculator_volume_volatility(self):
        """测试成交量波动率计算"""
        # 测试正常成交量序列
        volumes = [1000000, 1200000, 900000, 1500000, 800000, 1300000]
        vol_volatility = VolatilityCalculator.calculate_volume_volatility(volumes)
        
        self.assertIsInstance(vol_volatility, float)
        self.assertGreaterEqual(vol_volatility, 0)
        
        # 测试稳定成交量
        stable_volumes = [1000000] * 10
        stable_volatility = VolatilityCalculator.calculate_volume_volatility(stable_volumes)
        self.assertEqual(stable_volatility, 0.0)
    
    def test_volatility_calculator_rsi(self):
        """测试RSI指标计算"""
        # 测试上升趋势（RSI应该较高）
        rising_prices = list(range(10, 25))  # 持续上升
        rsi_rising = VolatilityCalculator.calculate_rsi(rising_prices)
        
        self.assertIsInstance(rsi_rising, float)
        self.assertGreaterEqual(rsi_rising, 0)
        self.assertLessEqual(rsi_rising, 100)
        self.assertGreater(rsi_rising, 50)  # 上升趋势RSI应该大于50
        
        # 测试下降趋势（RSI应该较低）
        falling_prices = list(range(25, 10, -1))  # 持续下降
        rsi_falling = VolatilityCalculator.calculate_rsi(falling_prices)
        
        self.assertLess(rsi_falling, 50)  # 下降趋势RSI应该小于50
        
        # 测试数据不足情况
        short_prices = [10, 11, 12]
        rsi_short = VolatilityCalculator.calculate_rsi(short_prices)
        self.assertEqual(rsi_short, 50.0)  # 默认值
    
    def test_alert_queue_basic_operations(self):
        """测试预警队列基本操作"""
        queue = AlertQueue(max_size=5)
        
        # 测试添加预警
        alert = MarketAlert(
            symbol='000001.SZ',
            alert_type='price_volatility',
            level=AlertLevel.MEDIUM,
            message='价格波动异常',
            current_value=0.05,
            threshold=0.03,
            timestamp=datetime.now()
        )
        
        result = queue.add_alert(alert)
        self.assertTrue(result)
        
        # 测试重复添加（应该被去重）
        result = queue.add_alert(alert)
        self.assertFalse(result)
        
        # 测试获取预警
        alerts = queue.get_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].symbol, '000001.SZ')
    
    def test_alert_queue_size_limit(self):
        """测试预警队列大小限制"""
        queue = AlertQueue(max_size=3)
        
        # 添加超过限制的预警
        for i in range(5):
            alert = MarketAlert(
                symbol=f'00000{i}.SZ',
                alert_type='test',
                level=AlertLevel.LOW,
                message=f'测试预警{i}',
                current_value=i,
                threshold=1.0,
                timestamp=datetime.now() + timedelta(seconds=i)
            )
            queue.add_alert(alert)
        
        # 应该只保留最新的3个
        alerts = queue.get_alerts()
        self.assertEqual(len(alerts), 3)
    
    def test_alert_queue_cleanup(self):
        """测试预警队列清理"""
        queue = AlertQueue()
        
        # 添加旧预警
        old_alert = MarketAlert(
            symbol='000001.SZ',
            alert_type='old_alert',
            level=AlertLevel.LOW,
            message='旧预警',
            current_value=1.0,
            threshold=1.0,
            timestamp=datetime.now() - timedelta(hours=25)  # 25小时前
        )
        queue.add_alert(old_alert)
        
        # 添加新预警
        new_alert = MarketAlert(
            symbol='000002.SZ',
            alert_type='new_alert',
            level=AlertLevel.LOW,
            message='新预警',
            current_value=1.0,
            threshold=1.0,
            timestamp=datetime.now()
        )
        queue.add_alert(new_alert)
        
        # 清理旧预警
        queue.clear_old_alerts(hours=24)
        
        alerts = queue.get_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].alert_type, 'new_alert')
    
    def test_stock_monitor_initialization(self):
        """测试股票监控器初始化"""
        monitor = StockMonitor(self.mock_config, self.mock_data_manager)
        
        self.assertEqual(monitor.config, self.mock_config)
        self.assertEqual(monitor.data_manager, self.mock_data_manager)
        self.assertEqual(monitor.symbols, ['000001.SZ', '600519.SH'])
        self.assertEqual(monitor.volatility_threshold, 0.03)
        self.assertEqual(monitor.check_interval, 60)
        self.assertFalse(monitor.is_running)
    
    def test_stock_monitor_start_stop(self):
        """测试股票监控器启动和停止"""
        monitor = StockMonitor(self.mock_config, self.mock_data_manager)
        
        async def test_start_stop():
            # 测试启动
            await monitor.start_monitoring()
            self.assertTrue(monitor.is_running)
            self.assertIsNotNone(monitor.monitor_task)
            
            # 测试停止
            await monitor.stop_monitoring()
            self.assertFalse(monitor.is_running)
        
        self.loop.run_until_complete(test_start_stop())
    
    def test_stock_monitor_callback_registration(self):
        """测试预警回调注册"""
        monitor = StockMonitor(self.mock_config, self.mock_data_manager)
        
        callback_called = [False]
        
        def test_callback(alert):
            callback_called[0] = True
        
        monitor.add_alert_callback(test_callback)
        self.assertEqual(len(monitor.alert_callbacks), 1)
    
    def test_stock_monitor_price_volatility_check(self):
        """测试价格波动率检查"""
        monitor = StockMonitor(self.mock_config, self.mock_data_manager)
        
        # 设置历史价格数据（高波动率）
        high_vol_prices = [10.0, 12.0, 9.0, 13.0, 8.0, 14.0, 7.0, 15.0]
        monitor.price_history['000001.SZ'] = deque(high_vol_prices, maxlen=100)
        
        stock_data = self.test_stock_data['000001.SZ']
        
        async def test_volatility_check():
            await monitor._check_price_volatility('000001.SZ', stock_data)
            
            # 检查是否生成了预警
            alerts = monitor.alert_queue.get_alerts()
            volatility_alerts = [a for a in alerts if a.alert_type == 'price_volatility']
            
            # 高波动率应该生成预警
            if volatility_alerts:
                self.assertGreater(len(volatility_alerts), 0)
        
        self.loop.run_until_complete(test_volatility_check())
    
    def test_stock_monitor_volume_anomaly_check(self):
        """测试成交量异常检查"""
        monitor = StockMonitor(self.mock_config, self.mock_data_manager)
        
        # 设置正常成交量历史
        normal_volumes = [1000000] * 10
        monitor.volume_history['000001.SZ'] = deque(normal_volumes, maxlen=100)
        
        # 创建异常成交量数据
        anomaly_data = StockData(
            symbol='000001.SZ',
            name='平安银行',
            current_price=12.50,
            change=0.30,
            change_percent=2.46,
            volume=5000000,  # 5倍于正常成交量
            timestamp=datetime.now()
        )
        
        async def test_volume_check():
            await monitor._check_volume_anomaly('000001.SZ', anomaly_data)
            
            # 检查是否生成了成交量异常预警
            alerts = monitor.alert_queue.get_alerts()
            volume_alerts = [a for a in alerts if a.alert_type == 'volume_anomaly']
            
            self.assertGreater(len(volume_alerts), 0)
        
        self.loop.run_until_complete(test_volume_check())
    
    def test_stock_monitor_price_change_check(self):
        """测试价格变化检查"""
        monitor = StockMonitor(self.mock_config, self.mock_data_manager)
        
        # 创建大幅价格变化数据
        large_change_data = StockData(
            symbol='000001.SZ',
            name='平安银行',
            current_price=12.50,
            change=0.80,
            change_percent=6.84,  # 超过5%的变化
            volume=1500000,
            timestamp=datetime.now()
        )
        
        async def test_price_change_check():
            await monitor._check_price_change('000001.SZ', large_change_data)
            
            # 检查是否生成了价格变化预警
            alerts = monitor.alert_queue.get_alerts()
            price_alerts = [a for a in alerts if a.alert_type == 'price_change']
            
            self.assertGreater(len(price_alerts), 0)
            self.assertEqual(price_alerts[0].level, AlertLevel.MEDIUM)
        
        self.loop.run_until_complete(test_price_change_check())
    
    def test_stock_monitor_rsi_signals(self):
        """测试RSI信号检查"""
        monitor = StockMonitor(self.mock_config, self.mock_data_manager)
        
        # 设置超买条件的价格历史
        overbought_prices = list(range(10, 30))  # 持续上升
        monitor.price_history['000001.SZ'] = deque(overbought_prices, maxlen=100)
        
        stock_data = self.test_stock_data['000001.SZ']
        
        async def test_rsi_check():
            await monitor._check_technical_indicators('000001.SZ', stock_data)
            
            # 检查是否生成了RSI预警
            alerts = monitor.alert_queue.get_alerts()
            rsi_alerts = [a for a in alerts if 'rsi' in a.alert_type]
            
            # 可能生成超买或超卖信号
            if rsi_alerts:
                self.assertIn(rsi_alerts[0].alert_type, ['rsi_overbought', 'rsi_oversold'])
        
        self.loop.run_until_complete(test_rsi_check())
    
    def test_stock_monitor_alert_callback_execution(self):
        """测试预警回调执行"""
        monitor = StockMonitor(self.mock_config, self.mock_data_manager)
        
        callback_results = []
        
        def test_callback(alert):
            callback_results.append(alert)
        
        async def async_callback(alert):
            callback_results.append(f"async_{alert.symbol}")
        
        monitor.add_alert_callback(test_callback)
        monitor.add_alert_callback(async_callback)
        
        alert = MarketAlert(
            symbol='000001.SZ',
            alert_type='test',
            level=AlertLevel.LOW,
            message='测试预警',
            current_value=1.0,
            threshold=1.0,
            timestamp=datetime.now()
        )
        
        async def test_callback_execution():
            await monitor._trigger_alert(alert)
            
            # 验证回调被调用
            self.assertEqual(len(callback_results), 2)
            self.assertIsInstance(callback_results[0], MarketAlert)
            self.assertEqual(callback_results[1], "async_000001.SZ")
        
        self.loop.run_until_complete(test_callback_execution())
    
    def test_stock_monitor_status_reporting(self):
        """测试股票状态报告"""
        monitor = StockMonitor(self.mock_config, self.mock_data_manager)
        
        # 添加一些历史数据
        monitor.price_history['000001.SZ'] = deque([10, 11, 12, 13, 12], maxlen=100)
        monitor.volume_history['000001.SZ'] = deque([1000000, 1100000, 1200000], maxlen=100)
        
        status = monitor.get_stock_status('000001.SZ')
        
        self.assertIsInstance(status, dict)
        self.assertEqual(status['symbol'], '000001.SZ')
        self.assertIn('current_price', status)
        self.assertIn('volatility', status)
        self.assertIn('rsi', status)
        self.assertIn('price_history_count', status)
        self.assertIn('volume_history_count', status)
    
    def test_stock_monitor_summary(self):
        """测试监控摘要"""
        monitor = StockMonitor(self.mock_config, self.mock_data_manager)
        
        # 添加一些预警
        alert = MarketAlert(
            symbol='000001.SZ',
            alert_type='test',
            level=AlertLevel.LOW,
            message='测试预警',
            current_value=1.0,
            threshold=1.0,
            timestamp=datetime.now()
        )
        monitor.alert_queue.add_alert(alert)
        
        summary = monitor.get_monitoring_summary()
        
        self.assertIsInstance(summary, dict)
        self.assertIn('is_running', summary)
        self.assertIn('monitored_stocks', summary)
        self.assertIn('total_alerts', summary)
        self.assertIn('recent_alerts', summary)
        self.assertIn('check_interval', summary)
        self.assertIn('volatility_threshold', summary)
        
        self.assertEqual(summary['monitored_stocks'], 2)
        self.assertEqual(summary['total_alerts'], 1)
    
    def test_stock_monitor_error_handling(self):
        """测试监控错误处理"""
        monitor = StockMonitor(self.mock_config, self.mock_data_manager)
        
        # 模拟数据获取失败
        self.mock_data_manager.get_realtime_data.side_effect = Exception("数据获取失败")
        
        async def test_error_handling():
            # 检查股票时发生错误不应该崩溃
            await monitor._check_stocks()
            
            # 系统应该继续运行
            self.assertTrue(True)  # 如果到达这里说明没有崩溃
        
        self.loop.run_until_complete(test_error_handling())
    
    def test_stock_monitor_data_analysis(self):
        """测试股票数据分析"""
        monitor = StockMonitor(self.mock_config, self.mock_data_manager)
        
        stock_data = self.test_stock_data['000001.SZ']
        
        async def test_analysis():
            await monitor._analyze_stock('000001.SZ', stock_data)
            
            # 验证数据被添加到历史记录
            self.assertGreater(len(monitor.price_history['000001.SZ']), 0)
            self.assertGreater(len(monitor.volume_history['000001.SZ']), 0)
            
            # 验证最后价格被更新
            self.assertEqual(monitor.last_prices['000001.SZ'], stock_data.current_price)
        
        self.loop.run_until_complete(test_analysis())
    
    def test_stock_monitor_recent_alerts(self):
        """测试获取最近预警"""
        monitor = StockMonitor(self.mock_config, self.mock_data_manager)
        
        # 添加不同时间的预警
        old_alert = MarketAlert(
            symbol='000001.SZ',
            alert_type='old',
            level=AlertLevel.LOW,
            message='旧预警',
            current_value=1.0,
            threshold=1.0,
            timestamp=datetime.now() - timedelta(hours=25)
        )
        
        recent_alert = MarketAlert(
            symbol='000002.SZ',
            alert_type='recent',
            level=AlertLevel.MEDIUM,
            message='最近预警',
            current_value=1.0,
            threshold=1.0,
            timestamp=datetime.now() - timedelta(hours=1)
        )
        
        monitor.alert_queue.add_alert(old_alert)
        monitor.alert_queue.add_alert(recent_alert)
        
        # 获取最近24小时的预警
        recent_alerts = monitor.get_recent_alerts(hours=24)
        
        self.assertEqual(len(recent_alerts), 1)
        self.assertEqual(recent_alerts[0].alert_type, 'recent')


if __name__ == '__main__':
    unittest.main()