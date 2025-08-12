#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块

负责加载和管理系统配置
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """数据库配置"""
    url: str
    echo: bool = False
    pool_size: int = 10


@dataclass
class RiskConfig:
    """风险管理配置"""
    max_position_size: float
    max_positions: int
    stop_loss: float
    take_profit: float
    risk_tolerance: float


@dataclass
class MonitoringConfig:
    """监控配置"""
    stocks: List[str]
    volatility_threshold: float
    check_interval: int


@dataclass
class StrategyConfig:
    """策略配置"""
    name: str
    analysis_period: int
    pressure_factor: float
    support_factor: float
    volume_threshold: float


@dataclass
class NotificationConfig:
    """通知配置"""
    wecom_enabled: bool
    wecom_webhook_url: str
    mention_all: bool = False


class Config:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.project_root = Path(__file__).parent.parent.parent
        self.config_file = self.project_root / config_file
        
        # 加载环境变量
        load_dotenv(self.project_root / ".env")
        
        # 加载配置
        self._load_config()
        
    def _load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
                
            # 替换环境变量
            self._replace_env_vars(self._config)
            
            # 解析配置
            self._parse_config()
            
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件不存在: {self.config_file}")
        except yaml.YAMLError as e:
            raise ValueError(f"配置文件格式错误: {e}")
    
    def _replace_env_vars(self, obj):
        """递归替换环境变量"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    env_var = value[2:-1]
                    obj[key] = os.getenv(env_var, value)
                elif isinstance(value, (dict, list)):
                    self._replace_env_vars(value)
        elif isinstance(obj, list):
            for item in obj:
                self._replace_env_vars(item)
    
    def _parse_config(self):
        """解析配置"""
        # 系统配置
        self.system = self._config.get('system', {})
        
        # 数据源配置
        self.data_sources = self._config.get('data_sources', {})
        
        # 数据库配置
        db_config = self._config.get('database', {})
        self.database = DatabaseConfig(
            url=db_config.get('url', 'sqlite:///stock_trading.db'),
            echo=db_config.get('echo', False),
            pool_size=db_config.get('pool_size', 10)
        )
        
        # 风险管理配置
        risk_config = self._config.get('risk_management', {})
        self.risk = RiskConfig(
            max_position_size=risk_config.get('max_position_size', 10000),
            max_positions=risk_config.get('max_positions', 5),
            stop_loss=risk_config.get('stop_loss', 0.05),
            take_profit=risk_config.get('take_profit', 0.10),
            risk_tolerance=risk_config.get('risk_tolerance', 0.02)
        )
        
        # 监控配置
        monitor_config = self._config.get('monitoring', {})
        self.monitoring = MonitoringConfig(
            stocks=monitor_config.get('stocks', []),
            volatility_threshold=monitor_config.get('volatility_threshold', 0.03),
            check_interval=monitor_config.get('check_interval', 60)
        )
        
        # 策略配置
        strategy_config = self._config.get('strategy', {})
        params = strategy_config.get('parameters', {})
        self.strategy = StrategyConfig(
            name=strategy_config.get('name', 'pressure_support_strategy'),
            analysis_period=params.get('analysis_period', 6),
            pressure_factor=params.get('pressure_factor', 1.05),
            support_factor=params.get('support_factor', 0.95),
            volume_threshold=params.get('volume_threshold', 1.5)
        )
        
        # 通知配置
        notification_config = self._config.get('notification', {})
        wecom_config = notification_config.get('wecom', {})
        self.notification = NotificationConfig(
            wecom_enabled=wecom_config.get('enabled', True),
            wecom_webhook_url=wecom_config.get('webhook_url', ''),
            mention_all=wecom_config.get('mention_all', False)
        )
        
        # 日志配置
        self.logging = self._config.get('logging', {})
        
        # 回测配置
        self.backtest = self._config.get('backtest', {})
    
    def get(self, key: str, default=None):
        """获取配置值"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def get_env(self, key: str, default=None):
        """获取环境变量"""
        return os.getenv(key, default)
    
    @property
    def project_root_path(self) -> Path:
        """项目根目录路径"""
        return self.project_root
    
    @property
    def logs_dir(self) -> Path:
        """日志目录路径"""
        return self.project_root / "logs"
    
    def __repr__(self):
        return f"Config(file={self.config_file})"


# 全局配置实例
config = Config()