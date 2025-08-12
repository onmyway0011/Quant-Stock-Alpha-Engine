#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企业微信通知模块

负责发送交易信号和预警消息到企业微信
"""

import json
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from ..models.models import TradeSignal, MarketAlert, TradeAction, AlertLevel
from ..utils.logger import LoggerMixin, log_notification_sent


class MessageType(Enum):
    """消息类型枚举"""
    TEXT = "text"
    MARKDOWN = "markdown"
    IMAGE = "image"
    NEWS = "news"


class WeComNotifier(LoggerMixin):
    """企业微信通知器"""
    
    def __init__(self, webhook_url: str, mention_all: bool = False):
        self.webhook_url = webhook_url
        self.mention_all = mention_all
        self.session = None
        
    async def initialize(self) -> bool:
        """初始化通知器
        
        Returns:
            是否初始化成功
        """
        try:
            self.session = aiohttp.ClientSession()
            
            # 测试连接
            test_message = {
                "msgtype": "text",
                "text": {
                    "content": "量化交易系统连接测试"
                }
            }
            
            success = await self._send_message(test_message)
            if success:
                self.logger.info("企业微信通知器初始化成功")
                return True
            else:
                self.logger.error("企业微信通知器初始化失败")
                return False
                
        except Exception as e:
            self.logger.error(f"企业微信通知器初始化异常: {e}")
            return False
    
    async def send_trade_signal(self, signal: TradeSignal) -> bool:
        """发送交易信号通知
        
        Args:
            signal: 交易信号
            
        Returns:
            是否发送成功
        """
        try:
            # 构建交易信号消息
            message = self._build_trade_signal_message(signal)
            success = await self._send_message(message)
            
            log_notification_sent(
                "WeChat", 
                f"交易信号: {signal.symbol} {signal.action.value}",
                "success" if success else "failed"
            )
            
            return success
            
        except Exception as e:
            self.logger.error(f"发送交易信号通知失败: {e}")
            return False
    
    async def send_market_alert(self, alert: MarketAlert) -> bool:
        """发送市场预警通知
        
        Args:
            alert: 市场预警
            
        Returns:
            是否发送成功
        """
        try:
            # 构建预警消息
            message = self._build_market_alert_message(alert)
            success = await self._send_message(message)
            
            log_notification_sent(
                "WeChat", 
                f"市场预警: {alert.symbol} {alert.alert_type}",
                "success" if success else "failed"
            )
            
            return success
            
        except Exception as e:
            self.logger.error(f"发送市场预警通知失败: {e}")
            return False
    
    async def send_system_status(self, status: Dict[str, Any]) -> bool:
        """发送系统状态通知
        
        Args:
            status: 系统状态信息
            
        Returns:
            是否发送成功
        """
        try:
            message = self._build_system_status_message(status)
            success = await self._send_message(message)
            
            log_notification_sent(
                "WeChat", 
                "系统状态更新",
                "success" if success else "failed"
            )
            
            return success
            
        except Exception as e:
            self.logger.error(f"发送系统状态通知失败: {e}")
            return False
    
    async def send_daily_summary(self, summary: Dict[str, Any]) -> bool:
        """发送每日总结
        
        Args:
            summary: 每日总结数据
            
        Returns:
            是否发送成功
        """
        try:
            message = self._build_daily_summary_message(summary)
            success = await self._send_message(message)
            
            log_notification_sent(
                "WeChat", 
                "每日交易总结",
                "success" if success else "failed"
            )
            
            return success
            
        except Exception as e:
            self.logger.error(f"发送每日总结失败: {e}")
            return False
    
    def _build_trade_signal_message(self, signal: TradeSignal) -> Dict[str, Any]:
        """构建交易信号消息
        
        Args:
            signal: 交易信号
            
        Returns:
            消息字典
        """
        # 动作图标
        action_icons = {
            TradeAction.BUY: "📈",
            TradeAction.SELL: "📉",
            TradeAction.HOLD: "⏸️"
        }
        
        # 信心度颜色
        confidence_color = self._get_confidence_color(signal.confidence)
        
        # 构建Markdown消息
        content = f"""
## {action_icons.get(signal.action, '📊')} 交易信号

