#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化股票交易系统

一个基于Python的量化股票交易系统，包含以下功能：
1. 股票波动监控和预警
2. 基于压力位支撑位的交易策略
3. 企业微信消息通知
4. 风险管理和交易执行

Author: Quant Team
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Quant Team"
__description__ = "量化股票交易系统"

# 导出主要类
from .core.engine import TradingEngine
from .core.config import Config
from .core.monitor import StockMonitor
from .data.data_provider import DataManager
from .strategy.pressure_support_strategy import PressureSupportStrategy
from .notification.wecom_notifier import NotificationManager
from .models.models import (
    TradeSignal, MarketAlert, StockData, 
    TradeAction, AlertLevel, OrderStatus
)

__all__ = [
    'TradingEngine',
    'Config', 
    'StockMonitor',
    'DataManager',
    'PressureSupportStrategy',
    'NotificationManager',
    'TradeSignal',
    'MarketAlert', 
    'StockData',
    'TradeAction',
    'AlertLevel',
    'OrderStatus'
]