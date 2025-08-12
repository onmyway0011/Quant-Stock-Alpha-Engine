#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web界面模块

提供统一的配置管理界面
"""

__version__ = "1.0.0"
__author__ = "Quant Team"

# 导出主要类
from .config_server import ConfigServer, ConfigManager

__all__ = [
    'ConfigServer',
    'ConfigManager'
]