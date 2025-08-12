#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易引擎核心模块

整合所有模块并提供统一的交易系统接口
"""

import asyncio
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict

from ..models.models import TradeSignal, MarketAlert, TradeAction, OrderStatus
from ..data.data_provider import DataManager
from ..core.monitor import StockMonitor
from ..strategy.pressure_support_strategy import PressureSupportStrategy
from ..notification.wecom_notifier import NotificationManager
from ..utils.logger import LoggerMixin, log_trade_signal, log_trade_execution, log_system_status


class RiskManager(LoggerMixin):
    """风险管理器"""
    
    def __init__(self, config):
        self.config = config
        self.max_position_size = config.risk.max_position_size
        self.max_positions = config.risk.max_positions
        self.stop_loss = config.risk.stop_loss
        self.take_profit = config.risk.take_profit
        self.risk_tolerance = config.risk.risk_tolerance
        
        # 当前持仓信息
        self.current_positions = {}
        self.daily_pnl = 0.0
        self.total_exposure = 0.0
        
    def check_risk_limits(self, signal: TradeSignal) -> tuple[bool, str]:
        """检查风险限制
        
        Args:
            signal: 交易信号
            
        Returns:
            (是否通过风险检查, 原因)
        """
        try:
            # 1. 检查最大持仓数量
            if signal.action == TradeAction.BUY:
                if len(self.current_positions) >= self.max_positions:
                    return False, f"超过最大持仓数量限制: {self.max_positions}"
            
            # 2. 检查单笔交易金额
            trade_amount = signal.price * signal.quantity
            if trade_amount > self.max_position_size:
                return False, f"单笔交易金额超限: {trade_amount:.2f} > {self.max_position_size}"
            
            # 3. 检查总风险敞口
            if signal.action == TradeAction.BUY:
                new_exposure = self.total_exposure + trade_amount
                max_exposure = self.max_position_size * self.max_positions
                if new_exposure > max_exposure:
                    return False, f"总风险敞口超限: {new_exposure:.2f} > {max_exposure}"
            
            # 4. 检查日内亏损限制
            if self.daily_pnl < -self.max_position_size * self.risk_tolerance:
                return False, f"日内亏损超限: {self.daily_pnl:.2f}"
            
            # 5. 检查信心度阈值
            if signal.confidence < 0.6:  # 最低信心度要求
                return False, f"信心度过低: {signal.confidence:.2%}"
            
            return True, "风险检查通过"
            
        except Exception as e:
            self.logger.error(f"风险检查异常: {e}")
            return False, f"风险检查异常: {e}"
    
    def update_position(self, symbol: str, action: TradeAction, quantity: int, price: float):
        """更新持仓信息
        
        Args:
            symbol: 股票代码
            action: 交易动作
            quantity: 数量
            price: 价格
        """
        try:
            if action == TradeAction.BUY:
                if symbol in self.current_positions:
                    # 加仓
                    pos = self.current_positions[symbol]
                    total_cost = pos['quantity'] * pos['avg_price'] + quantity * price
                    total_quantity = pos['quantity'] + quantity
                    pos['avg_price'] = total_cost / total_quantity
                    pos['quantity'] = total_quantity
                else:
                    # 新建仓位
                    self.current_positions[symbol] = {
                        'quantity': quantity,
                        'avg_price': price,
                        'open_time': datetime.now()
                    }
                
                self.total_exposure += quantity * price
                
            elif action == TradeAction.SELL:
                if symbol in self.current_positions:
                    pos = self.current_positions[symbol]
                    if pos['quantity'] >= quantity:
                        # 计算盈亏
                        pnl = (price - pos['avg_price']) * quantity
                        self.daily_pnl += pnl
                        
                        # 更新持仓
                        pos['quantity'] -= quantity
                        self.total_exposure -= quantity * pos['avg_price']
                        
                        # 如果全部卖出，删除持仓
                        if pos['quantity'] == 0:
                            del self.current_positions[symbol]
                    else:
                        self.logger.warning(f"卖出数量超过持仓: {symbol}")
                        
        except Exception as e:
            self.logger.error(f"更新持仓信息失败: {e}")
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """获取风险摘要
        
        Returns:
            风险摘要信息
        """
        return {
            'current_positions': len(self.current_positions),
            'max_positions': self.max_positions,
            'total_exposure': self.total_exposure,
            'daily_pnl': self.daily_pnl,
            'risk_utilization': len(self.current_positions) / self.max_positions,
            'exposure_utilization': self.total_exposure / (self.max_position_size * self.max_positions)
        }


class TradeExecutor(LoggerMixin):
    """交易执行器（模拟）"""
    
    def __init__(self, config):
        self.config = config
        self.commission_rate = 0.0003  # 手续费率
        self.executed_trades = []
        
    async def execute_trade(self, signal: TradeSignal) -> tuple[bool, str]:
        """执行交易（模拟）
        
        Args:
            signal: 交易信号
            
        Returns:
            (是否执行成功, 执行结果)
        """
        try:
            # 模拟交易执行延迟
            await asyncio.sleep(0.1)
            
            # 计算手续费
            trade_amount = signal.price * signal.quantity
            commission = trade_amount * self.commission_rate
            
            # 模拟执行成功（实际应该调用券商API）
            execution_result = {
                'symbol': signal.symbol,
                'action': signal.action,
                'quantity': signal.quantity,
                'price': signal.price,
                'amount': trade_amount,
                'commission': commission,
                'status': OrderStatus.FILLED,
                'executed_at': datetime.now(),
                'strategy': signal.strategy,
                'signal_reason': signal.reason
            }
            
            self.executed_trades.append(execution_result)
            
            log_trade_execution(
                signal.symbol,
                signal.action.value,
                signal.price,
                signal.quantity,
                "success"
            )
            
            return True, "交易执行成功"
            
        except Exception as e:
            self.logger.error(f"交易执行失败: {e}")
            log_trade_execution(
                signal.symbol,
                signal.action.value,
                signal.price,
                signal.quantity,
                f"failed: {e}"
            )
            return False, f"交易执行失败: {e}"
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要
        
        Returns:
            执行摘要信息
        """
        today = datetime.now().date()
        today_trades = [t for t in self.executed_trades 
                       if t['executed_at'].date() == today]
        
        buy_trades = [t for t in today_trades if t['action'] == TradeAction.BUY]
        sell_trades = [t for t in today_trades if t['action'] == TradeAction.SELL]
        
        return {
            'total_trades': len(self.executed_trades),
            'today_trades': len(today_trades),
            'today_buy_trades': len(buy_trades),
            'today_sell_trades': len(sell_trades),
            'total_commission': sum(t['commission'] for t in self.executed_trades),
            'today_commission': sum(t['commission'] for t in today_trades)
        }


