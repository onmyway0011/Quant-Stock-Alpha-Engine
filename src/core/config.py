#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块

负责加载和管理系统配置
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator

class SystemConfig(BaseModel):
    """系统配置"""
    name: str = Field("Quant Stock Alpha Engine", description="系统名称")
    version: str = Field("1.0.0", description="系统版本")
    timezone: str = Field("Asia/Shanghai", description="时区")

class DataSourcesConfig(BaseModel):
    """数据源配置"""
    primary: str = Field("akshare", description="主要数据源")
    backup: str = Field("tushare", description="备用数据源")
    realtime: str = Field("sina", description="实时数据源")

class DataConfig(BaseModel):
    """数据配置"""
    sources: DataSourcesConfig = Field(default_factory=DataSourcesConfig)
    tushare_token: str = Field("", description="Tushare Token")

class DatabaseConfig(BaseModel):
    """数据库配置"""
    url: str = Field("sqlite:///stock_trading.db", description="数据库连接URL")
    echo: bool = Field(False, description="是否打印SQL语句")
    pool_size: int = Field(10, description="数据库连接池大小")

class TradeConfig(BaseModel):
    """交易配置"""
    commission_rate: float = Field(0.0003, description="手续费率")

class TrailingStopConfig(BaseModel):
    """追踪止损配置"""
    enabled: bool = Field(True, description="是否启用追踪止损")
    percentage: float = Field(0.02, description="追踪止损百分比")

class RiskManagementConfig(BaseModel):
    """风险管理配置"""
    max_position_size: float = Field(10000, description="最大仓位规模")
    max_positions: int = Field(5, description="最大持仓数量")
    stop_loss: float = Field(0.1, description="止损阈值")
    take_profit: float = Field(0.15, description="止盈阈值")
    risk_tolerance: float = Field(0.02, description="风险容忍度")
    trailing_stop: TrailingStopConfig = Field(default_factory=TrailingStopConfig)

class StockThresholdConfig(BaseModel):
    """个股阈值配置"""
    symbol: str = Field(..., description="股票代码")
    name: str = Field("", description="股票名称")
    rsi_overbought: float = Field(70.0, description="RSI超买阈值")
    rsi_oversold: float = Field(30.0, description="RSI超卖阈值")
    price_change_threshold: float = Field(0.05, description="价格变动阈值（5%）")
    volume_threshold: float = Field(2.0, description="成交量异常阈值（倍数）")
    macd_threshold: float = Field(0.1, description="MACD信号阈值")
    enabled: bool = Field(True, description="是否启用监控")
    
    @validator('rsi_overbought', allow_reuse=True)
    def validate_rsi_overbought(cls, v):
        if not 50 <= v <= 100:
            raise ValueError('RSI超买阈值应在50-100之间')
        return v
    
    @validator('rsi_oversold', allow_reuse=True)
    def validate_rsi_oversold(cls, v):
        if not 0 <= v <= 50:
            raise ValueError('RSI超卖阈值应在0-50之间')
        return v

class MonitoringConfig(BaseModel):
    """监控配置"""
    stocks: List[str] = Field(default_factory=lambda: ["000001.SZ", "600519.SH"], description="监控的股票列表（向后兼容）")
    stock_thresholds: List[StockThresholdConfig] = Field(default_factory=list, description="个股监控阈值配置")
    volatility_threshold: float = Field(0.03, description="波动性阈值")
    check_interval: int = Field(60, description="检查间隔（秒）")
    polling_interval: int = Field(30, description="轮询间隔（秒）")
    enable_auto_notification: bool = Field(True, description="是否启用自动通知")
    notification_cooldown: int = Field(300, description="通知冷却时间（秒）")
    # 向后兼容新增：历史数据长度（用于波动/均线等计算的窗口缓存）
    history_size: int = Field(120, description="历史数据记录长度（条）")
    
    @validator('check_interval', allow_reuse=True)
    def check_interval_positive(cls, v):
        if v <= 0:
            raise ValueError('检查间隔必须为正数')
        return v
    
    @validator('polling_interval', allow_reuse=True)
    def polling_interval_positive(cls, v):
        if v <= 0:
            raise ValueError('轮询间隔必须为正数')
        return v

    @validator('history_size', allow_reuse=True)
    def history_size_positive(cls, v):
        if v <= 0:
            raise ValueError('history_size 必须为正数')
        return v

class StrategyParamsConfig(BaseModel):
    """策略参数配置"""
    short_window: int = Field(10, description="短期窗口")
    long_window: int = Field(50, description="长期窗口")
    volume_multiple: float = Field(2.0, description="成交量倍数")

class PressureSupportStrategyConfig(BaseModel):
    """压力支撑策略配置"""
    enabled: bool = Field(True, description="是否启用策略")
    params: StrategyParamsConfig = Field(default_factory=StrategyParamsConfig)

class StrategiesConfig(BaseModel):
    """策略配置"""
    pressure_support_strategy: PressureSupportStrategyConfig = Field(default_factory=PressureSupportStrategyConfig)

