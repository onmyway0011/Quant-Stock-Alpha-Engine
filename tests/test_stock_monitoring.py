#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票监控功能测试

测试股票监控服务、技术指标计算、预警功能等
"""

import unittest
import asyncio
import tempfile
import os
import yaml
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
import numpy as np
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
# 确保src包可导入
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from src.core.stock_monitor import (
    StockMonitorService, TechnicalIndicators, StockAlert, AlertType
)
from src.core.config import StockThresholdConfig
from src.models.models import AlertLevel, StockData
from src.notification.wecom_notifier import NotificationManager, StockAlertType


class TestTechnicalIndicators(unittest.TestCase):
    """技术指标计算测试"""
    
    def setUp(self):
        self.indicators = TechnicalIndicators()
        
        # 创建测试数据
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(50) * 0.5)
        volumes = np.random.randint(1000, 10000, 50)
        
        self.test_data = pd.DataFrame({
            'date': dates,
            'close': prices,
            'volume': volumes
        })
    
    def test_rsi_calculation(self):
        """测试RSI计算"""
        rsi = self.indicators.calculate_rsi(self.test_data['close'])
        
        # RSI应该在0-100之间
        self.assertGreaterEqual(rsi, 0)
        self.assertLessEqual(rsi, 100)
        
        # 测试数据不足的情况
        short_prices = pd.Series([100, 101, 102])
        rsi_short = self.indicators.calculate_rsi(short_prices)
        self.assertEqual(rsi_short, 50.0)  # 默认中性值
    
    def test_macd_calculation(self):
        """测试MACD计算"""
        macd, signal, histogram = self.indicators.calculate_macd(self.test_data['close'])
        
        # 返回值应该是数字
        self.assertIsInstance(macd, float)
        self.assertIsInstance(signal, float)
        self.assertIsInstance(histogram, float)
        
        # 测试数据不足的情况
        short_prices = pd.Series([100, 101, 102])
        macd_short, signal_short, hist_short = self.indicators.calculate_macd(short_prices)
        self.assertEqual(macd_short, 0.0)
        self.assertEqual(signal_short, 0.0)
        self.assertEqual(hist_short, 0.0)
    
    def test_price_change_calculation(self):
        """测试价格变动计算"""
        # 正常情况
        change = self.indicators.calculate_price_change(110, 100)
        self.assertAlmostEqual(change, 0.1, places=2)
        
        # 下跌情况
        change = self.indicators.calculate_price_change(90, 100)
        self.assertAlmostEqual(change, -0.1, places=2)
        
        # 除零情况
        change = self.indicators.calculate_price_change(100, 0)
        self.assertEqual(change, 0.0)
    
    def test_volume_ratio_calculation(self):
        """测试成交量比率计算"""
        # 正常情况
        ratio = self.indicators.calculate_volume_ratio(2000, 1000)
        self.assertEqual(ratio, 2.0)
        
        # 除零情况
        ratio = self.indicators.calculate_volume_ratio(1000, 0)
        self.assertEqual(ratio, 1.0)


class TestStockMonitorService(unittest.TestCase):
    """股票监控服务测试"""
    
    def setUp(self):
        # 创建模拟对象
        self.mock_data_manager = Mock()
        self.mock_notification_manager = Mock()
        
        # 创建监控服务
        self.monitor_service = StockMonitorService(
            self.mock_data_manager,
            self.mock_notification_manager
        )
        
        # 创建测试股票配置
        self.test_stock_config = StockThresholdConfig(
            symbol="000001.SZ",
            name="平安银行",
            rsi_overbought=70.0,
            rsi_oversold=30.0,
            price_change_threshold=0.05,
            volume_threshold=2.0,
            macd_threshold=0.1,
            enabled=True
        )
        
        # 创建测试数据
        self.mock_realtime_data = {
            "000001.SZ": StockData(
                symbol="000001.SZ",
                name="平安银行",
                current_price=12.50,
                volume=1000000,
                high=12.80,
                low=12.20,
                change=0.25,
                change_percent=2.04,
                timestamp=datetime.now()
            )
        }
        
        # 创建历史数据
        dates = pd.date_range('2023-01-01', periods=60, freq='D')
        prices = 12.0 + np.cumsum(np.random.randn(60) * 0.1)
        volumes = np.random.randint(500000, 2000000, 60)
        
        self.mock_historical_data = pd.DataFrame({
            'date': dates,
            'open': prices + np.random.randn(60) * 0.05,
            'high': prices + np.abs(np.random.randn(60) * 0.1),
            'low': prices - np.abs(np.random.randn(60) * 0.1),
            'close': prices,
            'volume': volumes
        })
    
    @patch('src.core.config.config')
    async def test_monitor_cycle(self, mock_config):
        """测试监控循环"""
        # 配置模拟
        mock_config.monitoring.stock_thresholds = [self.test_stock_config]
        
        # 设置数据管理器返回值
        self.mock_data_manager.get_realtime_data = AsyncMock(return_value=self.mock_realtime_data)
        self.mock_data_manager.get_historical_data = AsyncMock(return_value=self.mock_historical_data)
        
        # 设置通知管理器
        self.mock_notification_manager.notify_stock_alert = AsyncMock(return_value=True)
        
        # 执行监控循环
        await self.monitor_service._monitor_cycle()
        
        # 验证数据获取被调用
        self.mock_data_manager.get_realtime_data.assert_called_once()
        self.mock_data_manager.get_historical_data.assert_called_once()
    
    def test_rsi_alerts(self):
        """测试RSI预警"""
        # 测试超买预警
        alerts = self.monitor_service._check_rsi_alerts(self.test_stock_config, 75.0)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].alert_type, AlertType.RSI_OVERBOUGHT)
        
        # 测试超卖预警
        alerts = self.monitor_service._check_rsi_alerts(self.test_stock_config, 25.0)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].alert_type, AlertType.RSI_OVERSOLD)
        
        # 测试正常范围
        alerts = self.monitor_service._check_rsi_alerts(self.test_stock_config, 50.0)
        self.assertEqual(len(alerts), 0)
    
    def test_price_alerts(self):
        """测试价格变动预警"""
        # 测试价格上涨预警
        alerts = self.monitor_service._check_price_alerts(self.test_stock_config, 0.06)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].alert_type, AlertType.PRICE_SURGE)
        
        # 测试价格下跌预警
        alerts = self.monitor_service._check_price_alerts(self.test_stock_config, -0.06)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].alert_type, AlertType.PRICE_DROP)
        
        # 测试正常范围
        alerts = self.monitor_service._check_price_alerts(self.test_stock_config, 0.02)
        self.assertEqual(len(alerts), 0)
    
    def test_volume_alerts(self):
        """测试成交量预警"""
        # 测试成交量异常
        alerts = self.monitor_service._check_volume_alerts(self.test_stock_config, 2.5)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].alert_type, AlertType.VOLUME_SPIKE)
        
        # 测试正常成交量
        alerts = self.monitor_service._check_volume_alerts(self.test_stock_config, 1.5)
        self.assertEqual(len(alerts), 0)
    
    def test_macd_alerts(self):
        """测试MACD预警"""
        # 测试MACD信号
        alerts = self.monitor_service._check_macd_alerts(self.test_stock_config, 0.15)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].alert_type, AlertType.MACD_SIGNAL)
        
        # 测试正常范围
        alerts = self.monitor_service._check_macd_alerts(self.test_stock_config, 0.05)
        self.assertEqual(len(alerts), 0)
    
    @patch('src.core.config.config')
    async def test_handle_alert_with_cooldown(self, mock_config):
        """测试预警处理和冷却时间"""
        mock_config.monitoring.notification_cooldown = 300
        mock_config.monitoring.enable_auto_notification = True
        
        # 创建测试预警
        alert = StockAlert(
            symbol="000001.SZ",
            name="平安银行",
            alert_type=AlertType.RSI_OVERBOUGHT,
            current_value=75.0,
            threshold=70.0,
            message="RSI超买预警",
            timestamp=datetime.now(),
            level=AlertLevel.WARNING
        )
        
        # 设置通知管理器
        self.mock_notification_manager.notify_market_alert = AsyncMock(return_value=True)
        
        # 第一次处理预警
        await self.monitor_service._handle_alert(alert)
        self.mock_notification_manager.notify_market_alert.assert_called_once()
        
        # 重置mock
        self.mock_notification_manager.reset_mock()
        
        # 立即再次处理相同预警（应该被冷却时间阻止）
        await self.monitor_service._handle_alert(alert)
        self.mock_notification_manager.notify_market_alert.assert_not_called()
    
    def test_dataframe_standardization(self):
        """测试数据框标准化"""
        # 创建Tushare格式的数据
        tushare_data = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20230101'],
            'open': [12.0],
            'high': [12.5],
            'low': [11.8],
            'close': [12.3],
            'vol': [1000000]
        })
        
        standardized = self.monitor_service._standardize_dataframe(tushare_data)
        
        # 验证列名转换
        self.assertIn('symbol', standardized.columns)
        self.assertIn('date', standardized.columns)
        self.assertIn('volume', standardized.columns)
        
        # 验证必要列存在
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            self.assertIn(col, standardized.columns)
    
    async def test_monitoring_status(self):
        """测试监控状态获取"""
        status = await self.monitor_service.get_monitoring_status()
        
        self.assertIn('is_running', status)
        self.assertIn('monitored_stocks', status)
        self.assertIn('polling_interval', status)
        self.assertIn('auto_notification', status)
        self.assertIn('last_check', status)
        
        self.assertIsInstance(status['is_running'], bool)
        self.assertIsInstance(status['monitored_stocks'], int)


class TestStockThresholdConfig(unittest.TestCase):
    """股票阈值配置测试"""
    
    def test_valid_config_creation(self):
        """测试有效配置创建"""
        config = StockThresholdConfig(
            symbol="000001.SZ",
            name="平安银行",
            rsi_overbought=75.0,
            rsi_oversold=25.0,
            price_change_threshold=0.05,
            volume_threshold=2.0,
            macd_threshold=0.1,
            enabled=True
        )
        
        self.assertEqual(config.symbol, "000001.SZ")
        self.assertEqual(config.name, "平安银行")
        self.assertEqual(config.rsi_overbought, 75.0)
        self.assertEqual(config.rsi_oversold, 25.0)
        self.assertTrue(config.enabled)
    
    def test_rsi_validation(self):
        """测试RSI阈值验证"""
        # 测试无效的RSI超买阈值
        with self.assertRaises(ValueError):
            StockThresholdConfig(
                symbol="000001.SZ",
                rsi_overbought=45.0  # 应该在50-100之间
            )
        
        # 测试无效的RSI超卖阈值
        with self.assertRaises(ValueError):
            StockThresholdConfig(
                symbol="000001.SZ",
                rsi_oversold=55.0  # 应该在0-50之间
            )
    
    def test_default_values(self):
        """测试默认值"""
        config = StockThresholdConfig(symbol="000001.SZ")
        
        self.assertEqual(config.rsi_overbought, 70.0)
        self.assertEqual(config.rsi_oversold, 30.0)
        self.assertEqual(config.price_change_threshold, 0.05)
        self.assertEqual(config.volume_threshold, 2.0)
        self.assertEqual(config.macd_threshold, 0.1)
        self.assertTrue(config.enabled)


class TestNotificationEnhancements(unittest.TestCase):
    """通知功能增强测试"""
    
    def setUp(self):
        self.notification_manager = NotificationManager()
    
    @patch('src.core.config.config')
    def test_stock_alert_notification(self, mock_config):
        """测试股票预警通知"""
        async def run_test():
            mock_config.notification.wecom_enabled = True
            mock_config.web.n8n.enabled = False
            
            # 模拟企微通知器
            mock_wecom = Mock()
            mock_wecom._build_stock_alert_message = Mock(return_value={'msgtype': 'text'})
            mock_wecom._send_message = AsyncMock(return_value=True)
            
            self.notification_manager.wecom_notifier = mock_wecom
            
            # 发送股票预警通知
            result = await self.notification_manager.notify_stock_alert(
                symbol="000001.SZ",
                name="平安银行",
                alert_type=StockAlertType.PRICE_BREAKOUT,
                current_value=12.50,
                threshold=12.00,
                message="价格突破阻力位",
                level=AlertLevel.WARNING
            )
            
            self.assertTrue(result)
            mock_wecom._build_stock_alert_message.assert_called_once()
            mock_wecom._send_message.assert_called_once()
        
        asyncio.run(run_test())


class TestIntegrationScenarios(unittest.TestCase):
    """集成测试场景"""
    
    def setUp(self):
        # 创建临时配置文件
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.yaml')
        
        # 创建测试配置
        test_config = {
            'system': {'name': 'Test System'},
            'monitoring': {
                'polling_interval': 30,
                'notification_cooldown': 300,
                'enable_auto_notification': True,
                'stock_thresholds': [
                    {
                        'symbol': '000001.SZ',
                        'name': '平安银行',
                        'rsi_overbought': 70.0,
                        'rsi_oversold': 30.0,
                        'price_change_threshold': 0.05,
                        'volume_threshold': 2.0,
                        'macd_threshold': 0.1,
                        'enabled': True
                    }
                ]
            },
            'notification': {
                'wecom_enabled': True,
                'wecom_webhook_url': 'https://test.webhook.url'
            },
            'web': {
                'n8n': {
                    'enabled': True,
                    'webhook_url': 'https://test.n8n.webhook.url'
                }
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('src.core.config.CONFIG_FILE')
    def test_full_monitoring_workflow(self, mock_config_file):
        """测试完整的监控工作流"""
        mock_config_file.return_value = self.config_file
        
        # 这里可以添加完整的工作流测试
        # 包括配置加载、监控启动、预警触发、通知发送等
        pass


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)