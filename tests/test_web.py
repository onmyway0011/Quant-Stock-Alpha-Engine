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
from unittest.mock import patch, MagicMock

import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.web.config_server import ConfigServer, ConfigManager


class TestWebInterface(unittest.TestCase):
    """Web界面测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.yaml')
        self.env_file = os.path.join(self.temp_dir, '.env')
        self.env_example_file = os.path.join(self.temp_dir, '.env.example')
        
        # 创建测试配置文件
        self.test_config_data = {
            'system': {
                'name': 'Test Trading System',
                'version': '1.0.0',
                'timezone': 'Asia/Shanghai'
            },
            'monitoring': {
                'stocks': ['000001.SZ', '600519.SH'],
                'volatility_threshold': 0.03,
                'check_interval': 60
            },
            'risk_management': {
                'max_position_size': 10000,
                'stop_loss': 0.05
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.test_config_data, f)
        
        # 创建环境变量文件
        with open(self.env_file, 'w', encoding='utf-8') as f:
            f.write('TUSHARE_TOKEN=test_token\n')
            f.write('WECOM_WEBHOOK_URL=https://test.webhook.url\n')
        
        with open(self.env_example_file, 'w', encoding='utf-8') as f:
            f.write('TUSHARE_TOKEN=your_token_here\n')
            f.write('WECOM_WEBHOOK_URL=your_webhook_url\n')
            f.write('DATABASE_URL=sqlite:///stock_trading.db\n')
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_config_manager_initialization(self):
        """测试配置管理器初始化"""
        manager = ConfigManager(self.config_file, self.env_file)
        
        self.assertEqual(manager.config_file, Path(self.config_file))
        self.assertEqual(manager.env_file, Path(self.env_file))
    
    def test_config_manager_load_config(self):
        """测试加载配置"""
        manager = ConfigManager(self.config_file, self.env_file)
        
        config_data = manager.load_config()
        
        self.assertEqual(config_data['system']['name'], 'Test Trading System')
        self.assertEqual(config_data['monitoring']['volatility_threshold'], 0.03)
        self.assertIn('000001.SZ', config_data['monitoring']['stocks'])
    
    def test_config_manager_save_config(self):
        """测试保存配置"""
        manager = ConfigManager(self.config_file, self.env_file)
        
        # 修改配置
        modified_config = self.test_config_data.copy()
        modified_config['system']['name'] = 'Modified System'
        
        # 保存配置
        success = manager.save_config(modified_config)
        self.assertTrue(success)
        
        # 验证保存结果
        loaded_config = manager.load_config()
        self.assertEqual(loaded_config['system']['name'], 'Modified System')
    
    def test_config_manager_load_env_config(self):
        """测试加载环境变量配置"""
        manager = ConfigManager(self.config_file, self.env_file)
        manager.env_example_file = Path(self.env_example_file)
        
        with patch.dict(os.environ, {
            'TUSHARE_TOKEN': 'test_token',
            'WECOM_WEBHOOK_URL': 'https://test.webhook.url'
        }):
            env_config = manager.load_env_config()
            
            self.assertEqual(env_config['TUSHARE_TOKEN'], 'test_token')
            self.assertEqual(env_config['WECOM_WEBHOOK_URL'], 'https://test.webhook.url')
            self.assertIn('DATABASE_URL', env_config)
    
    def test_config_manager_save_env_config(self):
        """测试保存环境变量配置"""
        manager = ConfigManager(self.config_file, self.env_file)
        
        env_data = {
            'TUSHARE_TOKEN': 'new_token',
            'WECOM_WEBHOOK_URL': 'https://new.webhook.url',
            'DATABASE_URL': 'sqlite:///new.db'
        }
        
        success = manager.save_env_config(env_data)
        self.assertTrue(success)
        
        # 验证保存结果
        with open(self.env_file, 'r') as f:
            content = f.read()
            self.assertIn('TUSHARE_TOKEN=new_token', content)
            self.assertIn('https://new.webhook.url', content)
    
    def test_config_manager_get_schemas(self):
        """测试获取配置模式"""
        manager = ConfigManager()
        
        config_schema = manager.get_config_schema()
        env_schema = manager.get_env_schema()
        
        # 验证配置模式
        self.assertIn('system', config_schema)
        self.assertIn('monitoring', config_schema)
        self.assertIn('risk_management', config_schema)
        
        # 验证环境变量模式
        self.assertIn('TUSHARE_TOKEN', env_schema)
        self.assertIn('WECOM_WEBHOOK_URL', env_schema)
        self.assertIn('DATABASE_URL', env_schema)
        
        # 验证字段类型
        self.assertEqual(config_schema['monitoring']['volatility_threshold']['type'], 'number')
        self.assertEqual(env_schema['TUSHARE_TOKEN']['type'], 'password')
    
    def test_config_manager_validate_config(self):
        """测试配置验证"""
        manager = ConfigManager()
        
        # 测试有效配置
        valid_config = {
            'system': {'name': 'Test', 'version': '1.0.0'},
            'monitoring': {
                'stocks': ['000001.SZ'],
                'volatility_threshold': 0.03,
                'check_interval': 60
            },
            'risk_management': {
                'max_position_size': 10000,
                'stop_loss': 0.05
            }
        }
        
        errors = manager.validate_config(valid_config)
        self.assertEqual(len(errors), 0)
        
        # 测试无效配置
        invalid_config = valid_config.copy()
        invalid_config['monitoring']['volatility_threshold'] = -0.1  # 负值
        invalid_config['risk_management']['stop_loss'] = 1.5  # 超过最大值
        
        errors = manager.validate_config(invalid_config)
        self.assertGreater(len(errors), 0)
    
    def test_config_server_initialization(self):
        """测试配置服务器初始化"""
        server = ConfigServer(host='127.0.0.1', port=8080)
        
        self.assertEqual(server.host, '127.0.0.1')
        self.assertEqual(server.port, 8080)
        self.assertIsNotNone(server.app)
        self.assertIsNotNone(server.config_manager)
    
    def test_config_server_routes_setup(self):
        """测试配置服务器路由设置"""
        server = ConfigServer()
        
        # 检查路由是否正确设置
        with server.app.test_client() as client:
            # 测试主页路由
            response = client.get('/')
            self.assertEqual(response.status_code, 200)
            
            # 测试配置页面路由
            response = client.get('/config')
            self.assertEqual(response.status_code, 200)
            
            # 测试日志页面路由
            response = client.get('/logs')
            self.assertEqual(response.status_code, 200)
    
    def test_config_server_api_get_config(self):
        """测试获取配置API"""
        server = ConfigServer()
        server.config_manager = ConfigManager(self.config_file, self.env_file)
        server.config_manager.env_example_file = Path(self.env_example_file)
        
        with server.app.test_client() as client:
            response = client.get('/api/config')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            
            self.assertIn('config', data)
            self.assertIn('env', data)
            self.assertIn('schema', data)
            
            # 验证配置数据
            self.assertEqual(data['config']['system']['name'], 'Test Trading System')
    
    def test_config_server_api_save_config(self):
        """测试保存配置API"""
        server = ConfigServer()
        server.config_manager = ConfigManager(self.config_file, self.env_file)
        
        # 准备测试数据
        test_data = {
            'config': {
                'system': {'name': 'Updated System'},
                'monitoring': {
                    'stocks': ['000001.SZ'],
                    'volatility_threshold': 0.04,
                    'check_interval': 30
                },
                'risk_management': {
                    'max_position_size': 20000,
                    'stop_loss': 0.08
                }
            },
            'env': {
                'TUSHARE_TOKEN': 'updated_token',
                'WECOM_WEBHOOK_URL': 'https://updated.webhook.url'
            }
        }
        
        with server.app.test_client() as client:
            response = client.post('/api/config',
                                 data=json.dumps(test_data),
                                 content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            
            self.assertTrue(data['success'])
            self.assertEqual(data['message'], '配置保存成功')
    
    def test_config_server_api_validate_config(self):
        """测试验证配置API"""
        server = ConfigServer()
        
        # 测试有效配置
        valid_data = {
            'config': {
                'system': {'name': 'Test'},
                'monitoring': {
                    'volatility_threshold': 0.03,
                    'check_interval': 60
                },
                'risk_management': {
                    'max_position_size': 10000
                }
            }
        }
        
        with server.app.test_client() as client:
            response = client.post('/api/validate',
                                 data=json.dumps(valid_data),
                                 content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            
            self.assertTrue(data['valid'])
            self.assertEqual(len(data['errors']), 0)
    
    def test_config_server_api_test_connection(self):
        """测试连接测试API"""
        server = ConfigServer()
        
        # 模拟数据库连接测试
        with patch.object(server, '_test_database_connection') as mock_test:
            mock_test.return_value = {'success': True, 'message': '连接成功'}
            
            test_data = {
                'type': 'database',
                'config': {
                    'DATABASE_URL': 'sqlite:///test.db'
                }
            }
            
            with server.app.test_client() as client:
                response = client.post('/api/test-connection',
                                     data=json.dumps(test_data),
                                     content_type='application/json')
                
                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                
                self.assertTrue(data['success'])
                self.assertEqual(data['message'], '连接成功')
    
    def test_config_server_api_get_logs(self):
        """测试获取日志API"""
        server = ConfigServer()
        
        # 创建测试日志文件
        log_dir = Path(self.temp_dir) / 'logs'
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / 'trading.log'
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write('2024-01-01 10:00:00 | INFO | test | 测试日志1\n')
            f.write('2024-01-01 10:01:00 | ERROR | test | 测试日志2\n')
            f.write('2024-01-01 10:02:00 | WARNING | test | 测试日志3\n')
        
        # 修改配置管理器的项目根目录
        server.config_manager.project_root = Path(self.temp_dir)
        
        with server.app.test_client() as client:
            response = client.get('/api/logs')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            
            self.assertIn('logs', data)
            self.assertIn('total_lines', data)
            self.assertEqual(data['total_lines'], 3)
            self.assertEqual(len(data['logs']), 3)
    
    @patch('src.web.config_server.create_engine')
    def test_config_server_database_connection_test(self, mock_create_engine):
        """测试数据库连接测试"""
        server = ConfigServer()
        
        # 模拟成功连接
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_create_engine.return_value = mock_engine
        
        result = server._test_database_connection('sqlite:///test.db')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], '数据库连接成功')
        
        # 模拟连接失败
        mock_create_engine.side_effect = Exception('连接失败')
        
        result = server._test_database_connection('invalid_url')
        
        self.assertFalse(result['success'])
        self.assertIn('连接失败', result['message'])
    
    @patch('requests.post')
    def test_config_server_wecom_connection_test(self, mock_post):
        """测试企微连接测试"""
        server = ConfigServer()
        
        # 模拟成功响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'errcode': 0, 'errmsg': 'ok'}
        mock_post.return_value = mock_response
        
        result = server._test_wecom_connection('https://test.webhook.url')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], '企微连接成功')
        
        # 模拟失败响应
        mock_response.json.return_value = {'errcode': 40001, 'errmsg': 'invalid key'}
        
        result = server._test_wecom_connection('https://test.webhook.url')
        
        self.assertFalse(result['success'])
        self.assertIn('企微API错误', result['message'])
    
    @patch('tushare.pro_api')
    @patch('tushare.set_token')
    def test_config_server_tushare_connection_test(self, mock_set_token, mock_pro_api):
        """测试Tushare连接测试"""
        server = ConfigServer()
        
        # 模拟成功连接
        mock_pro = MagicMock()
        mock_pro.stock_basic.return_value = MagicMock(empty=False)
        mock_pro_api.return_value = mock_pro
        
        result = server._test_tushare_connection('test_token')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], 'Tushare连接成功')
        
        # 模拟连接失败
        mock_pro_api.side_effect = Exception('API错误')
        
        result = server._test_tushare_connection('invalid_token')
        
        self.assertFalse(result['success'])
        self.assertIn('Tushare连接失败', result['message'])
    
    def test_config_server_start_stop(self):
        """测试配置服务器启动和停止"""
        server = ConfigServer(host='127.0.0.1', port=0)  # 使用随机端口
        
        # 测试启动
        success = server.start()
        self.assertTrue(success)
        self.assertIsNotNone(server.server)
        self.assertIsNotNone(server.server_thread)
        
        # 测试URL获取
        url = server.get_url()
        self.assertIn('http://127.0.0.1:', url)
        
        # 测试停止
        server.stop()
    
    def test_config_server_error_handling(self):
        """测试配置服务器错误处理"""
        server = ConfigServer()
        
        # 测试无效配置保存
        invalid_data = {
            'config': {
                'invalid_section': 'invalid_value'
            },
            'env': {}
        }
        
        with server.app.test_client() as client:
            response = client.post('/api/config',
                                 data=json.dumps(invalid_data),
                                 content_type='application/json')
            
            # 应该返回错误
            self.assertIn(response.status_code, [400, 500])
    
    def test_config_server_template_rendering(self):
        """测试模板渲染"""
        server = ConfigServer()
        server.config_manager = ConfigManager(self.config_file, self.env_file)
        server.config_manager.env_example_file = Path(self.env_example_file)
        
        with server.app.test_client() as client:
            # 测试配置页面渲染
            response = client.get('/config')
            
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Test Trading System', response.data)
            
            # 测试日志页面渲染
            response = client.get('/logs')
            
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'\xe7\xb3\xbb\xe7\xbb\x9f\xe6\x97\xa5\xe5\xbf\x97', response.data)  # "系统日志" in UTF-8
    
    def test_config_server_static_files(self):
        """测试静态文件服务"""
        server = ConfigServer()
        
        with server.app.test_client() as client:
            # 测试CSS文件（如果存在）
            response = client.get('/static/css/style.css')
            # 文件可能不存在，但不应该是500错误
            self.assertNotEqual(response.status_code, 500)
            
            # 测试JS文件（如果存在）
            response = client.get('/static/js/app.js')
            # 文件可能不存在，但不应该是500错误
            self.assertNotEqual(response.status_code, 500)


if __name__ == '__main__':
    unittest.main()