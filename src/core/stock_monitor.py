#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票监控服务

实现股票实时监控、技术指标计算和阈值检测
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ..models.models import MarketAlert, AlertLevel
from ..utils.logger import LoggerMixin
from ..data.data_provider import DataManager
from ..notification.wecom_notifier import NotificationManager
from .config import config, StockThresholdConfig


class AlertType(Enum):
    """预警类型"""
    RSI_OVERBOUGHT = "rsi_overbought"
    RSI_OVERSOLD = "rsi_oversold"
    PRICE_SURGE = "price_surge"
    PRICE_DROP = "price_drop"
    VOLUME_SPIKE = "volume_spike"
    MACD_SIGNAL = "macd_signal"


@dataclass
class StockAlert:
    """股票预警信息"""
    symbol: str
    name: str
    alert_type: AlertType
    current_value: float
    threshold: float
    message: str
    timestamp: datetime
    level: AlertLevel


class TechnicalIndicators:
    """技术指标计算器"""
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
        """计算RSI指标"""
        if len(prices) < period + 1:
            return 50.0  # 默认中性值
        
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
    
    @staticmethod
    def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float, float]:
        """计算MACD指标"""
        if len(prices) < slow:
            return 0.0, 0.0, 0.0
        
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        
        return (
            float(macd_line.iloc[-1]) if not pd.isna(macd_line.iloc[-1]) else 0.0,
            float(signal_line.iloc[-1]) if not pd.isna(signal_line.iloc[-1]) else 0.0,
            float(histogram.iloc[-1]) if not pd.isna(histogram.iloc[-1]) else 0.0
        )
    
    @staticmethod
    def calculate_price_change(current_price: float, previous_price: float) -> float:
        """计算价格变动百分比"""
        if previous_price == 0:
            return 0.0
        return (current_price - previous_price) / previous_price
    
    @staticmethod
    def calculate_volume_ratio(current_volume: float, avg_volume: float) -> float:
        """计算成交量比率"""
        if avg_volume == 0:
            return 1.0
        return current_volume / avg_volume