class TradingEngine(LoggerMixin):
    """交易引擎主类"""
    
    def __init__(self, config):
        self.config = config
        
        # 核心组件
        self.data_manager = None
        self.monitor = None
        self.strategy = None
        self.risk_manager = None
        self.trade_executor = None
        self.notification_manager = None
        
        # 运行状态
        self.is_running = False
        self.start_time = None
        
        # 统计信息
        self.stats = {
            'signals_generated': 0,
            'trades_executed': 0,
            'alerts_triggered': 0,
            'notifications_sent': 0
        }
        
    async def initialize(self):
        """初始化交易引擎"""
        try:
            self.logger.info("正在初始化交易引擎...")
            
            # 初始化数据管理器
            self.data_manager = DataManager(self.config)
            await self.data_manager.initialize()
            
            # 初始化风险管理器
            self.risk_manager = RiskManager(self.config)
            
            # 初始化交易执行器
            self.trade_executor = TradeExecutor(self.config)
            
            # 初始化策略
            self.strategy = PressureSupportStrategy(self.config, self.data_manager)
            
            # 初始化监控器
            self.monitor = StockMonitor(self.config, self.data_manager)
            self.monitor.add_alert_callback(self._handle_market_alert)
            
            # 初始化通知管理器
            self.notification_manager = NotificationManager(self.config)
            await self.notification_manager.initialize()
            
            # 设置定时任务
            self._setup_scheduled_tasks()
            
            self.logger.info("交易引擎初始化完成")
            
        except Exception as e:
            self.logger.error(f"交易引擎初始化失败: {e}")
            raise
    
    async def run(self):
        """运行交易引擎"""
        try:
            self.is_running = True
            self.start_time = datetime.now()
            
            log_system_status("TradingEngine", "running", "交易引擎已启动")
            
            # 启动监控
            await self.monitor.start_monitoring()
            
            # 发送启动通知
            await self._send_startup_notification()
            
            # 主循环
            await self._main_loop()
            
        except Exception as e:
            self.logger.error(f"交易引擎运行异常: {e}")
            raise
    
    async def stop(self):
        """停止交易引擎"""
        try:
            self.is_running = False
            
            # 停止监控
            if self.monitor:
                await self.monitor.stop_monitoring()
            
            # 关闭数据管理器
            if self.data_manager:
                await self.data_manager.close()
            
            # 关闭通知管理器
            if self.notification_manager:
                await self.notification_manager.close()
            
            # 发送停止通知
            await self._send_shutdown_notification()
            
            log_system_status("TradingEngine", "stopped", "交易引擎已停止")
            
        except Exception as e:
            self.logger.error(f"停止交易引擎异常: {e}")
    
    async def _main_loop(self):
        """主循环"""
        while self.is_running:
            try:
                # 执行定时任务
                schedule.run_pending()
                
                # 生成交易信号
                await self._generate_trade_signals()
                
                # 等待下一个周期
                await asyncio.sleep(60)  # 每分钟检查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"主循环异常: {e}")
                await asyncio.sleep(60)
    
    async def _generate_trade_signals(self):
        """生成交易信号"""
        try:
            symbols = self.config.monitoring.stocks
            
            for symbol in symbols:
                # 生成信号
                signal = await self.strategy.generate_signal(symbol)
                
                if signal:
                    self.stats['signals_generated'] += 1
                    
                    # 记录信号
                    log_trade_signal(
                        signal.symbol,
                        signal.action.value,
                        signal.price,
                        signal.quantity,
                        signal.reason
                    )
                    
                    # 风险检查
                    risk_passed, risk_reason = self.risk_manager.check_risk_limits(signal)
                    
                    if risk_passed:
                        # 执行交易
                        success, exec_result = await self.trade_executor.execute_trade(signal)
                        
                        if success:
                            self.stats['trades_executed'] += 1
                            
                            # 更新持仓
                            self.risk_manager.update_position(
                                signal.symbol,
                                signal.action,
                                signal.quantity,
                                signal.price
                            )
                            
                            # 发送交易通知
                            await self.notification_manager.notify_trade_signal(signal)
                            self.stats['notifications_sent'] += 1
                    else:
                        self.logger.warning(f"风险检查未通过: {risk_reason}")
                        
        except Exception as e:
            self.logger.error(f"生成交易信号失败: {e}")
    
    async def _handle_market_alert(self, alert: MarketAlert):
        """处理市场预警
        
        Args:
            alert: 市场预警
        """
        try:
            self.stats['alerts_triggered'] += 1
            
            # 发送预警通知
            await self.notification_manager.notify_market_alert(alert)
            self.stats['notifications_sent'] += 1
            
        except Exception as e:
            self.logger.error(f"处理市场预警失败: {e}")
    
    def _setup_scheduled_tasks(self):
        """设置定时任务"""
        # 每日总结（收盘后）
        schedule.every().day.at("15:30").do(self._schedule_daily_summary)
        
        # 系统状态报告（每小时）
        schedule.every().hour.do(self._schedule_status_report)
        
        # 风险检查（每30分钟）
        schedule.every(30).minutes.do(self._schedule_risk_check)
    
    def _schedule_daily_summary(self):
        """定时每日总结"""
        asyncio.create_task(self._send_daily_summary())
    
    def _schedule_status_report(self):
        """定时状态报告"""
        asyncio.create_task(self._send_status_report())
    
    def _schedule_risk_check(self):
        """定时风险检查"""
        asyncio.create_task(self._perform_risk_check())
    
    async def _send_startup_notification(self):
        """发送启动通知"""
        try:
            status = {
                'system_name': '量化股票交易系统',
                'status': '已启动',
                'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'monitored_stocks': len(self.config.monitoring.stocks),
                'active_strategies': 1,
                'healthy': True
            }
            
            await self.notification_manager.notify_system_status(status)
            
        except Exception as e:
            self.logger.error(f"发送启动通知失败: {e}")
    
    async def _send_shutdown_notification(self):
        """发送停止通知"""
        try:
            if self.start_time:
                uptime = datetime.now() - self.start_time
                uptime_str = str(uptime).split('.')[0]  # 去掉微秒
            else:
                uptime_str = 'N/A'
            
            status = {
                'system_name': '量化股票交易系统',
                'status': '已停止',
                'uptime': uptime_str,
                'total_signals': self.stats['signals_generated'],
                'total_trades': self.stats['trades_executed'],
                'total_alerts': self.stats['alerts_triggered'],
                'healthy': False
            }
            
            await self.notification_manager.notify_system_status(status)
            
        except Exception as e:
            self.logger.error(f"发送停止通知失败: {e}")
    
    async def _send_daily_summary(self):
        """发送每日总结"""
        try:
            exec_summary = self.trade_executor.get_execution_summary()
            risk_summary = self.risk_manager.get_risk_summary()
            
            summary = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'total_trades': exec_summary['today_trades'],
                'buy_trades': exec_summary['today_buy_trades'],
                'sell_trades': exec_summary['today_sell_trades'],
                'total_pnl': risk_summary['daily_pnl'],
                'positions_count': risk_summary['current_positions'],
                'total_commission': exec_summary['today_commission'],
                'signals_generated': self.stats['signals_generated'],
                'alerts_triggered': self.stats['alerts_triggered']
            }
            
            await self.notification_manager.notify_daily_summary(summary)
            
        except Exception as e:
            self.logger.error(f"发送每日总结失败: {e}")
    
    async def _send_status_report(self):
        """发送状态报告"""
        try:
            uptime = datetime.now() - self.start_time if self.start_time else timedelta(0)
            uptime_str = str(uptime).split('.')[0]
            
            status = {
                'system_name': '量化股票交易系统',
                'status': '运行中' if self.is_running else '已停止',
                'uptime': uptime_str,
                'monitored_stocks': len(self.config.monitoring.stocks),
                'active_strategies': 1,
                'today_trades': self.trade_executor.get_execution_summary()['today_trades'],
                'current_positions': self.risk_manager.get_risk_summary()['current_positions'],
                'healthy': self.is_running
            }
            
            await self.notification_manager.notify_system_status(status)
            
        except Exception as e:
            self.logger.error(f"发送状态报告失败: {e}")
    
    async def _perform_risk_check(self):
        """执行风险检查"""
        try:
            risk_summary = self.risk_manager.get_risk_summary()
            
            # 检查风险指标
            warnings = []
            
            if risk_summary['risk_utilization'] > 0.8:
                warnings.append("持仓数量接近上限")
            
            if risk_summary['exposure_utilization'] > 0.8:
                warnings.append("风险敞口接近上限")
            
            if risk_summary['daily_pnl'] < -self.config.risk.max_position_size * 0.5:
                warnings.append("日内亏损较大")
            
            # 如果有风险警告，发送通知
            if warnings:
                message = f"⚠️ 风险提醒\n\n" + "\n".join(f"• {w}" for w in warnings)
                message += f"\n\n当前持仓: {risk_summary['current_positions']}\n"
                message += f"日内盈亏: ¥{risk_summary['daily_pnl']:.2f}"
                
                await self.notification_manager.send_custom_notification(message)
                
        except Exception as e:
            self.logger.error(f"风险检查失败: {e}")
    
    def get_engine_status(self) -> Dict[str, Any]:
        """获取引擎状态
        
        Returns:
            引擎状态信息
        """
        uptime = datetime.now() - self.start_time if self.start_time else timedelta(0)
        
        return {
            'is_running': self.is_running,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'uptime': str(uptime).split('.')[0],
            'stats': self.stats.copy(),
            'risk_summary': self.risk_manager.get_risk_summary() if self.risk_manager else {},
            'execution_summary': self.trade_executor.get_execution_summary() if self.trade_executor else {},
            'monitoring_summary': self.monitor.get_monitoring_summary() if self.monitor else {}
        }