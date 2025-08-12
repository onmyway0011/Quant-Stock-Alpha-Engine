#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票监控模块

负责监控股票波动并生成预警
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from collections import defaultdict, deque

from ..models.models import StockData, MarketAlert, AlertLevel
from ..utils.logger import LoggerMixin, log_market_alert, log_system_status
from ..data.data_provider import DataManager


class VolatilityCalculator:
    """波动率计算器"""
    
    @staticmethod
    def calculate_price_volatility(prices: List[float], window: int = 20) -> float:
        """计算价格波动率
        
        Args:
            prices: 价格序列
            window: 计算窗口
            
        Returns:
            波动率
        """
        if len(prices) < 2:
            return 0.0
            
        # 计算收益率
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)
        
        if len(returns) < 2:
            return 0.0
            
        # 计算标准差（波动率）
        return float(np.std(returns[-window:]))
    
    @staticmethod
    def calculate_volume_volatility(volumes: List[int], window: int = 20) -> float:
        """计算成交量波动率"""
        if len(volumes) < 2:
            return 0.0
            
        recent_volumes = volumes[-window:]
        if len(recent_volumes) < 2:
            return 0.0
            
        avg_volume = np.mean(recent_volumes)
        if avg_volume == 0:
            return 0.0
            
        return float(np.std(recent_volumes) / avg_volume)
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """计算RSI指标"""
        if len(prices) < period + 1:
            return 50.0
            
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)


