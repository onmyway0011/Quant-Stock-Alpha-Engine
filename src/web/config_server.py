#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理Web服务器

提供统一的配置页面，集成所有系统配置
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.serving import make_server
import threading

from ..core.config import Config
from ..utils.logger import LoggerMixin


class ConfigManager(LoggerMixin):
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.yaml", env_file: str = ".env"):
        self.project_root = Path(__file__).parent.parent.parent
        self.config_file = self.project_root / config_file
        self.env_file = self.project_root / env_file
        self.env_example_file = self.project_root / ".env.example"
        
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def save_config(self, config_data: Dict[str, Any]) -> bool:
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            self.logger.info("配置文件保存成功")
            return True
        except Exception as e:
            self.logger.error(f"保存配置文件失败: {e}")
            return False
    
    def load_env_config(self) -> Dict[str, str]:
        """加载环境变量配置"""
        env_config = {}
        
        # 从.env.example读取所有可配置项
        if self.env_example_file.exists():
            with open(self.env_example_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key = line.split('=')[0]
                        env_config[key] = os.getenv(key, '')
        
        return env_config
    
    def save_env_config(self, env_data: Dict[str, str]) -> bool:
        """保存环境变量配置"""
        try:
            with open(self.env_file, 'w', encoding='utf-8') as f:
                for key, value in env_data.items():
                    f.write(f"{key}={value}\n")
            self.logger.info("环境变量配置保存成功")
            return True
        except Exception as e:
            self.logger.error(f"保存环境变量配置失败: {e}")
            return False
    
    def get_config_schema(self) -> Dict[str, Any]:
        """获取配置模式定义"""
        return {
            'system': {
                'name': {'type': 'string', 'description': '系统名称'},
                'version': {'type': 'string', 'description': '系统版本'},
                'timezone': {'type': 'string', 'description': '时区设置'}
            },
            'data_sources': {
                'primary': {'type': 'select', 'options': ['tushare', 'akshare'], 'description': '主要数据源'},
                'backup': {'type': 'select', 'options': ['tushare', 'akshare'], 'description': '备用数据源'},
                'realtime': {'type': 'select', 'options': ['sina', 'tushare'], 'description': '实时数据源'}
            },
            'monitoring': {
                'stocks': {'type': 'array', 'description': '监控股票列表'},
                'volatility_threshold': {'type': 'number', 'min': 0.01, 'max': 0.1, 'description': '波动率阈值'},
                'check_interval': {'type': 'number', 'min': 10, 'max': 300, 'description': '检查间隔(秒)'}
            },
            'strategy': {
                'name': {'type': 'string', 'description': '策略名称'},
                'parameters': {
                    'analysis_period': {'type': 'number', 'min': 1, 'max': 12, 'description': '分析周期(月)'},
                    'pressure_factor': {'type': 'number', 'min': 1.0, 'max': 1.2, 'description': '压力位因子'},
                    'support_factor': {'type': 'number', 'min': 0.8, 'max': 1.0, 'description': '支撑位因子'},
                    'volume_threshold': {'type': 'number', 'min': 1.0, 'max': 5.0, 'description': '成交量阈值'}
                }
            },
            'risk_management': {
                'max_position_size': {'type': 'number', 'min': 1000, 'max': 100000, 'description': '最大持仓金额'},
                'max_positions': {'type': 'number', 'min': 1, 'max': 20, 'description': '最大持仓数量'},
                'stop_loss': {'type': 'number', 'min': 0.01, 'max': 0.2, 'description': '止损比例'},
                'take_profit': {'type': 'number', 'min': 0.05, 'max': 0.5, 'description': '止盈比例'},
                'risk_tolerance': {'type': 'number', 'min': 0.01, 'max': 0.1, 'description': '风险容忍度'}
            },
            'notification': {
                'wecom': {
                    'enabled': {'type': 'boolean', 'description': '启用企微通知'},
                    'mention_all': {'type': 'boolean', 'description': '@所有人'}
                }
            },
            'logging': {
                'level': {'type': 'select', 'options': ['DEBUG', 'INFO', 'WARNING', 'ERROR'], 'description': '日志级别'},
                'rotation': {'type': 'string', 'description': '日志轮转'},
                'retention': {'type': 'string', 'description': '日志保留期'}
            }
        }
    
    def get_env_schema(self) -> Dict[str, Any]:
        """获取环境变量模式定义"""
        return {
            'TUSHARE_TOKEN': {'type': 'password', 'description': 'Tushare API Token'},
            'ALPHA_VANTAGE_API_KEY': {'type': 'password', 'description': 'Alpha Vantage API Key'},
            'WECOM_WEBHOOK_URL': {'type': 'url', 'description': '企业微信Webhook URL'},
            'DATABASE_URL': {'type': 'string', 'description': '数据库连接URL'},
            'MAX_POSITION_SIZE': {'type': 'number', 'description': '最大持仓金额'},
            'RISK_TOLERANCE': {'type': 'number', 'description': '风险容忍度'},
            'STOP_LOSS_RATIO': {'type': 'number', 'description': '止损比例'},
            'TAKE_PROFIT_RATIO': {'type': 'number', 'description': '止盈比例'},
            'MONITOR_INTERVAL': {'type': 'number', 'description': '监控间隔'},
            'VOLATILITY_THRESHOLD': {'type': 'number', 'description': '波动率阈值'},
            'LOG_LEVEL': {'type': 'select', 'options': ['DEBUG', 'INFO', 'WARNING', 'ERROR'], 'description': '日志级别'},
            'LOG_FILE': {'type': 'string', 'description': '日志文件路径'},
            'ANALYSIS_PERIOD_MONTHS': {'type': 'number', 'description': '分析周期(月)'},
            'PRESSURE_LEVEL_FACTOR': {'type': 'number', 'description': '压力位因子'},
            'SUPPORT_LEVEL_FACTOR': {'type': 'number', 'description': '支撑位因子'}
        }
    
    def validate_config(self, config_data: Dict[str, Any]) -> List[str]:
        """验证配置数据"""
        errors = []
        schema = self.get_config_schema()
        
        def validate_section(data, schema_section, path=""):
            for key, rules in schema_section.items():
                current_path = f"{path}.{key}" if path else key
                
                if key not in data:
                    errors.append(f"缺少必需配置项: {current_path}")
                    continue
                
                value = data[key]
                
                if isinstance(rules, dict) and 'type' in rules:
                    # 验证类型和范围
                    if rules['type'] == 'number':
                        try:
                            num_value = float(value)
                            if 'min' in rules and num_value < rules['min']:
                                errors.append(f"{current_path}: 值 {num_value} 小于最小值 {rules['min']}")
                            if 'max' in rules and num_value > rules['max']:
                                errors.append(f"{current_path}: 值 {num_value} 大于最大值 {rules['max']}")
                        except (ValueError, TypeError):
                            errors.append(f"{current_path}: 不是有效的数字")
                    
                    elif rules['type'] == 'array' and not isinstance(value, list):
                        errors.append(f"{current_path}: 应该是数组类型")
                    
                    elif rules['type'] == 'boolean' and not isinstance(value, bool):
                        errors.append(f"{current_path}: 应该是布尔类型")
                
                elif isinstance(rules, dict) and 'type' not in rules:
                    # 嵌套对象
                    if isinstance(value, dict):
                        validate_section(value, rules, current_path)
                    else:
                        errors.append(f"{current_path}: 应该是对象类型")
        
        validate_section(config_data, schema)
        return errors


class ConfigServer(LoggerMixin):
    """配置管理Web服务器"""
    
    def __init__(self, host='127.0.0.1', port=8080):
        self.host = host
        self.port = port
        self.app = Flask(__name__, 
                        template_folder=str(Path(__file__).parent / 'templates'),
                        static_folder=str(Path(__file__).parent / 'static'))
        self.app.secret_key = 'quant_config_secret_key_2024'
        self.config_manager = ConfigManager()
        self.server = None
        self.server_thread = None
        
        self._setup_routes()
    
    def _setup_routes(self):
        """设置路由"""
        
        @self.app.route('/')
        def index():
            """主页"""
            return render_template('index.html')
        
        @self.app.route('/config')
        def config_page():
            """配置页面"""
            config_data = self.config_manager.load_config()
            env_data = self.config_manager.load_env_config()
            config_schema = self.config_manager.get_config_schema()
            env_schema = self.config_manager.get_env_schema()
            
            return render_template('config.html', 
                                 config_data=config_data,
                                 env_data=env_data,
                                 config_schema=config_schema,
                                 env_schema=env_schema)
        
        @self.app.route('/api/config', methods=['GET'])
        def get_config():
            """获取配置API"""
            config_data = self.config_manager.load_config()
            env_data = self.config_manager.load_env_config()
            return jsonify({
                'config': config_data,
                'env': env_data,
                'schema': {
                    'config': self.config_manager.get_config_schema(),
                    'env': self.config_manager.get_env_schema()
                }
            })
        
        @self.app.route('/api/config', methods=['POST'])
        def save_config():
            """保存配置API"""
            try:
                data = request.get_json()
                config_data = data.get('config', {})
                env_data = data.get('env', {})
                
                # 验证配置
                errors = self.config_manager.validate_config(config_data)
                if errors:
                    return jsonify({'success': False, 'errors': errors}), 400
                
                # 保存配置
                config_saved = self.config_manager.save_config(config_data)
                env_saved = self.config_manager.save_env_config(env_data)
                
                if config_saved and env_saved:
                    return jsonify({'success': True, 'message': '配置保存成功'})
                else:
                    return jsonify({'success': False, 'message': '配置保存失败'}), 500
                    
            except Exception as e:
                self.logger.error(f"保存配置失败: {e}")
                return jsonify({'success': False, 'message': str(e)}), 500
        
        @self.app.route('/api/validate', methods=['POST'])
        def validate_config():
            """验证配置API"""
            try:
                data = request.get_json()
                config_data = data.get('config', {})
                
                errors = self.config_manager.validate_config(config_data)
                
                return jsonify({
                    'valid': len(errors) == 0,
                    'errors': errors
                })
                
            except Exception as e:
                return jsonify({'valid': False, 'errors': [str(e)]}), 500
        
        @self.app.route('/api/test-connection', methods=['POST'])
        def test_connection():
            """测试连接API"""
            try:
                data = request.get_json()
                connection_type = data.get('type')
                config = data.get('config', {})
                
                # 这里可以添加实际的连接测试逻辑
                if connection_type == 'database':
                    # 测试数据库连接
                    result = self._test_database_connection(config.get('DATABASE_URL', ''))
                elif connection_type == 'wecom':
                    # 测试企微连接
                    result = self._test_wecom_connection(config.get('WECOM_WEBHOOK_URL', ''))
                elif connection_type == 'tushare':
                    # 测试Tushare连接
                    result = self._test_tushare_connection(config.get('TUSHARE_TOKEN', ''))
                else:
                    result = {'success': False, 'message': '不支持的连接类型'}
                
                return jsonify(result)
                
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)}), 500
        
        @self.app.route('/logs')
        def logs_page():
            """日志页面"""
            return render_template('logs.html')
        
        @self.app.route('/api/logs')
        def get_logs():
            """获取日志API"""
            try:
                log_file = Path(self.config_manager.project_root) / 'logs' / 'trading.log'
                if log_file.exists():
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        # 返回最后100行
                        return jsonify({
                            'logs': lines[-100:],
                            'total_lines': len(lines)
                        })
                else:
                    return jsonify({'logs': [], 'total_lines': 0})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
    
    def _test_database_connection(self, db_url: str) -> Dict[str, Any]:
        """测试数据库连接"""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(db_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {'success': True, 'message': '数据库连接成功'}
        except Exception as e:
            return {'success': False, 'message': f'数据库连接失败: {str(e)}'}
    
    def _test_wecom_connection(self, webhook_url: str) -> Dict[str, Any]:
        """测试企微连接"""
        try:
            import requests
            test_message = {
                "msgtype": "text",
                "text": {
                    "content": "配置测试消息"
                }
            }
            response = requests.post(webhook_url, json=test_message, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    return {'success': True, 'message': '企微连接成功'}
                else:
                    return {'success': False, 'message': f'企微API错误: {result}'}
            else:
                return {'success': False, 'message': f'HTTP错误: {response.status_code}'}
        except Exception as e:
            return {'success': False, 'message': f'企微连接失败: {str(e)}'}
    
    def _test_tushare_connection(self, token: str) -> Dict[str, Any]:
        """测试Tushare连接"""
        try:
            import tushare as ts
            ts.set_token(token)
            pro = ts.pro_api()
            # 测试获取股票基本信息
            df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name')
            if df is not None and not df.empty:
                return {'success': True, 'message': 'Tushare连接成功'}
            else:
                return {'success': False, 'message': 'Tushare返回空数据'}
        except Exception as e:
            return {'success': False, 'message': f'Tushare连接失败: {str(e)}'}
    
    def start(self):
        """启动服务器"""
        try:
            self.server = make_server(self.host, self.port, self.app, threaded=True)
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            self.logger.info(f"配置管理服务器已启动: http://{self.host}:{self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"启动配置服务器失败: {e}")
            return False
    
    def stop(self):
        """停止服务器"""
        if self.server:
            self.server.shutdown()
            self.logger.info("配置管理服务器已停止")
    
    def get_url(self) -> str:
        """获取服务器URL"""
        return f"http://{self.host}:{self.port}"