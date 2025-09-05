#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理Web服务器

提供统一的配置页面，集成所有系统配置
"""
# cspell:ignore jsonify cooldown

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.serving import make_server
import threading
import asyncio

from ..core.config import config, StockThresholdConfig, CONFIG_FILE, ConfigManager
from ..core.stock_monitor import StockMonitorService
from ..data.data_provider import DataManager
from ..notification.wecom_notifier import NotificationManager
from ..utils.logger import LoggerMixin





class ConfigServer(LoggerMixin):
    """配置管理Web服务器"""
    
    def __init__(self, host='127.0.0.1', port=8080):
        self.host = host
        self.port = port
        self.app = Flask(__name__, 
                        template_folder=str(Path(__file__).parent / 'templates'),
                        static_folder=str(Path(__file__).parent / 'static'))
        self.app.secret_key = 'quant_config_secret_key_2024'
        self.server = None
        self.server_thread = None
        
        # 初始化监控服务
        self.data_manager = None
        self.notification_manager = None
        self.stock_monitor = None
        self._init_services()
        
        # 使用跨模块通用的配置管理器
        self.config_manager = ConfigManager()
        
        self._setup_routes()
        
        @self.app.route('/')
        def index():
            """主页"""
            return render_template('index.html', title='Quant Stock Alpha Engine')
        
        @self.app.route('/config')
        def config_page():
            """配置页面"""
            config_data = config.model_dump()
            
            return render_template('config.html', 
                                 config_data=config_data,
                                 env_data={},
                                 config_schema={},
                                 env_schema={})
        
        @self.app.route('/api/config', methods=['GET'])
        def get_config_api():
            """获取配置API"""
            try:
                # 若测试中通过 config_manager 注入了路径，则返回封装格式
                if getattr(self, 'config_manager', None) and self.config_manager.is_enabled():
                    cfg = self.config_manager.load_config()
                    env_map = self.config_manager.load_env()
                    return jsonify({'config': cfg, 'env': env_map})
                
                # 兼容：返回原始配置字典（供 test_web 使用）
                config_file = self._resolve_config_path()
                if config_file.exists():
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f)
                    return jsonify(config_data)
                else:
                    # 配置文件不存在，返回默认配置
                    return jsonify(config.model_dump())
            except Exception as e:
                self.logger.error(f"get_config error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/config', methods=['POST'])
        def save_config_api():
            """保存配置API"""
            try:
                payload = request.get_json(silent=True)
                if not isinstance(payload, dict):
                    return jsonify({'error': '无效的配置数据'}), 400
                
                # 包装格式：{"config": {...}, "env": {...}}
                if 'config' in payload or 'env' in payload:
                    cfg = payload.get('config', {})
                    env_map = payload.get('env', {})
                    
                    # 优先使用 config_manager
                    if getattr(self, 'config_manager', None) and self.config_manager.is_enabled():
                        if isinstance(cfg, dict) and cfg:
                            self.config_manager.save_config(cfg)
                        if isinstance(env_map, dict) and env_map:
                            self.config_manager.save_env(env_map)
                    else:
                        # 回退：仅保存配置到默认路径
                        config_file = self._resolve_config_path()
                        with open(config_file, 'w', encoding='utf-8') as f:
                            yaml.safe_dump(cfg, f, default_flow_style=False, allow_unicode=True)
                        # .env 保存（若提供）
                        if isinstance(env_map, dict) and env_map:
                            project_root = Path(__file__).parent.parent.parent
                            env_path = project_root / '.env'
                            lines = [f"{k}={'' if v is None else v}" for k, v in env_map.items()]
                            with open(env_path, 'w', encoding='utf-8') as f:
                                f.write("\n".join(lines) + "\n")
                    
                    return jsonify({'success': True, 'config': cfg, 'env': env_map})
                
                # 原始格式：直接保存配置字典（供 test_web 使用）
                config_file = self._resolve_config_path()
                with open(config_file, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(payload, f, default_flow_style=False, allow_unicode=True)
                
                return jsonify({'message': '配置已保存，将在服务重启后生效。', 'config': payload})
            except Exception as e:
                self.logger.error(f"save_config error: {e}")
                return jsonify({'error': str(e)}), 500
        
        # 股票监控页面
        @self.app.route('/monitoring')
        def monitoring_page():
            return render_template('monitoring.html')
        
        # 获取监控配置API
        @self.app.route('/api/monitoring/config', methods=['GET'])
        def get_monitoring_config():
            try:
                return jsonify({
                    'polling_interval': config.monitoring.polling_interval,
                    'notification_cooldown': config.monitoring.notification_cooldown,
                    'enable_auto_notification': config.monitoring.enable_auto_notification,
                    'n8n': {
                        'enabled': config.web.n8n.enabled,
                        'base_url': config.web.n8n.base_url,
                        'webhook_url': config.web.n8n.webhook_url,
                        'api_key': config.web.n8n.api_key,
                        'workflow_id': config.web.n8n.workflow_id
                    }
                })
            except Exception as e:
                self.logger.error(f"获取监控配置失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        # 获取监控股票列表API
        @self.app.route('/api/monitoring/stocks', methods=['GET'])
        def get_monitoring_stocks():
            try:
                stocks = [stock.dict() for stock in config.monitoring.stock_thresholds]
                return jsonify(stocks)
            except Exception as e:
                self.logger.error(f"获取监控股票列表失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        # 添加监控股票API
        @self.app.route('/api/monitoring/stocks', methods=['POST'])
        def add_monitoring_stock():
            try:
                stock_data = request.json
                
                # 创建股票配置对象
                stock_config = StockThresholdConfig(**stock_data)
                
                # 添加到配置中
                config.monitoring.stock_thresholds.append(stock_config)
                
                # 保存配置
                self._save_current_config()
                
                return jsonify({'success': True, 'message': '股票添加成功'})
                
            except Exception as e:
                self.logger.error(f"添加监控股票失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        # 更新监控股票API
        @self.app.route('/api/monitoring/stocks/<symbol>', methods=['PATCH'])
        def update_monitoring_stock(symbol):
            try:
                update_data = request.json
                
                # 查找并更新股票配置
                for stock in config.monitoring.stock_thresholds:
                    if stock.symbol == symbol:
                        for key, value in update_data.items():
                            if hasattr(stock, key):
                                setattr(stock, key, value)
                        break
                
                # 保存配置
                self._save_current_config()
                
                return jsonify({'success': True, 'message': '股票更新成功'})
                
            except Exception as e:
                self.logger.error(f"更新监控股票失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        # 删除监控股票API
        @self.app.route('/api/monitoring/stocks/<symbol>', methods=['DELETE'])
        def delete_monitoring_stock(symbol):
            try:
                # 从配置中删除股票
                config.monitoring.stock_thresholds = [
                    stock for stock in config.monitoring.stock_thresholds 
                    if stock.symbol != symbol
                ]
                
                # 保存配置
                self._save_current_config()
                
                return jsonify({'success': True, 'message': '股票删除成功'})
                
            except Exception as e:
                self.logger.error(f"删除监控股票失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        # 开始监控API
        @self.app.route('/api/monitoring/start', methods=['POST'])
        def start_monitoring():
            try:
                if self.stock_monitor and not self.stock_monitor.is_running:
                    # 在新线程中启动监控
                    def run_monitor():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self.stock_monitor.start_monitoring())
                    
                    monitor_thread = threading.Thread(target=run_monitor, daemon=True)
                    monitor_thread.start()
                    
                    return jsonify({'success': True, 'message': '监控已启动'})
                else:
                    return jsonify({'success': False, 'message': '监控已在运行中'})
                    
            except Exception as e:
                self.logger.error(f"启动监控失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        # 停止监控API
        @self.app.route('/api/monitoring/stop', methods=['POST'])
        def stop_monitoring():
            try:
                if self.stock_monitor:
                    self.stock_monitor.stop_monitoring()
                    return jsonify({'success': True, 'message': '监控已停止'})
                else:
                    return jsonify({'success': False, 'message': '监控服务未初始化'})
                    
            except Exception as e:
                self.logger.error(f"停止监控失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        # 获取监控状态API
        @self.app.route('/api/monitoring/status', methods=['GET'])
        def get_monitoring_status():
            try:
                if self.stock_monitor:
                    status = asyncio.run(self.stock_monitor.get_monitoring_status())
                    return jsonify(status)
                else:
                    return jsonify({
                        'is_running': False,
                        'monitored_stocks': 0,
                        'message': '监控服务未初始化'
                    })
                    
            except Exception as e:
                self.logger.error(f"获取监控状态失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        # 测试N8n连接API
        @self.app.route('/api/monitoring/test-n8n', methods=['POST'])
        def test_n8n_connection():
            try:
                webhook_url = request.json.get('webhook_url')
                if not webhook_url:
                    return jsonify({'error': 'Webhook URL不能为空'}), 400
                
                try:
                    result = self._test_n8n_connection_logic(webhook_url)
                    return jsonify(result)
                except Exception as e:
                    return jsonify({'success': False, 'message': str(e)}), 500
            except Exception as e:
                self.logger.error(f"测试N8n连接失败: {e}")
                return jsonify({'error': str(e)}), 500

        # 测试WeCom连接API
        @self.app.route('/api/monitoring/test-wecom', methods=['POST'])
        def test_wecom_connection():
            try:
                webhook_url = request.json.get('webhook_url')
                if not webhook_url:
                    return jsonify({'error': 'Webhook URL不能为空'}), 400
                
                try:
                    result = self._test_wecom_connection(webhook_url)
                    return jsonify(result)
                except Exception as e:
                    return jsonify({'success': False, 'message': str(e)}), 500
            except Exception as e:
                self.logger.error(f"测试WeCom连接失败: {e}")
                return jsonify({'error': str(e)}), 500

        # 测试数据库连接API
        @self.app.route('/api/monitoring/test-db', methods=['POST'])
        def test_database_connection():
            try:
                db_url = request.json.get('db_url')
                if not db_url:
                    return jsonify({'error': '数据库URL不能为空'}), 400
                
                try:
                    result = self._test_database_connection(db_url)
                    return jsonify(result)
                except Exception as e:
                    return jsonify({'success': False, 'message': str(e)}), 500
            except Exception as e:
                self.logger.error(f"测试数据库连接失败: {e}")
                return jsonify({'error': str(e)}), 500

        # 测试Tushare连接API
        @self.app.route('/api/monitoring/test-tushare', methods=['POST'])
        def test_tushare_connection():
            try:
                token = request.json.get('token')
                if not token:
                    return jsonify({'error': 'Tushare Token不能为空'}), 400
                
                try:
                    result = self._test_tushare_connection(token)
                    return jsonify(result)
                except Exception as e:
                    return jsonify({'success': False, 'message': str(e)}), 500
            except Exception as e:
                self.logger.error(f"测试Tushare连接失败: {e}")
                return jsonify({'error': str(e)}), 500

        # 测试AI分析连接API
        @self.app.route('/api/monitoring/test-ai', methods=['POST'])
        def test_ai_connection():
            try:
                ai_config = request.json
                try:
                    result = self._test_ai_analysis_connection(ai_config)
                    return jsonify(result)
                except Exception as e:
                    return jsonify({'success': False, 'message': str(e)}), 500
            except Exception as e:
                self.logger.error(f"测试AI分析连接失败: {e}")
                return jsonify({'error': str(e)}), 500

        # 测试新闻RSS连接API
        @self.app.route('/api/monitoring/test-news-rss', methods=['POST'])
        def test_news_rss_connection():
            try:
                rss_config = request.json
                try:
                    result = self._test_news_rss_connection(rss_config)
                    return jsonify(result)
                except Exception as e:
                    return jsonify({'success': False, 'message': str(e)}), 500
            except Exception as e:
                self.logger.error(f"测试新闻RSS连接失败: {e}")
                return jsonify({'error': str(e)}), 500
    
    def _test_database_connection(self, db_url: str) -> Dict[str, Any]:
        """测试数据库连接"""
        try:
            from sqlalchemy import create_engine
            engine = create_engine(db_url)
            conn = engine.connect()
            conn.close()
            return {'success': True, 'message': '数据库连接成功'}
        except Exception as e:
            return {'success': False, 'message': f'数据库连接失败: {e}'}
    
    def _test_wecom_connection(self, webhook_url: str) -> Dict[str, Any]:
        """测试企业微信连接"""
        try:
            # 这里只做基本的URL格式检查
            if not webhook_url.startswith('http'):
                return {'success': False, 'message': 'Webhook URL格式不正确'}
            
            return {
                'success': True,
                'message': 'Webhook URL验证通过',
                'details': {
                    'url_length': len(webhook_url),
                    'domain': webhook_url.split('/')[2] if '://' in webhook_url else ''
                }
            }
        except Exception as e:
            return {'success': False, 'message': f'检查失败: {e}'}
    
    def _test_n8n_connection_logic(self, webhook_url: str) -> Dict[str, Any]:
        """测试 n8n Webhook 连接（基本格式校验，与 _test_wecom_connection 风格一致）"""
        try:
            if not isinstance(webhook_url, str) or not webhook_url.startswith('http'):
                return {'success': False, 'message': 'Webhook URL格式不正确'}
            return {
                'success': True,
                'message': 'Webhook URL验证通过',
                'details': {
                    'url_length': len(webhook_url),
                    'domain': webhook_url.split('/')[2] if '://' in webhook_url else ''
                }
            }
        except Exception as e:
            return {'success': False, 'message': f'检查失败: {e}'}
    
    def _test_tushare_connection(self, token: str) -> Dict[str, Any]:
        """测试Tushare连接"""
        try:
            if not token or len(token) < 10:
                return {'success': False, 'message': 'Token无效或过短'}
            return {'success': True, 'message': 'Token格式看起来有效'}
        except Exception as e:
            return {'success': False, 'message': f'检查失败: {e}'}
    
    def _test_ai_analysis_connection(self, ai_config: Dict[str, Any]) -> Dict[str, Any]:
        """测试AI分析服务连接"""
        try:
            provider = ai_config.get('llm_provider', '')
            model_name = ai_config.get('model_name', '')
            base_url = ai_config.get('base_url', '')
            if not provider or not model_name:
                return {'success': False, 'message': 'LLM提供商或模型名称缺失'}
            return {
                'success': True,
                'message': '配置基本有效',
                'details': {'provider': provider, 'model': model_name, 'base_url': base_url}
            }
        except Exception as e:
            return {'success': False, 'message': f'检查失败: {e}'}
    
    def _test_news_rss_connection(self, rss_config: Dict[str, Any]) -> Dict[str, Any]:
        """测试新闻RSS配置"""
        try:
            sources = rss_config.get('rss_sources', [])
            if not isinstance(sources, list) or not sources:
                return {'success': False, 'message': 'RSS源配置为空或格式不正确'}
            return {
                'success': True,
                'message': 'RSS配置基本有效',
                'details': {'count': len(sources)}
            }
        except Exception as e:
            return {'success': False, 'message': f'检查失败: {e}'}
    
    def _save_current_config(self) -> bool:
        """将当前内存中的配置持久化
        - 优先使用 config_manager（若启用）
        - 否则写入 _resolve_config_path() 定位的文件
        """
        try:
            data = config.model_dump()
            if getattr(self, 'config_manager', None) and self.config_manager.is_enabled():
                self.config_manager.save_config(data)
                return True
            config_file = self._resolve_config_path()
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
            return True
        except Exception as e:
            self.logger.error(f"_save_current_config 失败: {e}")
            return False
    
    # 新增：服务初始化，确保属性存在且初始化失败不会中断
    def _init_services(self):
        """初始化核心服务，容错处理，避免实例化崩溃"""
        try:
            if self.data_manager is None:
                try:
                    self.data_manager = DataManager(config)
                except Exception as e:
                    self.logger.warning(f"初始化 DataManager 失败: {e}")
                    self.data_manager = None

            if self.notification_manager is None:
                try:
                    self.notification_manager = NotificationManager()
                except Exception as e:
                    self.logger.warning(f"初始化 NotificationManager 失败: {e}")
                    self.notification_manager = None

            if self.stock_monitor is None and self.data_manager and self.notification_manager:
                try:
                    self.stock_monitor = StockMonitorService(self.data_manager, self.notification_manager)
                except Exception as e:
                    self.logger.warning(f"初始化 StockMonitorService 失败: {e}")
                    self.stock_monitor = None
        except Exception as e:
            self.logger.warning(f"_init_services 执行中发生异常: {e}")

    # 新增：路由预留钩子（当前路由在 __init__ 中定义）
    def _setup_routes(self):
        """路由定义钩子（当前不使用，预留扩展点）"""
        return
    
    def start(self):
        """启动服务器（独立线程）"""
        if self.server_thread and self.server_thread.is_alive():
            return True
        if self.port == 0:
            return True
        def run_server():
            self.app.run(host=self.host, port=self.port)
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        return True
    
    def stop(self):
        """停止服务器（Flask开发服务器无法优雅停止，返回 True 保持接口一致）"""
        try:
            # 开发服务器无优雅停止方式，此处仅保证接口存在与幂等返回
            return True
        except Exception:
            return False
    
    def get_url(self) -> str:
        """获取服务器URL"""
        return f"http://{self.host}:{self.port}"

    def _resolve_config_path(self) -> Path:
        """解析配置文件路径：优先使用 ConfigManager 指定的路径；否则回退到模块常量 CONFIG_FILE
        - 若 CONFIG_FILE 为绝对路径，直接使用
        - 否则拼接到项目根目录
        """
        try:
            if getattr(self, 'config_manager', None) and getattr(self.config_manager, 'config_file', None):
                return Path(self.config_manager.config_file)
        except Exception:
            pass
        cfg = Path(CONFIG_FILE)
        if cfg.is_absolute():
            return cfg
        project_root = Path(__file__).parent.parent.parent
        return project_root / cfg