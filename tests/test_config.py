#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置模块测试

测试新的Pydantic配置加载、验证和访问功能
"""

import unittest
import tempfile
import os
import yaml
from pathlib import Path
from unittest.mock import patch
import sys
import importlib

from pydantic import ValidationError

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestPydanticConfig(unittest.TestCase):
    """测试基于Pydantic的配置模块"""

    @classmethod
    def setUpClass(cls):
        """在所有测试开始前，创建临时配置文件并加载配置模块"""
        cls.temp_dir = tempfile.mkdtemp()
        cls.config_file = os.path.join(cls.temp_dir, 'config.yaml')

        # 定义一个完整的测试配置
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

        # 使用补丁来重定向配置文件的路径
        cls.config_path_patch = patch('src.core.config.CONFIG_FILE', cls.config_file)
        cls.config_path_patch.start()

        # 重新加载配置模块以应用补丁
        from src.core import config as config_module
        importlib.reload(config_module)
        cls.config = config_module.config

    @classmethod
    def tearDownClass(cls):
        """在所有测试结束后，停止补丁并清理临时文件"""
        cls.config_path_patch.stop()
        import shutil
        shutil.rmtree(cls.temp_dir)

    def test_config_loading_and_access(self):
        """测试配置是否正确加载以及是否可以通过属性访问"""
        self.assertEqual(self.config.system.name, 'Test Trading System')
        self.assertEqual(self.config.monitoring.volatility_threshold, 0.03)
        self.assertIn('000001.SZ', self.config.monitoring.stocks)
        self.assertEqual(self.config.strategies.pressure_support_strategy.params.long_window, 50)

    def test_pydantic_validation(self):
        """测试Pydantic的验证功能"""
        invalid_config_data = self.test_config_data.copy()
        invalid_config_data['monitoring']['check_interval'] = -10  # 无效值

        invalid_config_file = os.path.join(self.temp_dir, 'invalid_config.yaml')
        with open(invalid_config_file, 'w', encoding='utf-8') as f:
            yaml.dump(invalid_config_data, f)

        # 验证加载无效配置时是否会引发ValidationError
        with patch('src.core.config.CONFIG_FILE', invalid_config_file):
            with self.assertRaises(ValidationError):
                from src.core import config as config_module
                importlib.reload(config_module)

    def test_default_values(self):
        """测试是否正确应用了默认值"""
        minimal_config_data = {
            'system': {'name': 'Minimal System'}
        }
        minimal_config_file = os.path.join(self.temp_dir, 'minimal_config.yaml')
        with open(minimal_config_file, 'w', encoding='utf-8') as f:
            yaml.dump(minimal_config_data, f)

        with patch('src.core.config.CONFIG_FILE', minimal_config_file):
            from src.core import config as config_module
            importlib.reload(config_module)
            config = config_module.config
            
            # 验证默认值
            self.assertEqual(config.web.port, 8080)
            self.assertEqual(config.risk_management.stop_loss, 0.1)
            self.assertFalse(config.notification.wecom.webhook_url) # pydantic default is empty string, which is False

    def test_file_not_found(self):
        """测试当配置文件不存在时是否会引发FileNotFoundError"""
        with patch('src.core.config.CONFIG_FILE', 'non_existent_file.yaml'):
            with self.assertRaises(FileNotFoundError):
                from src.core import config as config_module
                importlib.reload(config_module)

if __name__ == '__main__':
    unittest.main()