class AlertQueue:
    """预警队列"""
    
    def __init__(self, max_size: int = 1000):
        self.queue = deque(maxlen=max_size)
        self.processed_alerts = set()
        
    def add_alert(self, alert: MarketAlert) -> bool:
        """添加预警
        
        Args:
            alert: 市场预警对象
            
        Returns:
            是否成功添加（去重）
        """
        # 生成预警唯一标识
        alert_id = f"{alert.symbol}_{alert.alert_type}_{alert.timestamp.strftime('%Y%m%d_%H%M')}"
        
        if alert_id not in self.processed_alerts:
            self.queue.append(alert)
            self.processed_alerts.add(alert_id)
            return True
        return False
    
    def get_alerts(self, count: int = None) -> List[MarketAlert]:
        """获取预警
        
        Args:
            count: 获取数量，None表示全部
            
        Returns:
            预警列表
        """
        if count is None:
            return list(self.queue)
        else:
            return list(self.queue)[-count:]
    
    def clear_old_alerts(self, hours: int = 24):
        """清理旧预警
        
        Args:
            hours: 保留小时数
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # 清理队列中的旧预警
        while self.queue and self.queue[0].timestamp < cutoff_time:
            self.queue.popleft()
        
        # 清理已处理预警集合（简单清理，实际应该更精确）
        if len(self.processed_alerts) > 10000:
            self.processed_alerts.clear()


class StockMonitor(LoggerMixin):
    """股票监控器"""
    
    def __init__(self, config, data_manager: DataManager):
        self.config = config
        self.data_manager = data_manager
        self.alert_queue = AlertQueue()
        
        # 监控配置
        self.symbols = config.monitoring.stocks
        self.volatility_threshold = config.monitoring.volatility_threshold
        self.check_interval = config.monitoring.check_interval
        
        # 数据缓存
        self.price_history = defaultdict(lambda: deque(maxlen=100))
        self.volume_history = defaultdict(lambda: deque(maxlen=100))
        self.last_prices = {}
        
        # 监控状态
        self.is_running = False
        self.monitor_task = None
        
        # 回调函数
        self.alert_callbacks: List[Callable[[MarketAlert], None]] = []
        
    def add_alert_callback(self, callback: Callable[[MarketAlert], None]):
        """添加预警回调函数
        
        Args:
            callback: 预警回调函数
        """
        self.alert_callbacks.append(callback)
    
    async def start_monitoring(self):
        """开始监控"""
        if self.is_running:
            self.logger.warning("监控已在运行中")
            return
            
        self.is_running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        
        log_system_status("StockMonitor", "running", f"监控{len(self.symbols)}只股票")
        self.logger.info(f"开始监控股票: {self.symbols}")
    
    async def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        log_system_status("StockMonitor", "stopped")
        self.logger.info("股票监控已停止")
    
    async def _monitor_loop(self):
        """监控主循环"""
        while self.is_running:
            try:
                await self._check_stocks()
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"监控循环异常: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_stocks(self):
        """检查股票"""
        try:
            # 获取实时数据
            stock_data = await self.data_manager.get_realtime_data(self.symbols)
            
            for symbol, data in stock_data.items():
                await self._analyze_stock(symbol, data)
                
            # 清理旧预警
            self.alert_queue.clear_old_alerts()
            
        except Exception as e:
            self.logger.error(f"检查股票数据失败: {e}")
    
    async def _analyze_stock(self, symbol: str, data: StockData):
        """分析单只股票
        
        Args:
            symbol: 股票代码
            data: 股票数据
        """
        try:
            # 更新历史数据
            self.price_history[symbol].append(data.current_price)
            self.volume_history[symbol].append(data.volume)
            
            # 检查各种预警条件
            await self._check_price_volatility(symbol, data)
            await self._check_volume_anomaly(symbol, data)
            await self._check_price_change(symbol, data)
            await self._check_technical_indicators(symbol, data)
            
            # 更新最后价格
            self.last_prices[symbol] = data.current_price
            
        except Exception as e:
            self.logger.error(f"分析股票{symbol}失败: {e}")
    
    async def _check_price_volatility(self, symbol: str, data: StockData):
        """检查价格波动率"""
        prices = list(self.price_history[symbol])
        if len(prices) < 10:
            return
            
        volatility = VolatilityCalculator.calculate_price_volatility(prices)
        
        if volatility > self.volatility_threshold:
            alert = MarketAlert(
                symbol=symbol,
                alert_type="price_volatility",
                level=self._get_volatility_alert_level(volatility),
                message=f"价格波动率异常: {volatility:.2%}",
                current_value=volatility,
                threshold=self.volatility_threshold,
                timestamp=datetime.now()
            )
            
            await self._trigger_alert(alert)
    
    async def _check_volume_anomaly(self, symbol: str, data: StockData):
        """检查成交量异常"""
        volumes = list(self.volume_history[symbol])
        if len(volumes) < 10:
            return
            
        avg_volume = np.mean(volumes[:-1])  # 排除当前成交量
        current_volume = data.volume
        
        # 成交量异常倍数
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        
        if volume_ratio > 3.0:  # 成交量超过平均值3倍
            alert = MarketAlert(
                symbol=symbol,
                alert_type="volume_anomaly",
                level=AlertLevel.MEDIUM if volume_ratio < 5.0 else AlertLevel.HIGH,
                message=f"成交量异常放大: {volume_ratio:.1f}倍",
                current_value=current_volume,
                threshold=avg_volume * 3,
                timestamp=datetime.now()
            )
            
            await self._trigger_alert(alert)
    
    async def _check_price_change(self, symbol: str, data: StockData):
        """检查价格变化"""
        change_percent = abs(data.change_percent)
        
        # 价格变化预警阈值
        if change_percent > 5.0:  # 涨跌幅超过5%
            level = AlertLevel.MEDIUM
            if change_percent > 8.0:
                level = AlertLevel.HIGH
            elif change_percent > 10.0:
                level = AlertLevel.CRITICAL
                
            alert = MarketAlert(
                symbol=symbol,
                alert_type="price_change",
                level=level,
                message=f"价格变化异常: {data.change_percent:+.2f}%",
                current_value=change_percent,
                threshold=5.0,
                timestamp=datetime.now()
            )
            
            await self._trigger_alert(alert)
    
    async def _check_technical_indicators(self, symbol: str, data: StockData):
        """检查技术指标"""
        prices = list(self.price_history[symbol])
        if len(prices) < 20:
            return
            
        # RSI指标
        rsi = VolatilityCalculator.calculate_rsi(prices)
        
        if rsi > 80:  # 超买
            alert = MarketAlert(
                symbol=symbol,
                alert_type="rsi_overbought",
                level=AlertLevel.MEDIUM,
                message=f"RSI超买信号: {rsi:.1f}",
                current_value=rsi,
                threshold=80.0,
                timestamp=datetime.now()
            )
            await self._trigger_alert(alert)
            
        elif rsi < 20:  # 超卖
            alert = MarketAlert(
                symbol=symbol,
                alert_type="rsi_oversold",
                level=AlertLevel.MEDIUM,
                message=f"RSI超卖信号: {rsi:.1f}",
                current_value=rsi,
                threshold=20.0,
                timestamp=datetime.now()
            )
            await self._trigger_alert(alert)
    
    def _get_volatility_alert_level(self, volatility: float) -> AlertLevel:
        """根据波动率获取预警级别"""
        if volatility > self.volatility_threshold * 3:
            return AlertLevel.CRITICAL
        elif volatility > self.volatility_threshold * 2:
            return AlertLevel.HIGH
        else:
            return AlertLevel.MEDIUM
    
    async def _trigger_alert(self, alert: MarketAlert):
        """触发预警
        
        Args:
            alert: 市场预警
        """
        # 添加到预警队列
        if self.alert_queue.add_alert(alert):
            # 记录预警日志
            log_market_alert(
                alert.symbol, 
                alert.current_value, 
                alert.current_value, 
                alert.threshold
            )
            
            # 调用回调函数
            for callback in self.alert_callbacks:
                try:
                    await callback(alert) if asyncio.iscoroutinefunction(callback) else callback(alert)
                except Exception as e:
                    self.logger.error(f"预警回调函数执行失败: {e}")
    
    def get_recent_alerts(self, hours: int = 24) -> List[MarketAlert]:
        """获取最近的预警
        
        Args:
            hours: 小时数
            
        Returns:
            预警列表
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        alerts = self.alert_queue.get_alerts()
        
        return [alert for alert in alerts if alert.timestamp >= cutoff_time]
    
    def get_stock_status(self, symbol: str) -> Dict:
        """获取股票状态
        
        Args:
            symbol: 股票代码
            
        Returns:
            股票状态信息
        """
        prices = list(self.price_history[symbol])
        volumes = list(self.volume_history[symbol])
        
        if not prices:
            return {}
            
        current_price = prices[-1] if prices else 0
        volatility = VolatilityCalculator.calculate_price_volatility(prices)
        rsi = VolatilityCalculator.calculate_rsi(prices)
        
        return {
            'symbol': symbol,
            'current_price': current_price,
            'volatility': volatility,
            'rsi': rsi,
            'price_history_count': len(prices),
            'volume_history_count': len(volumes),
            'last_update': datetime.now().isoformat()
        }
    
    def get_monitoring_summary(self) -> Dict:
        """获取监控摘要
        
        Returns:
            监控摘要信息
        """
        total_alerts = len(self.alert_queue.get_alerts())
        recent_alerts = len(self.get_recent_alerts(1))  # 最近1小时
        
        return {
            'is_running': self.is_running,
            'monitored_stocks': len(self.symbols),
            'total_alerts': total_alerts,
            'recent_alerts': recent_alerts,
            'check_interval': self.check_interval,
            'volatility_threshold': self.volatility_threshold,
            'last_check': datetime.now().isoformat()
        }