class StockMonitorService(LoggerMixin):
    """股票监控服务"""
    
    def __init__(self, data_manager: DataManager, notification_manager: NotificationManager):
        self.data_manager = data_manager
        self.notification_manager = notification_manager
        self.is_running = False
        self.last_notifications = {}  # 记录最后通知时间，避免频繁通知
        self.indicators = TechnicalIndicators()
        
    async def start_monitoring(self):
        """开始监控"""
        if self.is_running:
            self.logger.warning("监控服务已在运行中")
            return
        
        self.is_running = True
        self.logger.info("股票监控服务启动")
        
        try:
            while self.is_running:
                await self._monitor_cycle()
                await asyncio.sleep(config.monitoring.polling_interval)
        except Exception as e:
            self.logger.error(f"监控服务异常: {e}")
        finally:
            self.is_running = False
            self.logger.info("股票监控服务停止")
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        self.logger.info("正在停止股票监控服务...")
    
    async def _monitor_cycle(self):
        """单次监控循环"""
        try:
            # 获取配置的监控股票
            stock_configs = config.monitoring.stock_thresholds
            if not stock_configs:
                # 如果没有配置个股阈值，使用默认股票列表
                stock_configs = [
                    StockThresholdConfig(symbol=symbol) 
                    for symbol in config.monitoring.stocks
                ]
            
            # 监控每只股票
            for stock_config in stock_configs:
                if not stock_config.enabled:
                    continue
                
                try:
                    alerts = await self._check_stock_alerts(stock_config)
                    for alert in alerts:
                        await self._handle_alert(alert)
                except Exception as e:
                    self.logger.error(f"监控股票 {stock_config.symbol} 时发生错误: {e}")
                    
        except Exception as e:
            self.logger.error(f"监控循环异常: {e}")
    
    async def _check_stock_alerts(self, stock_config: StockThresholdConfig) -> List[StockAlert]:
        """检查单只股票的预警"""
        alerts = []
        symbol = stock_config.symbol
        
        try:
            # 获取实时数据
            realtime_data = await self.data_manager.get_realtime_data([symbol])
            if symbol not in realtime_data:
                self.logger.warning(f"无法获取 {symbol} 的实时数据")
                return alerts
            
            stock_data = realtime_data[symbol]
            current_price = stock_data.current_price
            current_volume = stock_data.volume
            
            # 获取历史数据用于计算技术指标
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
            historical_data = await self.data_manager.get_historical_data(symbol, start_date, end_date)
            
            if historical_data.empty:
                self.logger.warning(f"无法获取 {symbol} 的历史数据")
                return alerts
            
            # 标准化数据列名
            historical_data = self._standardize_dataframe(historical_data)
            
            # 计算技术指标
            rsi = self.indicators.calculate_rsi(historical_data['close'])
            macd, signal, histogram = self.indicators.calculate_macd(historical_data['close'])
            
            # 计算价格变动
            if len(historical_data) >= 2:
                previous_price = historical_data['close'].iloc[-2]
                price_change = self.indicators.calculate_price_change(current_price, previous_price)
            else:
                price_change = 0.0
            
            # 计算成交量比率
            avg_volume = historical_data['volume'].tail(20).mean()
            volume_ratio = self.indicators.calculate_volume_ratio(current_volume, avg_volume)
            
            # 检查各种预警条件
            alerts.extend(self._check_rsi_alerts(stock_config, rsi))
            alerts.extend(self._check_price_alerts(stock_config, price_change))
            alerts.extend(self._check_volume_alerts(stock_config, volume_ratio))
            alerts.extend(self._check_macd_alerts(stock_config, histogram))
            
        except Exception as e:
            self.logger.error(f"检查股票 {symbol} 预警时发生错误: {e}")
        
        return alerts
    
    def _check_rsi_alerts(self, stock_config: StockThresholdConfig, rsi: float) -> List[StockAlert]:
        """检查RSI预警"""
        alerts = []
        
        if rsi >= stock_config.rsi_overbought:
            alerts.append(StockAlert(
                symbol=stock_config.symbol,
                name=stock_config.name,
                alert_type=AlertType.RSI_OVERBOUGHT,
                current_value=rsi,
                threshold=stock_config.rsi_overbought,
                message=f"RSI超买信号: {rsi:.2f} >= {stock_config.rsi_overbought}",
                timestamp=datetime.now(),
                level=AlertLevel.WARNING
            ))
        
        if rsi <= stock_config.rsi_oversold:
            alerts.append(StockAlert(
                symbol=stock_config.symbol,
                name=stock_config.name,
                alert_type=AlertType.RSI_OVERSOLD,
                current_value=rsi,
                threshold=stock_config.rsi_oversold,
                message=f"RSI超卖信号: {rsi:.2f} <= {stock_config.rsi_oversold}",
                timestamp=datetime.now(),
                level=AlertLevel.WARNING
            ))
        
        return alerts
    
    def _check_price_alerts(self, stock_config: StockThresholdConfig, price_change: float) -> List[StockAlert]:
        """检查价格变动预警"""
        alerts = []
        
        if price_change >= stock_config.price_change_threshold:
            alerts.append(StockAlert(
                symbol=stock_config.symbol,
                name=stock_config.name,
                alert_type=AlertType.PRICE_SURGE,
                current_value=price_change,
                threshold=stock_config.price_change_threshold,
                message=f"价格大幅上涨: {price_change:.2%} >= {stock_config.price_change_threshold:.2%}",
                timestamp=datetime.now(),
                level=AlertLevel.INFO
            ))
        
        if price_change <= -stock_config.price_change_threshold:
            alerts.append(StockAlert(
                symbol=stock_config.symbol,
                name=stock_config.name,
                alert_type=AlertType.PRICE_DROP,
                current_value=price_change,
                threshold=-stock_config.price_change_threshold,
                message=f"价格大幅下跌: {price_change:.2%} <= {-stock_config.price_change_threshold:.2%}",
                timestamp=datetime.now(),
                level=AlertLevel.WARNING
            ))
        
        return alerts
    
    def _check_volume_alerts(self, stock_config: StockThresholdConfig, volume_ratio: float) -> List[StockAlert]:
        """检查成交量预警"""
        alerts = []
        
        if volume_ratio >= stock_config.volume_threshold:
            alerts.append(StockAlert(
                symbol=stock_config.symbol,
                name=stock_config.name,
                alert_type=AlertType.VOLUME_SPIKE,
                current_value=volume_ratio,
                threshold=stock_config.volume_threshold,
                message=f"成交量异常放大: {volume_ratio:.2f}倍 >= {stock_config.volume_threshold}倍",
                timestamp=datetime.now(),
                level=AlertLevel.INFO
            ))
        
        return alerts
    
    def _check_macd_alerts(self, stock_config: StockThresholdConfig, histogram: float) -> List[StockAlert]:
        """检查MACD预警"""
        alerts = []
        
        if abs(histogram) >= stock_config.macd_threshold:
            alert_type = AlertType.MACD_SIGNAL
            message = f"MACD信号: {histogram:.4f}, 阈值: {stock_config.macd_threshold}"
            
            alerts.append(StockAlert(
                symbol=stock_config.symbol,
                name=stock_config.name,
                alert_type=alert_type,
                current_value=histogram,
                threshold=stock_config.macd_threshold,
                message=message,
                timestamp=datetime.now(),
                level=AlertLevel.INFO
            ))
        
        return alerts
    
    async def _handle_alert(self, alert: StockAlert):
        """处理预警"""
        # 检查通知冷却时间
        alert_key = f"{alert.symbol}_{alert.alert_type.value}"
        now = datetime.now()
        
        if alert_key in self.last_notifications:
            last_time = self.last_notifications[alert_key]
            if (now - last_time).total_seconds() < config.monitoring.notification_cooldown:
                return  # 在冷却时间内，跳过通知
        
        # 记录预警
        self.logger.info(f"股票预警: {alert.symbol} - {alert.message}")
        
        # 发送通知
        if config.monitoring.enable_auto_notification:
            try:
                # 转换为MarketAlert格式
                market_alert = MarketAlert(
                    symbol=alert.symbol,
                    alert_type=alert.alert_type.value,
                    message=alert.message,
                    level=alert.level,
                    timestamp=alert.timestamp,
                    current_price=alert.current_value,
                    threshold=alert.threshold
                )
                
                # 发送企微通知
                await self.notification_manager.notify_market_alert(market_alert)
                
                # 更新最后通知时间
                self.last_notifications[alert_key] = now
                
            except Exception as e:
                self.logger.error(f"发送预警通知失败: {e}")
    
    def _standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化数据框列名"""
        # 创建列名映射
        column_mapping = {
            'ts_code': 'symbol',
            'trade_date': 'date',
            'vol': 'volume',
            'amount': 'turnover'
        }
        
        # 重命名列
        df = df.rename(columns=column_mapping)
        
        # 确保必要的列存在
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in df.columns:
                self.logger.warning(f"数据框缺少列: {col}")
        
        return df
    
    async def get_monitoring_status(self) -> Dict:
        """获取监控状态"""
        return {
            'is_running': self.is_running,
            'monitored_stocks': len(config.monitoring.stock_thresholds),
            'polling_interval': config.monitoring.polling_interval,
            'auto_notification': config.monitoring.enable_auto_notification,
            'last_check': datetime.now().isoformat()
        }