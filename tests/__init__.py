#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化测试模块

提供完整的系统功能测试覆盖
"""

__version__ = "1.0.0"
__author__ = "Quant Team"

# 导出主要测试类
from .test_config import TestConfig
from .test_data_provider import TestDataProvider
from .test_strategy import TestStrategy
from .test_monitor import TestMonitor
from .test_notification import TestNotification
from .test_engine import TestEngine
from .test_web import TestWebInterface
from .test_integration import TestIntegration

__all__ = [
    'TestConfig',
    'TestDataProvider',
    'TestStrategy',
    'TestMonitor',
    'TestNotification',
    'TestEngine',
    'TestWebInterface',
    'TestIntegration'
]