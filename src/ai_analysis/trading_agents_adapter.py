#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TradingAgents-CN适配器

集成TradingAgents-CN多智能体框架
参考项目: https://github.com/hsliuping/TradingAgents-CN
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from pathlib import Path

try:
    # 尝试导入TradingAgents-CN
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.default_config import DEFAULT_CONFIG
    TRADINGAGENTS_AVAILABLE = True
except ImportError:
    TRADINGAGENTS_AVAILABLE = False
    print("警告: TradingAgents-CN未安装，AI分析功能将受限")

from ...utils.logger import get_logger
from ...models.models import StockData


@dataclass
class AIAnalysisResult:
    """AI分析结果"""
    symbol: str
    analysis_date: str
    decision: Dict[str, Any]
    agent_reports: Dict[str, Any]
    confidence: float
    risk_score: float
    reasoning: str
    recommendations: List[str]
    timestamp: datetime


class TradingAgentsAdapter:
    """TradingAgents-CN适配器"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.logger = get_logger(self.__class__.__name__)
        
        # 检查TradingAgents-CN可用性
        if not TRADINGAGENTS_AVAILABLE:
            self.logger.error("TradingAgents-CN未安装，请先安装: pip install tradingagents-cn")
            self.trading_graph = None
            return
        
        # 初始化TradingAgents配置
        self.ta_config = self._init_trading_agents_config()
        
        # 创建TradingAgents实例
        try:
            self.trading_graph = TradingAgentsGraph(
                debug=self.config.get('debug', False),
                config=self.ta_config
            )
            self.logger.info("TradingAgents-CN初始化成功")
        except Exception as e:
            self.logger.error(f"TradingAgents-CN初始化失败: {e}")
            self.trading_graph = None
    
    def _init_trading_agents_config(self) -> Dict:
        """初始化TradingAgents配置"""
        # 基础配置
        ta_config = DEFAULT_CONFIG.copy() if TRADINGAGENTS_AVAILABLE else {}
        
        # LLM提供商配置
        llm_provider = self.config.get('llm_provider', 'dashscope')
        
        if llm_provider == 'dashscope':
            # 阿里百炼配置
            ta_config.update({
                'llm_provider': 'dashscope',
                'deep_think_llm': self.config.get('deep_think_llm', 'qwen-plus'),
                'quick_think_llm': self.config.get('quick_think_llm', 'qwen-turbo'),
                'dashscope_api_key': self.config.get('dashscope_api_key', ''),
            })
        elif llm_provider == 'deepseek':
            # DeepSeek配置
            ta_config.update({
                'llm_provider': 'deepseek',
                'deep_think_llm': 'deepseek-chat',
                'quick_think_llm': 'deepseek-chat',
                'deepseek_api_key': self.config.get('deepseek_api_key', ''),
            })
        elif llm_provider == 'google':
            # Google AI配置
            ta_config.update({
                'llm_provider': 'google',
                'deep_think_llm': 'gemini-2.0-flash-exp',
                'quick_think_llm': 'gemini-1.5-flash',
                'google_api_key': self.config.get('google_api_key', ''),
            })
        elif llm_provider == 'openrouter':
            # OpenRouter配置
            ta_config.update({
                'llm_provider': 'openrouter',
                'deep_think_llm': self.config.get('deep_think_llm', 'anthropic/claude-3.5-sonnet'),
                'quick_think_llm': self.config.get('quick_think_llm', 'openai/gpt-4o-mini'),
                'openrouter_api_key': self.config.get('openrouter_api_key', ''),
            })
        
        # 其他配置
        ta_config.update({
            'max_debate_rounds': self.config.get('max_debate_rounds', 2),
            'online_tools': self.config.get('online_tools', True),
            'enable_news_analysis': self.config.get('enable_news_analysis', True),
            'enable_social_sentiment': self.config.get('enable_social_sentiment', False),
            'risk_tolerance': self.config.get('risk_tolerance', 'medium'),
            'analysis_depth': self.config.get('analysis_depth', 'comprehensive')
        })
        
        return ta_config
    
    async def analyze_stock(self, symbol: str, analysis_date: str = None) -> Optional[AIAnalysisResult]:
        """分析股票
        
        Args:
            symbol: 股票代码
            analysis_date: 分析日期，格式YYYY-MM-DD
            
        Returns:
            AI分析结果
        """
        if not self.trading_graph:
            self.logger.error("TradingAgents未初始化，无法进行AI分析")
            return None
        
        try:
            # 设置分析日期
            if not analysis_date:
                analysis_date = datetime.now().strftime('%Y-%m-%d')
            
            self.logger.info(f"开始AI分析股票: {symbol}, 日期: {analysis_date}")
            
            # 调用TradingAgents进行分析
            state, decision = await asyncio.to_thread(
                self.trading_graph.propagate, symbol, analysis_date
            )
            
            if not decision:
                self.logger.warning(f"AI分析{symbol}未返回决策结果")
                return None
            
            # 解析分析结果
            analysis_result = self._parse_analysis_result(
                symbol, analysis_date, state, decision
            )
            
            self.logger.info(f"AI分析{symbol}完成，决策: {decision.get('action', 'HOLD')}")
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"AI分析{symbol}失败: {e}")
            return None
    
    def _parse_analysis_result(self, symbol: str, analysis_date: str, 
                             state: Dict, decision: Dict) -> AIAnalysisResult:
        """解析分析结果
        
        Args:
            symbol: 股票代码
            analysis_date: 分析日期
            state: TradingAgents状态
            decision: 决策结果
            
        Returns:
            AI分析结果
        """
        # 提取智能体报告
        agent_reports = {
            'fundamental_analyst': state.get('fundamental_analysis', {}),
            'technical_analyst': state.get('technical_analysis', {}),
            'news_analyst': state.get('news_analysis', {}),
            'sentiment_analyst': state.get('sentiment_analysis', {}),
            'bull_researcher': state.get('bull_research', {}),
            'bear_researcher': state.get('bear_research', {}),
            'trader': state.get('trader_decision', {}),
            'risk_manager': state.get('risk_assessment', {})
        }
        
        # 提取决策信息
        action = decision.get('action', 'HOLD')
        confidence = decision.get('confidence', 0.5)
        risk_score = decision.get('risk_score', 0.5)
        reasoning = decision.get('reasoning', '无详细推理信息')
        
        # 生成建议
        recommendations = self._generate_recommendations(decision, agent_reports)
        
        return AIAnalysisResult(
            symbol=symbol,
            analysis_date=analysis_date,
            decision=decision,
            agent_reports=agent_reports,
            confidence=confidence,
            risk_score=risk_score,
            reasoning=reasoning,
            recommendations=recommendations,
            timestamp=datetime.now()
        )
    
    def _generate_recommendations(self, decision: Dict, agent_reports: Dict) -> List[str]:
        """生成投资建议
        
        Args:
            decision: 决策结果
            agent_reports: 智能体报告
            
        Returns:
            建议列表
        """
        recommendations = []
        
        action = decision.get('action', 'HOLD')
        confidence = decision.get('confidence', 0.5)
        risk_score = decision.get('risk_score', 0.5)
        
        # 基于决策的建议
        if action == 'BUY':
            if confidence >= 0.8:
                recommendations.append("AI强烈建议买入，多个智能体达成一致")
            elif confidence >= 0.6:
                recommendations.append("AI建议买入，但需注意风险控制")
            else:
                recommendations.append("AI倾向买入，建议小仓位试探")
        elif action == 'SELL':
            if confidence >= 0.8:
                recommendations.append("AI强烈建议卖出，建议及时止损")
            elif confidence >= 0.6:
                recommendations.append("AI建议卖出，建议减仓观望")
            else:
                recommendations.append("AI倾向卖出，建议谨慎操作")
        else:
            recommendations.append("AI建议持有观望，等待更明确信号")
        
        # 基于风险评分的建议
        if risk_score >= 0.7:
            recommendations.append("风险评分较高，建议严格控制仓位")
        elif risk_score >= 0.4:
            recommendations.append("风险评分中等，建议适度配置")
        else:
            recommendations.append("风险评分较低，可考虑增加配置")
        
        # 基于智能体分析的建议
        fundamental = agent_reports.get('fundamental_analyst', {})
        if fundamental.get('recommendation') == 'BUY':
            recommendations.append("基本面分析师看好公司基本面")
        elif fundamental.get('recommendation') == 'SELL':
            recommendations.append("基本面分析师对公司基本面担忧")
        
        technical = agent_reports.get('technical_analyst', {})
        if technical.get('trend') == 'BULLISH':
            recommendations.append("技术面分析显示上涨趋势")
        elif technical.get('trend') == 'BEARISH':
            recommendations.append("技术面分析显示下跌趋势")
        
        news = agent_reports.get('news_analyst', {})
        if news.get('sentiment') == 'POSITIVE':
            recommendations.append("新闻面偏向积极")
        elif news.get('sentiment') == 'NEGATIVE':
            recommendations.append("新闻面偏向消极")
        
        return recommendations
    
    async def batch_analyze(self, symbols: List[str], 
                          analysis_date: str = None,
                          max_concurrent: int = 3) -> Dict[str, AIAnalysisResult]:
        """批量分析股票
        
        Args:
            symbols: 股票代码列表
            analysis_date: 分析日期
            max_concurrent: 最大并发数
            
        Returns:
            分析结果字典
        """
        if not self.trading_graph:
            self.logger.error("TradingAgents未初始化，无法进行批量AI分析")
            return {}
        
        results = {}
        
        # 创建信号量限制并发数
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_single(symbol):
            async with semaphore:
                return symbol, await self.analyze_stock(symbol, analysis_date)
        
        # 并发分析
        tasks = [analyze_single(symbol) for symbol in symbols]
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        for result in completed_tasks:
            if isinstance(result, Exception):
                self.logger.error(f"批量AI分析时发生错误: {result}")
                continue
            
            symbol, analysis = result
            if analysis:
                results[symbol] = analysis
        
        self.logger.info(f"批量AI分析完成，成功分析{len(results)}/{len(symbols)}只股票")
        return results
    
    def get_agent_capabilities(self) -> Dict[str, List[str]]:
        """获取智能体能力描述
        
        Returns:
            智能体能力字典
        """
        return {
            'fundamental_analyst': [
                '分析公司财务报表',
                '评估公司估值水平',
                '研究行业发展趋势',
                '分析竞争优势'
            ],
            'technical_analyst': [
                '技术指标分析',
                '图表形态识别',
                '趋势分析',
                '支撑阻力位判断'
            ],
            'news_analyst': [
                '新闻事件分析',
                '政策影响评估',
                '市场热点追踪',
                '舆情监控'
            ],
            'sentiment_analyst': [
                '社交媒体情绪分析',
                '投资者情绪指标',
                '市场恐慌贪婪指数',
                '资金流向分析'
            ],
            'bull_researcher': [
                '寻找看涨理由',
                '积极因素挖掘',
                '上涨催化剂分析',
                '乐观情景预测'
            ],
            'bear_researcher': [
                '识别看跌风险',
                '消极因素评估',
                '下跌风险预警',
                '悲观情景分析'
            ],
            'trader': [
                '综合决策制定',
                '交易时机把握',
                '仓位管理建议',
                '执行策略优化'
            ],
            'risk_manager': [
                '风险评估',
                '止损止盈设置',
                '组合风险控制',
                '压力测试'
            ]
        }
    
    def get_supported_markets(self) -> List[str]:
        """获取支持的市场
        
        Returns:
            支持的市场列表
        """
        return ['A股', '港股', '美股']
    
    def get_analysis_metrics(self) -> Dict[str, str]:
        """获取分析指标说明
        
        Returns:
            分析指标字典
        """
        return {
            'confidence': '决策信心度，范围0-1，越高表示越确信',
            'risk_score': '风险评分，范围0-1，越高表示风险越大',
            'action': '推荐动作，BUY/SELL/HOLD',
            'reasoning': '详细推理过程和依据',
            'agent_consensus': '智能体共识度，衡量意见一致性'
        }
    
    async def close(self):
        """关闭连接"""
        # TradingAgents-CN通常不需要显式关闭
        self.logger.info("TradingAgents适配器已关闭")


class MockTradingAgentsAdapter(TradingAgentsAdapter):
    """模拟TradingAgents适配器（用于测试）"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.logger = get_logger(self.__class__.__name__)
        self.trading_graph = "mock"  # 模拟实例
        self.logger.info("模拟TradingAgents适配器初始化完成")
    
    async def analyze_stock(self, symbol: str, analysis_date: str = None) -> Optional[AIAnalysisResult]:
        """模拟股票分析"""
        if not analysis_date:
            analysis_date = datetime.now().strftime('%Y-%m-%d')
        
        # 模拟分析结果
        import random
        
        actions = ['BUY', 'SELL', 'HOLD']
        action = random.choice(actions)
        confidence = random.uniform(0.3, 0.9)
        risk_score = random.uniform(0.2, 0.8)
        
        decision = {
            'action': action,
            'confidence': confidence,
            'risk_score': risk_score,
            'reasoning': f'基于模拟分析，{symbol}的综合评分为{confidence:.2f}，风险评分为{risk_score:.2f}'
        }
        
        agent_reports = {
            'fundamental_analyst': {'recommendation': action, 'score': confidence},
            'technical_analyst': {'trend': 'BULLISH' if action == 'BUY' else 'BEARISH' if action == 'SELL' else 'NEUTRAL'},
            'news_analyst': {'sentiment': 'POSITIVE' if action == 'BUY' else 'NEGATIVE' if action == 'SELL' else 'NEUTRAL'},
            'sentiment_analyst': {'market_sentiment': random.uniform(0.3, 0.7)}
        }
        
        recommendations = self._generate_recommendations(decision, agent_reports)
        
        return AIAnalysisResult(
            symbol=symbol,
            analysis_date=analysis_date,
            decision=decision,
            agent_reports=agent_reports,
            confidence=confidence,
            risk_score=risk_score,
            reasoning=decision['reasoning'],
            recommendations=recommendations,
            timestamp=datetime.now()
        )
        
        await asyncio.sleep(0.1)  # 模拟分析时间