class StrategyConfig(BaseModel):
    """单个策略配置（向后兼容）"""
    name: str = Field("pressure_support_strategy", description="策略名称")
    analysis_period: int = Field(6, description="分析周期")
    pressure_factor: float = Field(1.05, description="压力因子")
    support_factor: float = Field(0.95, description="支撑因子")
    volume_threshold: float = Field(1.5, description="成交量阈值")

class WeComConfig(BaseModel):
    """企业微信配置"""
    webhook_url: str = Field("", description="企业微信Webhook URL")

class NotificationConfig(BaseModel):
    """通知配置"""
    wecom_enabled: bool = Field(False, description="是否启用企业微信通知")
    wecom_webhook_url: str = Field("", description="企业微信Webhook URL")
    mention_all: bool = Field(False, description="是否@所有人")
    wecom: WeComConfig = Field(default_factory=WeComConfig)

    @validator('wecom_webhook_url', pre=True, always=True, allow_reuse=True)
    def check_wecom_webhook_url(cls, v, values):
        if values.get('wecom_enabled') and not v:
            raise ValueError("企业微信通知已启用，但未提供Webhook URL")
        return v

class N8nConfig(BaseModel):
    """n8n工作流配置"""
    enabled: bool = Field(False, description="是否启用n8n集成")
    base_url: str = Field("http://localhost:5678", description="n8n服务器地址")
    api_key: str = Field("", description="n8n API密钥")
    webhook_url: str = Field("", description="n8n Webhook URL")
    workflow_id: str = Field("", description="默认工作流ID")
    timeout: int = Field(30, description="请求超时时间（秒）")

class NewsRssConfig(BaseModel):
    """新闻RSS配置"""
    enabled: bool = Field(False, description="是否启用新闻RSS功能")
    rss_sources: List[str] = Field(default_factory=lambda: [
        "https://feeds.finance.yahoo.com/rss/2.0/headline",
        "http://rss.cnn.com/rss/money_latest.rss"
    ], description="RSS源URL列表")
    fetch_interval: int = Field(3600, description="抓取间隔（秒）")
    max_articles: int = Field(100, description="最大文章数量")
    keywords_filter: List[str] = Field(default_factory=list, description="关键词过滤器")
    enabled_sources: List[str] = Field(default_factory=list, description="启用的RSS源")
    storage_days: int = Field(30, description="新闻存储天数")

class AIAnalysisConfig(BaseModel):
    """AI分析配置"""
    enabled: bool = Field(False, description="是否启用AI分析功能")
    llm_provider: str = Field("deepseek", description="LLM提供商")
    model_name: str = Field("deepseek-chat", description="模型名称")
    api_key: str = Field("", description="API密钥")
    base_url: str = Field("", description="API基础URL")
    temperature: float = Field(0.7, description="生成温度")
    max_tokens: int = Field(2048, description="最大令牌数")
    timeout: int = Field(30, description="请求超时时间（秒）")
    analysis_interval: int = Field(1800, description="分析间隔（秒）")
    enable_sentiment_analysis: bool = Field(True, description="是否启用情感分析")
    enable_technical_analysis: bool = Field(True, description="是否启用技术分析")
    enable_news_analysis: bool = Field(True, description="是否启用新闻分析")

class WebConfig(BaseModel):
    """Web配置"""
    host: str = Field("127.0.0.1", description="Web服务器主机")
    port: int = Field(8080, description="Web服务器端口")
    n8n: N8nConfig = Field(default_factory=N8nConfig)

