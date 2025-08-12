#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI分析模块

集成TradingAgents-CN多智能体框架，提供AI驱动的股票分析功能
"""

__version__ = "1.0.0"
__author__ = "Quant Team"

from .trading_agents_adapter import TradingAgentsAdapter
from .multi_agent_analyzer import MultiAgentAnalyzer
from .llm_providers import LLMProviderManager
from .report_generator import AIReportGenerator

__all__ = [
    'TradingAgentsAdapter',
    'MultiAgentAnalyzer',
    'LLMProviderManager',
    'AIReportGenerator'
]