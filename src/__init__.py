#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化股票交易系统

包级初始化尽量保持轻量，以避免导入时触发重型依赖。
需要具体组件时请从相应子模块导入，例如：
- from src.core.engine import TradingEngine
- from src.core.config import Config
- from src.core.monitor import StockMonitor
- from src.data.data_provider import DataManager
- from src.strategy.pressure_support_strategy import PressureSupportStrategy
- from src.notification.wecom_notifier import NotificationManager
- from src.models.models import TradeSignal, MarketAlert, StockData, TradeAction, AlertLevel, OrderStatus

Author: Quant Team
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Quant Team"
__description__ = "量化股票交易系统"

__all__ = []