class Config(BaseModel):
    """主配置类"""
    system: SystemConfig = Field(default_factory=SystemConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    data_sources: Dict[str, Any] = Field(default_factory=dict, description="数据源配置（向后兼容）")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    trade: TradeConfig = Field(default_factory=TradeConfig)
    risk_management: RiskManagementConfig = Field(default_factory=RiskManagementConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    strategies: StrategiesConfig = Field(default_factory=StrategiesConfig)
    notification: NotificationConfig = Field(default_factory=NotificationConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    news_rss: NewsRssConfig = Field(default_factory=NewsRssConfig)
    ai_analysis: AIAnalysisConfig = Field(default_factory=AIAnalysisConfig)
    logging: Dict[str, Any] = Field(default_factory=dict, description="日志配置")
    backtest: Dict[str, Any] = Field(default_factory=dict, description="回测配置")
    cache: Dict[str, Any] = Field(default_factory=dict, description="缓存配置")

    class Config:
        validate_assignment = True

    # 向后兼容访问：config.risk -> config.risk_management
    @property
    def risk(self) -> RiskManagementConfig:
        return self.risk_management

    # 新增：支持以文件路径作为位置参数进行初始化，例如 Config('/tmp/config.yaml')
    def __init__(self, *args, **data):
        if len(args) > 1:
            raise TypeError(f"Config() 接受最多一个位置参数（配置文件路径），收到 {len(args)} 个")
        if len(args) == 1:
            file_arg = args[0]
            if isinstance(file_arg, (str, Path)):
                path = Path(file_arg)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        raw_config = yaml.safe_load(f) or {}
                    # 替换环境变量
                    _replace_env_vars(raw_config)
                    # 兼容旧键 risk -> risk_management
                    if isinstance(raw_config, dict) and 'risk' in raw_config and 'risk_management' not in raw_config:
                        raw_config['risk_management'] = raw_config.pop('risk')
                    # 兼容 backtest.commission -> trade.commission_rate
                    if isinstance(raw_config, dict) and 'trade' not in raw_config:
                        backtest = raw_config.get('backtest', {})
                        if isinstance(backtest, dict) and 'commission' in backtest:
                            raw_config['trade'] = {'commission_rate': backtest['commission']}
                    # 文件内容优先，仍允许通过关键字覆盖
                    data = {**raw_config, **data}
                except FileNotFoundError:
                    raise FileNotFoundError(f"配置文件不存在: {path}")
                except yaml.YAMLError as e:
                    raise ValueError(f"配置文件格式错误: {e}")
            else:
                raise TypeError("Config() 的位置参数仅支持 str 或 Path 类型作为配置文件路径")
        super().__init__(**data)

def load_config(config_file: str = "config.yaml") -> Config:
    project_root = Path(__file__).parent.parent.parent
    config_path = project_root / config_file
    
    # 加载环境变量
    load_dotenv(project_root / ".env")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f)
            
        # 替换环境变量
        _replace_env_vars(raw_config)
        
        # 兼容旧配置键 risk -> risk_management
        if isinstance(raw_config, dict) and 'risk' in raw_config and 'risk_management' not in raw_config:
            raw_config['risk_management'] = raw_config.pop('risk')

        # 兼容 backtest.commission -> trade.commission_rate
        if isinstance(raw_config, dict) and 'trade' not in raw_config:
            backtest = raw_config.get('backtest', {})
            if isinstance(backtest, dict) and 'commission' in backtest:
                raw_config['trade'] = {'commission_rate': backtest['commission']}
        
        return Config(**raw_config)
        
    except FileNotFoundError:
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"配置文件格式错误: {e}")

def _replace_env_vars(obj):
    """递归替换环境变量"""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                env_var = value[2:-1]
                obj[key] = os.getenv(env_var, value)
            elif isinstance(value, (dict, list)):
                _replace_env_vars(value)
    elif isinstance(obj, list):
        for item in obj:
            _replace_env_vars(item)

class ConfigManager:
    """通用配置管理器
    - 供示例与Web端统一调用
    - 兼容测试中对 config.yaml 与 .env 的读取/保存
    - 为需要dict的轻量消费者提供 get_config()
    """
    def __init__(self, config_file: Optional[Union[Path, str]] = None, env_file: Optional[Union[Path, str]] = None):
        self.config_file: Optional[Path] = Path(config_file) if config_file else None
        self.env_file: Optional[Path] = Path(env_file) if env_file else None

    def is_enabled(self) -> bool:
        # 只要任一文件路径被设置，则认为启用文件读写/封装格式
        return bool(self.config_file or self.env_file)

    def _project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    def load_config(self) -> Dict[str, Any]:
        """优先从指定文件读取；否则返回当前内存配置"""
        try:
            if self.config_file and self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
        except Exception:
            pass
        # 回退到内存 config
        return config.model_dump()

    def save_config(self, cfg: Dict[str, Any]):
        """保存配置到指定文件；未指定时落盘到项目根目录的 CONFIG_FILE"""
        if not self.config_file:
            self.config_file = self._project_root() / CONFIG_FILE
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump(cfg, f, default_flow_style=False, allow_unicode=True)

    def load_env(self) -> Dict[str, str]:
        result: Dict[str, str] = {}
        if not self.env_file or not self.env_file.exists():
            return result
        try:
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        k, v = line.split('=', 1)
                        result[k.strip()] = v.strip()
        except Exception:
            return {}
        return result

    def save_env(self, env: Dict[str, Any]):
        """保存 .env 键值对"""
        if not self.env_file:
            self.env_file = self._project_root() / '.env'
        self.env_file.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        for k, v in env.items():
            if v is None:
                v = ''
            lines.append(f"{k}={v}")
        with open(self.env_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines) + "\n")

    def get_config(self) -> Dict[str, Any]:
        """为轻量dict消费者提供通用配置映射"""
        data_dict = self.load_config()
        tushare_token = ''
        try:
            if isinstance(data_dict, dict):
                tushare_token = (data_dict.get('data') or {}).get('tushare_token', '') or ''
        except Exception:
            tushare_token = ''
        return {
            'tushare_token': tushare_token,
            'default_history_days': 250,
            'min_data_points': 30,
        }

# 配置文件路径常量
CONFIG_FILE = "config.yaml"

# 全局配置实例
config = load_config()