**股票代码**: {signal.symbol}
**交易动作**: <font color="{confidence_color}">{signal.action.value.upper()}</font>
**价格**: ¥{signal.price:.2f}
**数量**: {signal.quantity:,}股
**信心度**: {signal.confidence:.1%}
**策略**: {signal.strategy}
**原因**: {signal.reason}
**时间**: {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

> 请根据市场情况谨慎决策，注意风险控制！
"""
        
        message = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }
        
        # 添加@所有人
        if self.mention_all:
            message["markdown"]["content"] += "\n\n<@all>"
        
        return message
    
    def _build_market_alert_message(self, alert: MarketAlert) -> Dict[str, Any]:
        """构建市场预警消息
        
        Args:
            alert: 市场预警
            
        Returns:
            消息字典
        """
        # 预警级别图标和颜色
        level_config = {
            AlertLevel.LOW: {"icon": "🟢", "color": "info"},
            AlertLevel.MEDIUM: {"icon": "🟡", "color": "warning"},
            AlertLevel.HIGH: {"icon": "🟠", "color": "warning"},
            AlertLevel.CRITICAL: {"icon": "🔴", "color": "warning"}
        }
        
        config = level_config.get(alert.level, {"icon": "⚠️", "color": "info"})
        
        content = f"""
## {config['icon']} 市场预警

**股票代码**: {alert.symbol}
**预警类型**: {alert.alert_type}
**预警级别**: <font color="{config['color']}">{alert.level.value.upper()}</font>
**当前值**: {alert.current_value:.4f}
**阈值**: {alert.threshold:.4f}
**消息**: {alert.message}
**时间**: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

> 请关注市场动态，及时调整策略！
"""
        
        message = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }
        
        # 高级别预警@所有人
        if alert.level in [AlertLevel.HIGH, AlertLevel.CRITICAL]:
            message["markdown"]["content"] += "\n\n<@all>"
        
        return message
    
    def _build_system_status_message(self, status: Dict[str, Any]) -> Dict[str, Any]:
        """构建系统状态消息
        
        Args:
            status: 系统状态
            
        Returns:
            消息字典
        """
        status_icon = "🟢" if status.get('healthy', True) else "🔴"
        
        content = f"""
## {status_icon} 系统状态更新

**系统名称**: {status.get('system_name', '量化交易系统')}
**运行状态**: {status.get('status', 'unknown')}
**运行时间**: {status.get('uptime', 'N/A')}
**监控股票**: {status.get('monitored_stocks', 0)}只
**活跃策略**: {status.get('active_strategies', 0)}个
**今日交易**: {status.get('today_trades', 0)}笔
**系统负载**: {status.get('cpu_usage', 'N/A')}
**内存使用**: {status.get('memory_usage', 'N/A')}
**更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }
    
    def _build_daily_summary_message(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """构建每日总结消息
        
        Args:
            summary: 每日总结
            
        Returns:
            消息字典
        """
        pnl = summary.get('total_pnl', 0)
        pnl_icon = "📈" if pnl >= 0 else "📉"
        pnl_color = "info" if pnl >= 0 else "warning"
        
        content = f"""
## 📊 每日交易总结

**日期**: {summary.get('date', datetime.now().strftime('%Y-%m-%d'))}
**总交易笔数**: {summary.get('total_trades', 0)}
**买入笔数**: {summary.get('buy_trades', 0)}
**卖出笔数**: {summary.get('sell_trades', 0)}
**总盈亏**: {pnl_icon} <font color="{pnl_color}">¥{pnl:,.2f}</font>
**胜率**: {summary.get('win_rate', 0):.1%}
**最大单笔盈利**: ¥{summary.get('max_profit', 0):,.2f}
**最大单笔亏损**: ¥{summary.get('max_loss', 0):,.2f}
**持仓股票**: {summary.get('positions_count', 0)}只
**现金余额**: ¥{summary.get('cash_balance', 0):,.2f}
**总资产**: ¥{summary.get('total_assets', 0):,.2f}

> 数据仅供参考，投资有风险，决策需谨慎！
"""
        
        return {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }
    
    def _get_confidence_color(self, confidence: float) -> str:
        """根据信心度获取颜色
        
        Args:
            confidence: 信心度 (0-1)
            
        Returns:
            颜色字符串
        """
        if confidence >= 0.8:
            return "info"  # 蓝色
        elif confidence >= 0.6:
            return "warning"  # 橙色
        else:
            return "comment"  # 灰色
    
    async def _send_message(self, message: Dict[str, Any]) -> bool:
        """发送消息到企业微信
        
        Args:
            message: 消息内容
            
        Returns:
            是否发送成功
        """
        try:
            if not self.webhook_url:
                self.logger.error("企业微信Webhook URL未配置")
                return False
            
            if not self.session:
                self.logger.error("HTTP会话未初始化")
                return False
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            async with self.session.post(
                self.webhook_url, 
                json=message, 
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    if result.get('errcode') == 0:
                        return True
                    else:
                        self.logger.error(f"企业微信API返回错误: {result}")
                        return False
                else:
                    self.logger.error(f"HTTP请求失败: {response.status}")
                    return False
                    
        except asyncio.TimeoutError:
            self.logger.error("发送消息超时")
            return False
        except Exception as e:
            self.logger.error(f"发送消息异常: {e}")
            return False
    
    async def send_custom_message(self, content: str, msg_type: MessageType = MessageType.TEXT) -> bool:
        """发送自定义消息
        
        Args:
            content: 消息内容
            msg_type: 消息类型
            
        Returns:
            是否发送成功
        """
        try:
            if msg_type == MessageType.TEXT:
                message = {
                    "msgtype": "text",
                    "text": {
                        "content": content
                    }
                }
            elif msg_type == MessageType.MARKDOWN:
                message = {
                    "msgtype": "markdown",
                    "markdown": {
                        "content": content
                    }
                }
            else:
                self.logger.error(f"不支持的消息类型: {msg_type}")
                return False
            
            return await self._send_message(message)
            
        except Exception as e:
            self.logger.error(f"发送自定义消息失败: {e}")
            return False
    
    async def close(self):
        """关闭通知器"""
        if self.session:
            await self.session.close()
            self.logger.info("企业微信通知器已关闭")


class NotificationManager(LoggerMixin):
    """通知管理器"""
    
    def __init__(self, config):
        self.config = config
        self.wecom_notifier = None
        self.enabled = config.notification.wecom_enabled
        
    async def initialize(self) -> bool:
        """初始化通知管理器
        
        Returns:
            是否初始化成功
        """
        if not self.enabled:
            self.logger.info("企业微信通知已禁用")
            return True
            
        try:
            webhook_url = self.config.notification.wecom_webhook_url
            mention_all = self.config.notification.mention_all
            
            if not webhook_url:
                self.logger.error("企业微信Webhook URL未配置")
                return False
            
            self.wecom_notifier = WeComNotifier(webhook_url, mention_all)
            success = await self.wecom_notifier.initialize()
            
            if success:
                self.logger.info("通知管理器初始化成功")
            else:
                self.logger.error("通知管理器初始化失败")
                
            return success
            
        except Exception as e:
            self.logger.error(f"通知管理器初始化异常: {e}")
            return False
    
    async def notify_trade_signal(self, signal: TradeSignal) -> bool:
        """通知交易信号
        
        Args:
            signal: 交易信号
            
        Returns:
            是否通知成功
        """
        if not self.enabled or not self.wecom_notifier:
            return True
            
        return await self.wecom_notifier.send_trade_signal(signal)
    
    async def notify_market_alert(self, alert: MarketAlert) -> bool:
        """通知市场预警
        
        Args:
            alert: 市场预警
            
        Returns:
            是否通知成功
        """
        if not self.enabled or not self.wecom_notifier:
            return True
            
        return await self.wecom_notifier.send_market_alert(alert)
    
    async def notify_system_status(self, status: Dict[str, Any]) -> bool:
        """通知系统状态
        
        Args:
            status: 系统状态
            
        Returns:
            是否通知成功
        """
        if not self.enabled or not self.wecom_notifier:
            return True
            
        return await self.wecom_notifier.send_system_status(status)
    
    async def notify_daily_summary(self, summary: Dict[str, Any]) -> bool:
        """通知每日总结
        
        Args:
            summary: 每日总结
            
        Returns:
            是否通知成功
        """
        if not self.enabled or not self.wecom_notifier:
            return True
            
        return await self.wecom_notifier.send_daily_summary(summary)
    
    async def send_custom_notification(self, content: str, msg_type: MessageType = MessageType.TEXT) -> bool:
        """发送自定义通知
        
        Args:
            content: 消息内容
            msg_type: 消息类型
            
        Returns:
            是否发送成功
        """
        if not self.enabled or not self.wecom_notifier:
            return True
            
        return await self.wecom_notifier.send_custom_message(content, msg_type)
    
    async def close(self):
        """关闭通知管理器"""
        if self.wecom_notifier:
            await self.wecom_notifier.close()