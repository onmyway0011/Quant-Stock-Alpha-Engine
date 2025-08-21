#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化测试模块

提供完整的系统功能测试覆盖
"""

__version__ = "1.0.0"
__author__ = "Quant Team"

# 测试包初始化，不自动导入测试类避免导入错误
__all__ = [
    'TestPydanticConfig',
    'TestDataProvider',
    'TestStrategy',
    'TestMonitor',
    'TestNotification',
    'TestEngine',
    'TestWebInterface',
    'TestIntegration'
]