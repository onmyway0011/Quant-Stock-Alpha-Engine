#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web界面测试

测试配置管理Web界面功能
"""

import unittest
import tempfile
import os
import yaml
import json
from pathlib import Path
from unittest.mock import patch
import sys
import importlib

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestWebInterface(unittest.TestCase):
    """Web界面测试类"""

    @classmethod
    def setUpClass(cls):
        """Patch config path and load modules"""
        cls.temp_dir = tempfile.mkdtemp()
        cls.config_file = os.path.join(cls.temp_dir, 'config.yaml')

        cls.test_config_data = {
            'system': {
                'name': 'Test Trading System',
                'version': '1.0.0',
                'timezone': 'Asia/Shanghai'
            },
            'data': {
                'sources': {
                    'primary': 'tushare',
                    'backup': 'baostock',
                    'realtime': 'akshare'
                },
                'tushare_token': 'test_token'
            },
            'monitoring': {
                'stocks': ['000001.SZ', '600519.SH'],
                'volatility_threshold': 0.03,
                'check_interval': 60
            },
            'risk_management': {
                'max_position_size': 10000,
                'stop_loss': 0.05,
                'trailing_stop': {
                    'enabled': True,
                    'percentage': 0.02
                }
            },
            'notification': {
                'wecom': {
                    'webhook_url': ''
                }
            },
            'web': {
                'host': '127.0.0.1',
                'port': 8080
            },
            'strategies': {
                'pressure_support_strategy': {
                    'enabled': True,
                    'params': {
                        'short_window': 10,
                        'long_window': 50,
                        'volume_multiple': 2.0
                    }
                }
            }
        }
        with open(cls.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(cls.test_config_data, f)

        # Patch load_config to use our test config file
        cls.load_config_patch = patch('src.core.config.load_config')
        cls.mock_load_config = cls.load_config_patch.start()
        
        # Mock load_config to always load from our test file
        def mock_load_config_func(config_file=None):
            from src.core.config import Config
            with open(cls.config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return Config(**data)
        
        cls.mock_load_config.side_effect = mock_load_config_func
        
        # Also patch CONFIG_FILE for the ConfigServer
        cls.config_file_patch = patch('src.web.config_server.CONFIG_FILE', cls.config_file)
        cls.config_file_patch.start()
        
        from src.web.config_server import ConfigServer
        
        cls.server = ConfigServer()
        cls.client = cls.server.app.test_client()

    @classmethod
    def tearDownClass(cls):
        """Stop patch and clean up"""
        # Stop patches started in setUpClass
        try:
            cls.load_config_patch.stop()
        except Exception:
            pass
        try:
            cls.config_file_patch.stop()
        except Exception:
            pass
        import shutil
        shutil.rmtree(cls.temp_dir)
    
    def setUp(self):
        """Reset config file for each test"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.test_config_data, f)

    def test_config_page(self):
        """测试配置页面"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Quant Stock Alpha Engine', response.data)

    def test_api_get_config(self):
        """测试获取配置API"""
        response = self.client.get('/api/config')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['system']['name'], 'Test Trading System')
        self.assertEqual(data['data']['tushare_token'], 'test_token')

    def test_api_save_config(self):
        """测试保存配置API"""
        response = self.client.get('/api/config')
        self.assertEqual(response.status_code, 200)
        new_config = json.loads(response.data)

        new_config['system']['name'] = 'API Modified System'
        
        response = self.client.post('/api/config', json=new_config)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], '配置已保存，将在服务重启后生效。')
        
        with open(self.config_file, 'r') as f:
            saved_config = yaml.safe_load(f)
        self.assertEqual(saved_config['system']['name'], 'API Modified System')

if __name__ == '__main__':
    unittest.main()