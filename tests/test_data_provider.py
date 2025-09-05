#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据提供者模块测试

测试数据获取、处理和管理功能
"""

import unittest
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from src.data.data_provider import (
    DataProvider, DataManager, TushareProvider,
    AkshareProvider, SinaProvider
)
from src.models.models import StockData
from src.core.config import Config


class TestDataProvider(unittest.TestCase):
    """数据提供者测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # 模拟配置
        self.mock_config = MagicMock()
        self.mock_config.data_sources = {
            'primary': 'tushare',
            'backup': 'akshare',
            'realtime': 'sina'
        }
        self.mock_config.get_env.return_value = 'test_token'
    
    def tearDown(self):
        """测试后清理"""
        self.loop.close()
    
    def test_tushare_provider_initialization(self):
        """测试Tushare提供者初始化"""
        provider = TushareProvider('test_token')
        
        self.assertEqual(provider.name, 'Tushare')
        self.assertEqual(provider.token, 'test_token')
        self.assertFalse(provider.is_available)
    
    @patch('src.data.data_provider.ts')
    def test_tushare_provider_initialize_success(self, mock_ts):
        """测试Tushare提供者成功初始化"""
        # 模拟tushare模块
        mock_pro = MagicMock()
        mock_pro.stock_basic.return_value = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'symbol': ['000001'],
            'name': ['平安银行']
        })
        mock_ts.pro_api.return_value = mock_pro
        
        provider = TushareProvider('test_token')
        
        async def test_init():
            result = await provider.initialize()
            self.assertTrue(result)
            self.assertTrue(provider.is_available)
        
        self.loop.run_until_complete(test_init())
    
    @patch('src.data.data_provider.ts', None)
    def test_tushare_provider_not_installed(self):
        """测试Tushare未安装情况"""
        provider = TushareProvider('test_token')
        
        async def test_init():
            result = await provider.initialize()
            self.assertFalse(result)
            self.assertFalse(provider.is_available)
        
        self.loop.run_until_complete(test_init())
    
    def test_akshare_provider_initialization(self):
        """测试Akshare提供者初始化"""
        provider = AkshareProvider()
        
        self.assertEqual(provider.name, 'Akshare')
        self.assertFalse(provider.is_available)
    
    @patch('src.data.data_provider.ak')
    def test_akshare_provider_initialize_success(self, mock_ak):
        """测试Akshare提供者成功初始化"""
        # 模拟akshare模块
        mock_ak.stock_zh_a_spot_em.return_value = pd.DataFrame({
            '代码': ['000001'],
            '名称': ['平安银行'],
            '最新价': [12.50]
        })
        
        provider = AkshareProvider()
        provider.is_available = True
        provider.ak = mock_ak  # 添加这行以正确设置mock对象
        
        async def test_init():
            result = await provider.initialize()
            self.assertTrue(result)
            self.assertTrue(provider.is_available)
        
        self.loop.run_until_complete(test_init())
    
    def test_sina_provider_initialization(self):
        """测试新浪提供者初始化"""
        provider = SinaProvider()
        
        self.assertEqual(provider.name, 'Sina')
        self.assertFalse(provider.is_available)
    
    @patch('aiohttp.ClientSession')
    def test_sina_provider_initialize_success(self, mock_session_class):
        """测试新浪提供者成功初始化"""
        # 模拟aiohttp响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None
        
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        provider = SinaProvider()
        
        async def test_init():
            result = await provider.initialize()
            self.assertTrue(result)
            self.assertTrue(provider.is_available)
        
        self.loop.run_until_complete(test_init())
    
    @patch('src.data.data_provider.ts')
    def test_tushare_get_realtime_data(self, mock_ts):
        """测试Tushare获取实时数据"""
        # 模拟tushare数据
        mock_pro = MagicMock()
        mock_pro.daily.return_value = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'open': [12.00],
            'high': [12.80],
            'low': [11.90],
            'close': [12.50],
            'pre_close': [12.00],
            'vol': [1000000]
        })
        mock_ts.pro_api.return_value = mock_pro
        
        provider = TushareProvider('test_token')
        provider.pro = mock_pro
        provider.is_available = True
        
        async def test_get_data():
            with patch.object(provider, '_get_stock_name', return_value='平安银行'):
                data = await provider.get_realtime_data(['000001.SZ'])
                
                self.assertIn('000001.SZ', data)
                stock_data = data['000001.SZ']
                self.assertIsInstance(stock_data, StockData)
                self.assertEqual(stock_data.symbol, '000001.SZ')
                self.assertEqual(stock_data.current_price, 12.50)
        
        self.loop.run_until_complete(test_get_data())
    
    @patch('src.data.data_provider.ak')
    def test_akshare_get_realtime_data(self, mock_ak):
        """测试Akshare获取实时数据"""
        # 模拟akshare数据
        mock_ak.stock_zh_a_spot_em.return_value = pd.DataFrame({
            '代码': ['000001'],  # 确保代码匹配
            '名称': ['平安银行'],
            '最新价': [12.50],
            '涨跌额': [0.50],
            '涨跌幅': [4.17],
            '成交量': [1000000],
            '最高': [12.80],
            '最低': [11.90],
            '今开': [12.00]
        })
        
        provider = AkshareProvider()
        provider.is_available = True
        provider.ak = mock_ak  # 添加这行
        
        async def test_get_data():
            data = await provider.get_realtime_data(['000001.SZ'])
            
            self.assertIn('000001.SZ', data)
            stock_data = data['000001.SZ']
            self.assertIsInstance(stock_data, StockData)
            self.assertEqual(stock_data.symbol, '000001.SZ')
            self.assertEqual(stock_data.current_price, 12.50)
        
        self.loop.run_until_complete(test_get_data())
    
    @patch('aiohttp.ClientSession')
    def test_sina_get_realtime_data(self, mock_session_class):
        """测试新浪获取实时数据"""
        # 模拟新浪数据响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = 'var hq_str_sh000001="平安银行,12.00,12.00,12.50,12.80,11.90,0.00,0.00,1000000,12500000.00,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2024-01-01,15:00:00,00";'
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None
        
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        provider = SinaProvider()
        provider.session = mock_session
        provider.is_available = True
        
        async def test_get_data():
            data = await provider.get_realtime_data(['000001.SH'])
            
            self.assertIn('000001.SH', data)
            stock_data = data['000001.SH']
            self.assertIsInstance(stock_data, StockData)
            self.assertEqual(stock_data.symbol, '000001.SH')
        
        self.loop.run_until_complete(test_get_data())
    
    @patch('src.data.data_provider.ts')
    def test_tushare_get_historical_data(self, mock_ts):
        """测试Tushare获取历史数据"""
        # 模拟历史数据
        mock_pro = MagicMock()
        mock_pro.daily.return_value = pd.DataFrame({
            'ts_code': ['000001.SZ'] * 5,
            'trade_date': ['20240101', '20240102', '20240103', '20240104', '20240105'],
            'open': [12.00, 12.50, 12.30, 12.80, 12.60],
            'high': [12.80, 12.90, 12.70, 13.00, 12.90],
            'low': [11.90, 12.20, 12.10, 12.50, 12.40],
            'close': [12.50, 12.30, 12.80, 12.60, 12.70],
            'vol': [1000000, 1200000, 900000, 1500000, 1100000]
        })
        mock_ts.pro_api.return_value = mock_pro
        
        provider = TushareProvider('test_token')
        provider.pro = mock_pro
        provider.is_available = True
        
        async def test_get_historical():
            df = await provider.get_historical_data('000001.SZ', '2024-01-01', '2024-01-05')
            
            self.assertFalse(df.empty)
            self.assertEqual(len(df), 5)
            self.assertIn('trade_date', df.columns)
        
        self.loop.run_until_complete(test_get_historical())
    
    def test_data_manager_initialization(self):
        """测试数据管理器初始化"""
        manager = DataManager(self.mock_config)
        
        self.assertEqual(manager.config, self.mock_config)
        self.assertEqual(manager.providers, {})
        self.assertIsNone(manager.primary_provider)
    
    @patch('src.data.data_provider.TushareProvider')
    @patch('src.data.data_provider.AkshareProvider')
    @patch('src.data.data_provider.SinaProvider')
    def test_data_manager_initialize(self, mock_sina, mock_akshare, mock_tushare):
        """测试数据管理器初始化"""
        # 模拟提供者
        mock_tushare_instance = AsyncMock()
        mock_tushare_instance.initialize.return_value = True
        mock_tushare.return_value = mock_tushare_instance
        
        mock_akshare_instance = AsyncMock()
        mock_akshare_instance.initialize.return_value = True
        mock_akshare.return_value = mock_akshare_instance
        
        mock_sina_instance = AsyncMock()
        mock_sina_instance.initialize.return_value = True
        mock_sina.return_value = mock_sina_instance
        
        manager = DataManager(self.mock_config)
        
        async def test_init():
            await manager.initialize()
            
            self.assertIn('tushare', manager.providers)
            self.assertIn('akshare', manager.providers)
            self.assertIn('sina', manager.providers)
        
        self.loop.run_until_complete(test_init())
    
    def test_data_manager_get_realtime_data_fallback(self):
        """测试数据管理器获取实时数据的降级机制"""
        manager = DataManager(self.mock_config)
        
        # 模拟提供者
        primary_provider = AsyncMock()
        primary_provider.is_available = False
        
        backup_provider = AsyncMock()
        backup_provider.is_available = True
        backup_provider.get_realtime_data.return_value = {
            '000001.SZ': StockData(
                symbol='000001.SZ',
                name='平安银行',
                current_price=12.50,
                change=0.50,
                change_percent=4.17,
                volume=1000000,
                timestamp=datetime.now()
            )
        }
        
        manager.primary_provider = primary_provider
        manager.backup_provider = backup_provider
        
        async def test_fallback():
            data = await manager.get_realtime_data(['000001.SZ'])
            
            self.assertIn('000001.SZ', data)
            backup_provider.get_realtime_data.assert_called_once()
        
        self.loop.run_until_complete(test_fallback())
    
    def test_symbol_conversion(self):
        """测试股票代码转换"""
        tushare_provider = TushareProvider('test_token')
        sina_provider = SinaProvider()
        
        # 测试Tushare格式转换
        self.assertEqual(tushare_provider._convert_symbol_to_ts('000001.SZ'), '000001.SZ')
        self.assertEqual(tushare_provider._convert_symbol_to_ts('600000.SH'), '600000.SH')
        
        # 测试新浪格式转换
        self.assertEqual(sina_provider._convert_symbol_to_sina('000001.SZ'), 'sz000001')
        self.assertEqual(sina_provider._convert_symbol_to_sina('600000.SH'), 'sh600000')
    
    def test_error_handling(self):
        """测试错误处理"""
        provider = TushareProvider('invalid_token')
        
        async def test_error():
            # 测试初始化失败
            with patch('src.data.data_provider.ts') as mock_ts:
                mock_ts.pro_api.side_effect = Exception('API Error')
                result = await provider.initialize()
                self.assertFalse(result)
            
            # 测试数据获取失败
            provider.is_available = True
            provider.pro = MagicMock()
            provider.pro.daily.side_effect = Exception('Data Error')
            
            data = await provider.get_realtime_data(['000001.SZ'])
            self.assertEqual(data, {})
        
        self.loop.run_until_complete(test_error())
    
    def test_data_validation(self):
        """测试数据验证"""
        # 测试StockData对象创建
        stock_data = StockData(
            symbol='000001.SZ',
            name='平安银行',
            current_price=12.50,
            change=0.50,
            change_percent=4.17,
            volume=1000000,
            timestamp=datetime.now()
        )
        
        self.assertEqual(stock_data.symbol, '000001.SZ')
        self.assertEqual(stock_data.current_price, 12.50)
        self.assertIsInstance(stock_data.timestamp, datetime)
    
    def test_concurrent_data_requests(self):
        """测试并发数据请求"""
        manager = DataManager(self.mock_config)
        
        # 模拟提供者
        provider = AsyncMock()
        provider.is_available = True
        provider.get_realtime_data.return_value = {
            '000001.SZ': StockData(
                symbol='000001.SZ',
                name='平安银行',
                current_price=12.50,
                change=0.50,
                change_percent=4.17,
                volume=1000000,
                timestamp=datetime.now()
            )
        }
        
        manager.realtime_provider = provider
        
        async def test_concurrent():
            # 并发请求
            tasks = [
                manager.get_realtime_data(['000001.SZ']),
                manager.get_realtime_data(['000002.SZ']),
                manager.get_realtime_data(['600000.SH'])
            ]
            
            results = await asyncio.gather(*tasks)
            
            self.assertEqual(len(results), 3)
            for result in results:
                self.assertIsInstance(result, dict)
        
        self.loop.run_until_complete(test_concurrent())


if __name__ == '__main__':
    unittest.main()