#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成测试

测试整个系统的端到端功能
"""

import unittest
import asyncio
import tempfile
import os
import yaml
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from src.core.engine import TradingEngine
from src.core.config import Config
from src.models.models import (
    TradeSignal, MarketAlert, StockData, 
    TradeAction, AlertLevel, OrderStatus
)
from src.web.config_server import ConfigServer


class TestIntegration(unittest.TestCase):
    """集成测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # 创建临时目录和配置文件
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.yaml')
        self.env_file = os.path.join(self.temp_dir, '.env')
        
        # 创建完整的测试配置
        self.test_config_data = {
            'system': {
                'name': 'Integration Test System',
                'version': '1.0.0',
                'timezone': 'Asia/Shanghai'
            },
            'data_sources': {
                'primary': 'tushare',
                'backup': 'akshare',
                'realtime': 'sina'
            },
            'monitoring': {
                'stocks': ['000001.SZ', '600519.SH'],
                'volatility_threshold': 0.03,
                'check_interval': 5  # 短间隔用于测试
            },
            'strategy': {
                'name': 'pressure_support_strategy',
                'parameters': {
                    'analysis_period': 6,
                    'pressure_factor': 1.05,
                    'support_factor': 0.95,
                    'volume_threshold': 1.5
                }
            },
            'risk_management': {
                'max_position_size': 10000,
                'max_positions': 5,
                'stop_loss': 0.05,
                'take_profit': 0.10,
                'risk_tolerance': 0.02
            },
            'notification': {
                'wecom': {
                    'enabled': True,
                    'mention_all': False
                }
            },
            'logging': {
                'level': 'INFO',
                'rotation': '1 day',
                'retention': '30 days'
            },
            'database': {
                'url': f'sqlite:///{self.temp_dir}/test_trading.db',
                'echo': False
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.test_config_data, f)
        
        # 创建环境变量文件
        with open(self.env_file, 'w', encoding='utf-8') as f:
            f.write('TUSHARE_TOKEN=test_token\n')
            f.write('WECOM_WEBHOOK_URL=https://test.webhook.url\n')
            f.write(f'DATABASE_URL=sqlite:///{self.temp_dir}/test_trading.db\n')
    
    def tearDown(self):
        """测试后清理"""
        self.loop.close()
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_config_loading_integration(self):
        """测试配置加载集成"""
        with patch.dict(os.environ, {'DATABASE_URL': f'sqlite:///{self.temp_dir}/test.db'}):
            config = Config(self.config_file)
            
            # 验证配置加载
            self.assertEqual(config.system['name'], 'Integration Test System')
            self.assertEqual(config.monitoring.volatility_threshold, 0.03)
            self.assertEqual(len(config.monitoring.stocks), 2)
            self.assertEqual(config.risk.max_position_size, 10000)
    
    @patch('src.data.data_provider.TushareProvider')
    @patch('src.data.data_provider.AkshareProvider')
    @patch('src.data.data_provider.SinaProvider')
    def test_data_provider_integration(self, mock_sina, mock_akshare, mock_tushare):
        """测试数据提供者集成"""
        # 模拟数据提供者
        mock_tushare_instance = AsyncMock()
        mock_tushare_instance.initialize.return_value = True
        mock_tushare_instance.is_available = True
        mock_tushare_instance.get_realtime_data.return_value = {
            '000001.SZ': StockData(
                symbol='000001.SZ',
                name='平安银行',
                current_price=12.50,
                change=0.30,
                change_percent=2.46,
                volume=1500000,
                timestamp=datetime.now()
            )
        }
        mock_tushare.return_value = mock_tushare_instance
        
        mock_akshare_instance = AsyncMock()
        mock_akshare_instance.initialize.return_value = True
        mock_akshare.return_value = mock_akshare_instance
        
        mock_sina_instance = AsyncMock()
        mock_sina_instance.initialize.return_value = True
        mock_sina.return_value = mock_sina_instance
        
        config = Config(self.config_file)
        
        async def test_data_integration():
            from src.data.data_provider import DataManager
            
            data_manager = DataManager(config)
            await data_manager.initialize()
            
            # 测试数据获取
            data = await data_manager.get_realtime_data(['000001.SZ'])
            
            self.assertIn('000001.SZ', data)
            self.assertEqual(data['000001.SZ'].current_price, 12.50)
        
        self.loop.run_until_complete(test_data_integration())
    
    @patch('src.notification.wecom_notifier.aiohttp.ClientSession')
    def test_notification_integration(self, mock_session_class):
        """测试通知系统集成"""
        # 模拟成功的HTTP响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {'errcode': 0, 'errmsg': 'ok'}
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None
        
        mock_session = AsyncMock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        config = Config(self.config_file)
        
        async def test_notification_integration():
            from src.notification.wecom_notifier import NotificationManager
            
            notification_manager = NotificationManager()
            success = await notification_manager.initialize()
            
            self.assertTrue(success)
            
            # 测试发送交易信号
            signal = TradeSignal(
                symbol='000001.SZ',
                action=TradeAction.BUY,
                price=12.50,
                quantity=1000,
                confidence=0.85,
                reason='集成测试',
                timestamp=datetime.now(),
                strategy='test'
            )
            
            result = await notification_manager.notify_trade_signal(signal)
            self.assertTrue(result)
            
            await notification_manager.close()
        
        self.loop.run_until_complete(test_notification_integration())
    
    @patch('src.data.data_provider.TushareProvider')
    @patch('src.data.data_provider.AkshareProvider')
    @patch('src.data.data_provider.SinaProvider')
    @patch('src.notification.wecom_notifier.aiohttp.ClientSession')
    def test_trading_engine_integration(self, mock_session_class, mock_sina, mock_akshare, mock_tushare):
        """测试交易引擎集成"""
        # 模拟数据提供者
        self._setup_mock_data_providers(mock_tushare, mock_akshare, mock_sina)
        
        # 模拟通知系统
        self._setup_mock_notification(mock_session_class)
        
        config = Config(self.config_file)
        
        async def test_engine_integration():
            engine = TradingEngine(config)
            
            # 初始化引擎
            await engine.initialize()
            
            # 验证组件初始化
            self.assertIsNotNone(engine.data_manager)
            self.assertIsNotNone(engine.monitor)
            self.assertIsNotNone(engine.strategy)
            self.assertIsNotNone(engine.risk_manager)
            self.assertIsNotNone(engine.trade_executor)
            self.assertIsNotNone(engine.notification_manager)
            
            # 模拟短暂运行
            engine.is_running = True
            engine.start_time = datetime.now()
            
            # 测试信号生成
            await engine._generate_trade_signals()
            
            # 验证统计信息
            self.assertGreaterEqual(engine.stats['signals_generated'], 0)
            
            # 停止引擎
            await engine.stop()
            
            self.assertFalse(engine.is_running)
        
        self.loop.run_until_complete(test_engine_integration())
    
    def test_web_interface_integration(self):
        """测试Web界面集成"""
        config_server = ConfigServer(host='127.0.0.1', port=0)
        config_server.config_manager.config_file = Path(self.config_file)
        config_server.config_manager.env_file = Path(self.env_file)
        
        # 启动服务器
        success = config_server.start()
        self.assertTrue(success)
        
        try:
            with config_server.app.test_client() as client:
                # 测试主页
                response = client.get('/')
                self.assertEqual(response.status_code, 200)
                
                # 测试配置API
                response = client.get('/api/config')
                self.assertEqual(response.status_code, 200)
                
                data = response.get_json()
                self.assertIn('config', data)
                self.assertEqual(data['config']['system']['name'], 'Integration Test System')
                
                # 测试配置保存
                updated_config = {
                    'config': data['config'],
                    'env': data['env']
                }
                updated_config['config']['system']['name'] = 'Updated System'
                
                response = client.post('/api/config',
                                     json=updated_config,
                                     content_type='application/json')
                
                self.assertEqual(response.status_code, 200)
                result = response.get_json()
                self.assertTrue(result['success'])
        
        finally:
            config_server.stop()
    
    @patch('src.data.data_provider.TushareProvider')
    @patch('src.data.data_provider.AkshareProvider')
    @patch('src.data.data_provider.SinaProvider')
    def test_monitoring_integration(self, mock_sina, mock_akshare, mock_tushare):
        """测试监控系统集成"""
        # 模拟数据提供者
        self._setup_mock_data_providers(mock_tushare, mock_akshare, mock_sina)
        
        config = Config(self.config_file)
        
        async def test_monitoring_integration():
            from src.data.data_provider import DataManager
            from src.core.monitor import StockMonitor
            
            data_manager = DataManager(config)
            await data_manager.initialize()
            
            monitor = StockMonitor(config, data_manager)
            
            # 添加预警回调
            alerts_received = []
            
            def alert_callback(alert):
                alerts_received.append(alert)
            
            monitor.add_alert_callback(alert_callback)
            
            # 启动监控
            await monitor.start_monitoring()
            
            # 等待一个检查周期
            await asyncio.sleep(0.1)
            
            # 停止监控
            await monitor.stop_monitoring()
            
            # 验证监控状态
            summary = monitor.get_monitoring_summary()
            self.assertEqual(summary['monitored_stocks'], 2)
            
            await data_manager.close()
        
        self.loop.run_until_complete(test_monitoring_integration())
    
    @patch('src.data.data_provider.TushareProvider')
    @patch('src.data.data_provider.AkshareProvider')
    @patch('src.data.data_provider.SinaProvider')
    def test_strategy_integration(self, mock_sina, mock_akshare, mock_tushare):
        """测试策略系统集成"""
        # 模拟数据提供者
        self._setup_mock_data_providers(mock_tushare, mock_akshare, mock_sina)
        
        config = Config(self.config_file)
        
        async def test_strategy_integration():
            from src.data.data_provider import DataManager
            from src.strategy.pressure_support_strategy import PressureSupportStrategy
            
            data_manager = DataManager(config)
            await data_manager.initialize()
            
            strategy = PressureSupportStrategy(data_manager)
            
            # 测试市场分析
            analysis = await strategy.analyze_market('000001.SZ')
            
            if analysis:  # 如果有足够的数据
                self.assertEqual(analysis.symbol, '000001.SZ')
                self.assertGreater(analysis.current_price, 0)
            
            # 测试信号生成
            signal = await strategy.generate_signal('000001.SZ')
            
            if signal:  # 如果生成了信号
                self.assertEqual(signal.symbol, '000001.SZ')
                self.assertIn(signal.action, [TradeAction.BUY, TradeAction.SELL, TradeAction.HOLD])
            
            await data_manager.close()
        
        self.loop.run_until_complete(test_strategy_integration())
    
    def test_error_handling_integration(self):
        """测试错误处理集成"""
        # 创建无效配置
        invalid_config_file = os.path.join(self.temp_dir, 'invalid_config.yaml')
        with open(invalid_config_file, 'w') as f:
            f.write('invalid: yaml: content: [')
        
        # 测试配置加载错误
        with self.assertRaises(ValueError):
            Config(invalid_config_file)
        
        # 测试缺少配置文件
        with self.assertRaises(FileNotFoundError):
            Config('nonexistent_config.yaml')
    
    def test_performance_integration(self):
        """测试性能集成"""
        config = Config(self.config_file)
        
        # 测试配置加载性能
        start_time = time.time()
        for _ in range(10):
            Config(self.config_file)
        end_time = time.time()
        
        # 配置加载应该很快
        self.assertLess(end_time - start_time, 1.0)
    
    def test_concurrent_operations_integration(self):
        """测试并发操作集成"""
        config = Config(self.config_file)
        
        async def test_concurrent():
            # 模拟并发配置访问
            tasks = []
            for _ in range(5):
                task = asyncio.create_task(self._async_config_operation(config))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 所有操作都应该成功
            for result in results:
                self.assertNotIsInstance(result, Exception)
        
        self.loop.run_until_complete(test_concurrent())
    
    async def _async_config_operation(self, config):
        """异步配置操作"""
        # 模拟一些配置访问操作
        await asyncio.sleep(0.01)
        return config.monitoring.volatility_threshold
    
    def _setup_mock_data_providers(self, mock_tushare, mock_akshare, mock_sina):
        """设置模拟数据提供者"""
        # Tushare模拟
        mock_tushare_instance = AsyncMock()
        mock_tushare_instance.initialize.return_value = True
        mock_tushare_instance.is_available = True
        mock_tushare_instance.get_realtime_data.return_value = {
            '000001.SZ': StockData(
                symbol='000001.SZ',
                name='平安银行',
                current_price=12.50,
                change=0.30,
                change_percent=2.46,
                volume=1500000,
                timestamp=datetime.now()
            ),
            '600519.SH': StockData(
                symbol='600519.SH',
                name='贵州茅台',
                current_price=1680.50,
                change=-25.30,
                change_percent=-1.48,
                volume=800000,
                timestamp=datetime.now()
            )
        }
        mock_tushare_instance.get_historical_data.return_value = self._create_mock_historical_data()
        mock_tushare.return_value = mock_tushare_instance
        
        # Akshare模拟
        mock_akshare_instance = AsyncMock()
        mock_akshare_instance.initialize.return_value = True
        mock_akshare_instance.is_available = True
        mock_akshare.return_value = mock_akshare_instance
        
        # Sina模拟
        mock_sina_instance = AsyncMock()
        mock_sina_instance.initialize.return_value = True
        mock_sina_instance.is_available = True
        mock_sina.return_value = mock_sina_instance
    
    def _setup_mock_notification(self, mock_session_class):
        """设置模拟通知系统"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {'errcode': 0, 'errmsg': 'ok'}
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None
        
        mock_session = AsyncMock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
    
    def _create_mock_historical_data(self):
        """创建模拟历史数据"""
        import pandas as pd
        import numpy as np
        
        dates = pd.date_range(start='2024-01-01', end='2024-06-30', freq='D')
        np.random.seed(42)
        
        prices = []
        base_price = 12.0
        for _ in range(len(dates)):
            change = np.random.normal(0, 0.02)
            base_price *= (1 + change)
            prices.append(max(base_price, 0.1))
        
        return pd.DataFrame({
            'date': dates,
            'open': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': np.random.randint(500000, 2000000, len(dates))
        })
    
    def test_full_system_integration(self):
        """测试完整系统集成"""
        """这是一个综合性的集成测试，验证整个系统的协同工作"""
        
        # 这个测试需要更多的模拟设置，暂时跳过
        self.skipTest("完整系统集成测试需要更复杂的环境设置")
        
        # 在实际环境中，这里会测试：
        # 1. 系统启动
        # 2. 数据获取
        # 3. 策略分析
        # 4. 信号生成
        # 5. 风险检查
        # 6. 交易执行
        # 7. 通知发送
        # 8. 监控预警
        # 9. Web界面交互
        # 10. 系统关闭


if __name__ == '__main__':
    unittest.main()