#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置模块测试

测试配置加载、验证和管理功能
"""

import unittest
import tempfile
import os
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import Config
from src.web.config_server import ConfigManager


class TestConfig(unittest.TestCase):
    """配置模块测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.yaml')
        self.env_file = os.path.join(self.temp_dir, '.env')
        
        # 创建测试配置文件
        self.test_config_data = {
            'system': {
                'name': 'Test Trading System',
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
                'check_interval': 60
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
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.test_config_data, f)
        
        # 创建测试环境变量文件
        with open(self.env_file, 'w', encoding='utf-8') as f:
            f.write('TUSHARE_TOKEN=test_token\n')
            f.write('WECOM_WEBHOOK_URL=https://test.webhook.url\n')
            f.write('DATABASE_URL=sqlite:///test.db\n')
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_config_loading(self):
        """测试配置加载"""
        with patch.object(Config, '__init__', lambda x, config_file=None: None):
            config = Config()
            config.config_file = Path(self.config_file)
            config._load_config()
            
            # 验证配置加载
            self.assertEqual(config._config['system']['name'], 'Test Trading System')
            self.assertEqual(config._config['monitoring']['volatility_threshold'], 0.03)
            self.assertIn('000001.SZ', config._config['monitoring']['stocks'])
    
    def test_config_validation(self):
        """测试配置验证"""
        config_manager = ConfigManager()
        
        # 测试有效配置
        errors = config_manager.validate_config(self.test_config_data)
        self.assertEqual(len(errors), 0, f"有效配置不应有错误: {errors}")
        
        # 测试无效配置
        invalid_config = self.test_config_data.copy()
        invalid_config['risk_management']['stop_loss'] = -0.1  # 无效值
        
        errors = config_manager.validate_config(invalid_config)
        self.assertGreater(len(errors), 0, "无效配置应该有错误")
    
    def test_config_schema(self):
        """测试配置模式"""
        config_manager = ConfigManager()
        schema = config_manager.get_config_schema()
        
        # 验证模式结构
        self.assertIn('system', schema)
        self.assertIn('monitoring', schema)
        self.assertIn('strategy', schema)
        self.assertIn('risk_management', schema)
        
        # 验证字段类型定义
        self.assertEqual(schema['monitoring']['volatility_threshold']['type'], 'number')
        self.assertEqual(schema['strategy']['parameters']['analysis_period']['type'], 'number')
    
    def test_env_config_loading(self):
        """测试环境变量配置加载"""
        config_manager = ConfigManager()
        config_manager.env_file = Path(self.env_file)
        config_manager.env_example_file = Path(self.env_file)  # 使用同一个文件作为示例
        
        with patch.dict(os.environ, {
            'TUSHARE_TOKEN': 'test_token',
            'WECOM_WEBHOOK_URL': 'https://test.webhook.url'
        }):
            env_config = config_manager.load_env_config()
            
            self.assertEqual(env_config['TUSHARE_TOKEN'], 'test_token')
            self.assertEqual(env_config['WECOM_WEBHOOK_URL'], 'https://test.webhook.url')
    
    def test_config_save_and_load(self):
        """测试配置保存和加载"""
        config_manager = ConfigManager()
        config_manager.config_file = Path(self.config_file)
        
        # 修改配置
        modified_config = self.test_config_data.copy()
        modified_config['system']['name'] = 'Modified Trading System'
        
        # 保存配置
        success = config_manager.save_config(modified_config)
        self.assertTrue(success, "配置保存应该成功")
        
        # 重新加载配置
        loaded_config = config_manager.load_config()
        self.assertEqual(loaded_config['system']['name'], 'Modified Trading System')
    
    def test_nested_config_access(self):
        """测试嵌套配置访问"""
        with patch.object(Config, '__init__', lambda x, config_file=None: None):
            config = Config()
            config._config = self.test_config_data
            
            # 测试get方法
            self.assertEqual(config.get('system.name'), 'Test Trading System')
            self.assertEqual(config.get('monitoring.volatility_threshold'), 0.03)
            self.assertEqual(config.get('nonexistent.key', 'default'), 'default')
    
    def test_config_type_conversion(self):
        """测试配置类型转换"""
        with patch.object(Config, '__init__', lambda x, config_file=None: None):
            config = Config()
            config._config = self.test_config_data
            config._parse_config()
            
            # 验证类型转换
            self.assertIsInstance(config.monitoring.volatility_threshold, float)
            self.assertIsInstance(config.monitoring.check_interval, int)
            self.assertIsInstance(config.monitoring.stocks, list)
            self.assertIsInstance(config.notification.wecom_enabled, bool)
    
    def test_config_error_handling(self):
        """测试配置错误处理"""
        # 测试文件不存在
        with self.assertRaises(FileNotFoundError):
            Config('nonexistent_config.yaml')
        
        # 测试无效YAML
        invalid_yaml_file = os.path.join(self.temp_dir, 'invalid.yaml')
        with open(invalid_yaml_file, 'w') as f:
            f.write('invalid: yaml: content: [')
        
        with self.assertRaises(ValueError):
            Config(invalid_yaml_file)
    
    def test_config_defaults(self):
        """测试配置默认值"""
        # 创建最小配置
        minimal_config = {'system': {'name': 'Minimal System'}}
        minimal_config_file = os.path.join(self.temp_dir, 'minimal.yaml')
        
        with open(minimal_config_file, 'w') as f:
            yaml.dump(minimal_config, f)
        
        with patch.object(Config, '__init__', lambda x, config_file=None: None):
            config = Config()
            config.config_file = Path(minimal_config_file)
            config._load_config()
            config._parse_config()
            
            # 验证默认值
            self.assertEqual(config.database.url, 'sqlite:///stock_trading.db')
            self.assertEqual(config.risk.max_position_size, 10000)
    
    def test_environment_variable_replacement(self):
        """测试环境变量替换"""
        config_with_env = {
            'database': {
                'url': '${DATABASE_URL}'
            },
            'notification': {
                'wecom': {
                    'webhook_url': '${WECOM_WEBHOOK_URL}'
                }
            }
        }
        
        with patch.object(Config, '__init__', lambda x, config_file=None: None):
            config = Config()
            config._config = config_with_env
            
            with patch.dict(os.environ, {
                'DATABASE_URL': 'sqlite:///test.db',
                'WECOM_WEBHOOK_URL': 'https://test.webhook.url'
            }):
                config._replace_env_vars(config._config)
                
                self.assertEqual(config._config['database']['url'], 'sqlite:///test.db')
                self.assertEqual(config._config['notification']['wecom']['webhook_url'], 'https://test.webhook.url')


if __name__ == '__main__':
    unittest.main()