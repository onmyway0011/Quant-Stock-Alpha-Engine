#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易引擎测试

测试交易引擎的核心功能
"""

import unittest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.engine import (
    TradingEngine, RiskManager, TradeExecutor
)
from src.models.models import (
    TradeSignal, MarketAlert, TradeAction, OrderStatus, AlertLevel
)


class TestEngine(unittest.TestCase):
    """交易引擎测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # 模拟配置
        self.mock_config = MagicMock()
        self.mock_config.risk.max_position_size = 10000
        self.mock_config.risk.max_positions = 5
        self.mock_config.risk.stop_loss = 0.05
        self.mock_config.risk.take_profit = 0.10
        self.mock_config.risk.risk_tolerance = 0.02
        self.mock_config.monitoring.stocks = ['000001.SZ', '600519.SH']
        
        # 创建测试数据
        self.test_trade_signal = TradeSignal(
            symbol='000001.SZ',
            action=TradeAction.BUY,
            price=12.50,
            quantity=800,
            confidence=0.85,
            reason='突破阻力位',
            timestamp=datetime.now(),
            strategy='pressure_support_strategy'
        )
        
        self.test_market_alert = MarketAlert(
            symbol='600519.SH',
            alert_type='price_volatility',
            level=AlertLevel.HIGH,
            message='价格波动率异常',
            current_value=0.052,
            threshold=0.03,
            timestamp=datetime.now()
        )
    
    def tearDown(self):
        """测试后清理"""
        self.loop.close()
    
    def test_risk_manager_initialization(self):
        """测试风险管理器初始化"""
        risk_manager = RiskManager(self.mock_config)
        
        self.assertEqual(risk_manager.max_position_size, 10000)
        self.assertEqual(risk_manager.max_positions, 5)
        self.assertEqual(risk_manager.stop_loss, 0.05)
        self.assertEqual(risk_manager.take_profit, 0.10)
        self.assertEqual(risk_manager.risk_tolerance, 0.02)
        self.assertEqual(risk_manager.current_positions, {})
        self.assertEqual(risk_manager.daily_pnl, 0.0)
        self.assertEqual(risk_manager.total_exposure, 0.0)
    
    def test_risk_manager_check_limits_success(self):
        """测试风险限制检查通过"""
        risk_manager = RiskManager(self.mock_config)
        
        # 正常交易信号应该通过检查
        passed, reason = risk_manager.check_risk_limits(self.test_trade_signal)
        
        self.assertTrue(passed)
        self.assertEqual(reason, "风险检查通过")
    
    def test_risk_manager_check_position_limit(self):
        """测试持仓数量限制"""
        risk_manager = RiskManager(self.mock_config)
        
        # 模拟已达到最大持仓数量
        for i in range(5):
            risk_manager.current_positions[f'00000{i}.SZ'] = {
                'quantity': 100,
                'avg_price': 10.0
            }
        
        # 新的买入信号应该被拒绝
        passed, reason = risk_manager.check_risk_limits(self.test_trade_signal)
        
        self.assertFalse(passed)
        self.assertIn("超过最大持仓数量限制", reason)
    
    def test_risk_manager_check_amount_limit(self):
        """测试单笔交易金额限制"""
        risk_manager = RiskManager(self.mock_config)
        
        # 创建超过限制的交易信号
        large_signal = TradeSignal(
            symbol='000001.SZ',
            action=TradeAction.BUY,
            price=100.0,  # 高价格
            quantity=1000,  # 大数量
            confidence=0.85,
            reason='测试',
            timestamp=datetime.now(),
            strategy='test'
        )
        
        passed, reason = risk_manager.check_risk_limits(large_signal)
        
        self.assertFalse(passed)
        self.assertIn("单笔交易金额超限", reason)
    
    def test_risk_manager_check_confidence_limit(self):
        """测试信心度限制"""
        risk_manager = RiskManager(self.mock_config)
        
        # 创建低信心度信号
        low_confidence_signal = TradeSignal(
            symbol='000001.SZ',
            action=TradeAction.BUY,
            price=12.50,
            quantity=100,
            confidence=0.3,  # 低信心度
            reason='测试',
            timestamp=datetime.now(),
            strategy='test'
        )
        
        passed, reason = risk_manager.check_risk_limits(low_confidence_signal)
        
        self.assertFalse(passed)
        self.assertIn("信心度过低", reason)
    
    def test_risk_manager_update_position_buy(self):
        """测试更新持仓 - 买入"""
        risk_manager = RiskManager(self.mock_config)
        
        # 首次买入
        risk_manager.update_position('000001.SZ', TradeAction.BUY, 100, 12.50)
        
        self.assertIn('000001.SZ', risk_manager.current_positions)
        position = risk_manager.current_positions['000001.SZ']
        self.assertEqual(position['quantity'], 100)
        self.assertEqual(position['avg_price'], 12.50)
        self.assertEqual(risk_manager.total_exposure, 1250.0)
        
        # 加仓
        risk_manager.update_position('000001.SZ', TradeAction.BUY, 100, 13.00)
        
        position = risk_manager.current_positions['000001.SZ']
        self.assertEqual(position['quantity'], 200)
        self.assertEqual(position['avg_price'], 12.75)  # 平均成本
        self.assertEqual(risk_manager.total_exposure, 2550.0)
    
    def test_risk_manager_update_position_sell(self):
        """测试更新持仓 - 卖出"""
        risk_manager = RiskManager(self.mock_config)
        
        # 先建立持仓
        risk_manager.current_positions['000001.SZ'] = {
            'quantity': 200,
            'avg_price': 12.50,
            'open_time': datetime.now()
        }
        risk_manager.total_exposure = 2500.0
        
        # 部分卖出
        risk_manager.update_position('000001.SZ', TradeAction.SELL, 100, 13.00)
        
        position = risk_manager.current_positions['000001.SZ']
        self.assertEqual(position['quantity'], 100)
        self.assertEqual(risk_manager.daily_pnl, 50.0)  # (13.00 - 12.50) * 100
        
        # 全部卖出
        risk_manager.update_position('000001.SZ', TradeAction.SELL, 100, 13.50)
        
        self.assertNotIn('000001.SZ', risk_manager.current_positions)
        self.assertEqual(risk_manager.daily_pnl, 150.0)  # 总盈利
    
    def test_risk_manager_get_summary(self):
        """测试获取风险摘要"""
        risk_manager = RiskManager(self.mock_config)
        
        # 添加一些持仓
        risk_manager.current_positions['000001.SZ'] = {'quantity': 100, 'avg_price': 12.50}
        risk_manager.current_positions['000002.SZ'] = {'quantity': 200, 'avg_price': 10.00}
        risk_manager.total_exposure = 3250.0
        risk_manager.daily_pnl = 150.0
        
        summary = risk_manager.get_risk_summary()
        
        self.assertEqual(summary['current_positions'], 2)
        self.assertEqual(summary['max_positions'], 5)
        self.assertEqual(summary['total_exposure'], 3250.0)
        self.assertEqual(summary['daily_pnl'], 150.0)
        self.assertEqual(summary['risk_utilization'], 0.4)  # 2/5
    
    def test_trade_executor_initialization(self):
        """测试交易执行器初始化"""
        executor = TradeExecutor(self.mock_config)
        
        self.assertEqual(executor.config, self.mock_config)
        self.assertEqual(executor.commission_rate, 0.0003)
        self.assertEqual(executor.executed_trades, [])
    
    def test_trade_executor_execute_trade(self):
        """测试交易执行"""
        executor = TradeExecutor(self.mock_config)
        
        async def test_execution():
            success, result = await executor.execute_trade(self.test_trade_signal)
            
            self.assertTrue(success)
            self.assertEqual(result, "交易执行成功")
            self.assertEqual(len(executor.executed_trades), 1)
            
            trade = executor.executed_trades[0]
            self.assertEqual(trade['symbol'], '000001.SZ')
            self.assertEqual(trade['action'], TradeAction.BUY)
            self.assertEqual(trade['quantity'], 800)
            self.assertEqual(trade['price'], 12.50)
            self.assertEqual(trade['status'], OrderStatus.FILLED)
            self.assertGreater(trade['commission'], 0)
        
        self.loop.run_until_complete(test_execution())
    
    def test_trade_executor_get_summary(self):
        """测试获取执行摘要"""
        executor = TradeExecutor(self.mock_config)
        
        # 模拟一些交易记录
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        executor.executed_trades = [
            {
                'symbol': '000001.SZ',
                'action': TradeAction.BUY,
                'executed_at': today,
                'commission': 3.75
            },
            {
                'symbol': '000002.SZ',
                'action': TradeAction.SELL,
                'executed_at': today,
                'commission': 2.50
            },
            {
                'symbol': '000003.SZ',
                'action': TradeAction.BUY,
                'executed_at': yesterday,
                'commission': 1.25
            }
        ]
        
        summary = executor.get_execution_summary()
        
        self.assertEqual(summary['total_trades'], 3)
        self.assertEqual(summary['today_trades'], 2)
        self.assertEqual(summary['today_buy_trades'], 1)
        self.assertEqual(summary['today_sell_trades'], 1)
        self.assertEqual(summary['total_commission'], 7.50)
        self.assertEqual(summary['today_commission'], 6.25)
    
    @patch('src.core.engine.DataManager')
    @patch('src.core.engine.StockMonitor')
    @patch('src.core.engine.PressureSupportStrategy')
    @patch('src.core.engine.NotificationManager')
    def test_trading_engine_initialization(self, mock_notification, mock_strategy, mock_monitor, mock_data):
        """测试交易引擎初始化"""
        engine = TradingEngine(self.mock_config)
        
        self.assertEqual(engine.config, self.mock_config)
        self.assertFalse(engine.is_running)
        self.assertIsNone(engine.start_time)
        self.assertEqual(engine.stats['signals_generated'], 0)
    
    @patch('src.core.engine.DataManager')
    @patch('src.core.engine.StockMonitor')
    @patch('src.core.engine.PressureSupportStrategy')
    @patch('src.core.engine.NotificationManager')
    def test_trading_engine_initialize_components(self, mock_notification, mock_strategy, mock_monitor, mock_data):
        """测试交易引擎组件初始化"""
        # 模拟组件
        mock_data_instance = AsyncMock()
        mock_data.return_value = mock_data_instance
        
        mock_monitor_instance = MagicMock()
        mock_monitor.return_value = mock_monitor_instance
        
        mock_strategy_instance = MagicMock()
        mock_strategy.return_value = mock_strategy_instance
        
        mock_notification_instance = AsyncMock()
        mock_notification_instance.initialize.return_value = True
        mock_notification.return_value = mock_notification_instance
        
        engine = TradingEngine(self.mock_config)
        
        async def test_init():
            await engine.initialize()
            
            self.assertIsNotNone(engine.data_manager)
            self.assertIsNotNone(engine.monitor)
            self.assertIsNotNone(engine.strategy)
            self.assertIsNotNone(engine.risk_manager)
            self.assertIsNotNone(engine.trade_executor)
            self.assertIsNotNone(engine.notification_manager)
            
            # 验证初始化调用
            mock_data_instance.initialize.assert_called_once()
            mock_notification_instance.initialize.assert_called_once()
        
        self.loop.run_until_complete(test_init())
    
    @patch('src.core.engine.DataManager')
    @patch('src.core.engine.StockMonitor')
    @patch('src.core.engine.PressureSupportStrategy')
    @patch('src.core.engine.NotificationManager')
    def test_trading_engine_signal_generation(self, mock_notification, mock_strategy, mock_monitor, mock_data):
        """测试交易信号生成流程"""
        # 模拟组件
        mock_strategy_instance = AsyncMock()
        mock_strategy_instance.generate_signal.return_value = self.test_trade_signal
        mock_strategy.return_value = mock_strategy_instance
        
        mock_notification_instance = AsyncMock()
        mock_notification_instance.initialize.return_value = True
        mock_notification_instance.notify_trade_signal.return_value = True
        mock_notification.return_value = mock_notification_instance
        
        engine = TradingEngine(self.mock_config)
        engine.strategy = mock_strategy_instance
        engine.risk_manager = RiskManager(self.mock_config)
        engine.trade_executor = TradeExecutor(self.mock_config)
        engine.notification_manager = mock_notification_instance
        
        async def test_signal_generation():
            await engine._generate_trade_signals()
            
            # 验证信号生成和执行
            self.assertEqual(engine.stats['signals_generated'], 2)  # 两只股票
            self.assertEqual(engine.stats['trades_executed'], 2)
            self.assertEqual(engine.stats['notifications_sent'], 2)
            
            # 验证策略调用
            self.assertEqual(mock_strategy_instance.generate_signal.call_count, 2)
        
        self.loop.run_until_complete(test_signal_generation())
    
    @patch('src.core.engine.DataManager')
    @patch('src.core.engine.StockMonitor')
    @patch('src.core.engine.PressureSupportStrategy')
    @patch('src.core.engine.NotificationManager')
    def test_trading_engine_risk_rejection(self, mock_notification, mock_strategy, mock_monitor, mock_data):
        """测试风险检查拒绝交易"""
        # 创建高风险信号
        high_risk_signal = TradeSignal(
            symbol='000001.SZ',
            action=TradeAction.BUY,
            price=100.0,  # 高价格
            quantity=1000,  # 大数量
            confidence=0.3,  # 低信心度
            reason='高风险测试',
            timestamp=datetime.now(),
            strategy='test'
        )
        
        mock_strategy_instance = AsyncMock()
        mock_strategy_instance.generate_signal.return_value = high_risk_signal
        mock_strategy.return_value = mock_strategy_instance
        
        engine = TradingEngine(self.mock_config)
        engine.strategy = mock_strategy_instance
        engine.risk_manager = RiskManager(self.mock_config)
        engine.trade_executor = TradeExecutor(self.mock_config)
        
        async def test_risk_rejection():
            await engine._generate_trade_signals()
            
            # 信号应该被生成但交易被拒绝
            self.assertEqual(engine.stats['signals_generated'], 2)
            self.assertEqual(engine.stats['trades_executed'], 0)  # 被风险检查拒绝
        
        self.loop.run_until_complete(test_risk_rejection())
    
    @patch('src.core.engine.DataManager')
    @patch('src.core.engine.StockMonitor')
    @patch('src.core.engine.PressureSupportStrategy')
    @patch('src.core.engine.NotificationManager')
    def test_trading_engine_alert_handling(self, mock_notification, mock_strategy, mock_monitor, mock_data):
        """测试市场预警处理"""
        mock_notification_instance = AsyncMock()
        mock_notification_instance.notify_market_alert.return_value = True
        mock_notification.return_value = mock_notification_instance
        
        engine = TradingEngine(self.mock_config)
        engine.notification_manager = mock_notification_instance
        
        async def test_alert_handling():
            await engine._handle_market_alert(self.test_market_alert)
            
            self.assertEqual(engine.stats['alerts_triggered'], 1)
            self.assertEqual(engine.stats['notifications_sent'], 1)
            
            # 验证通知调用
            mock_notification_instance.notify_market_alert.assert_called_once_with(self.test_market_alert)
        
        self.loop.run_until_complete(test_alert_handling())
    
    def test_trading_engine_status_reporting(self):
        """测试引擎状态报告"""
        engine = TradingEngine(self.mock_config)
        engine.start_time = datetime.now() - timedelta(hours=2)
        engine.stats['signals_generated'] = 10
        engine.stats['trades_executed'] = 8
        
        status = engine.get_engine_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn('is_running', status)
        self.assertIn('start_time', status)
        self.assertIn('uptime', status)
        self.assertIn('stats', status)
        
        self.assertEqual(status['stats']['signals_generated'], 10)
        self.assertEqual(status['stats']['trades_executed'], 8)
    
    @patch('src.core.engine.DataManager')
    @patch('src.core.engine.StockMonitor')
    @patch('src.core.engine.PressureSupportStrategy')
    @patch('src.core.engine.NotificationManager')
    def test_trading_engine_startup_shutdown(self, mock_notification, mock_strategy, mock_monitor, mock_data):
        """测试引擎启动和关闭"""
        # 模拟组件
        mock_data_instance = AsyncMock()
        mock_data.return_value = mock_data_instance
        
        mock_monitor_instance = AsyncMock()
        mock_monitor.return_value = mock_monitor_instance
        
        mock_notification_instance = AsyncMock()
        mock_notification_instance.initialize.return_value = True
        mock_notification.return_value = mock_notification_instance
        
        engine = TradingEngine(self.mock_config)
        
        async def test_startup_shutdown():
            # 初始化
            await engine.initialize()
            
            # 启动（模拟短暂运行）
            engine.is_running = True
            engine.start_time = datetime.now()
            
            # 停止
            await engine.stop()
            
            self.assertFalse(engine.is_running)
            
            # 验证组件停止调用
            mock_monitor_instance.stop_monitoring.assert_called_once()
            mock_data_instance.close.assert_called_once()
            mock_notification_instance.close.assert_called_once()
        
        self.loop.run_until_complete(test_startup_shutdown())
    
    def test_trading_engine_error_handling(self):
        """测试引擎错误处理"""
        engine = TradingEngine(self.mock_config)
        
        # 模拟组件初始化失败
        with patch('src.core.engine.DataManager') as mock_data:
            mock_data.side_effect = Exception("初始化失败")
            
            async def test_error_handling():
                with self.assertRaises(Exception):
                    await engine.initialize()
            
            self.loop.run_until_complete(test_error_handling())
    
    def test_trading_engine_performance_tracking(self):
        """测试引擎性能跟踪"""
        engine = TradingEngine(self.mock_config)
        
        # 模拟一些统计数据
        engine.stats['signals_generated'] = 100
        engine.stats['trades_executed'] = 85
        engine.stats['alerts_triggered'] = 15
        engine.stats['notifications_sent'] = 100
        
        # 计算成功率
        execution_rate = engine.stats['trades_executed'] / engine.stats['signals_generated']
        
        self.assertEqual(execution_rate, 0.85)
        self.assertEqual(engine.stats['alerts_triggered'], 15)


if __name__ == '__main__':
    unittest.main()