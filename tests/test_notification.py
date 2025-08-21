#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通知模块测试

测试企业微信通知功能
"""

import unittest
import asyncio
import json
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from src.notification.wecom_notifier import (
    WeComNotifier, NotificationManager, MessageType
)
from src.models.models import TradeSignal, MarketAlert, TradeAction, AlertLevel


class TestNotification(unittest.TestCase):
    """通知模块测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        self.webhook_url = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test_key'
        
        # 模拟配置
        self.mock_config = MagicMock()
        self.mock_config.notification.wecom_enabled = True
        self.mock_config.notification.wecom_webhook_url = self.webhook_url
        self.mock_config.notification.mention_all = False
        
        # 创建测试数据
        self.test_trade_signal = TradeSignal(
            symbol='000001.SZ',
            action=TradeAction.BUY,
            price=12.50,
            quantity=1000,
            confidence=0.85,
            reason='突破阻力位',
            timestamp=datetime.now(),
            strategy='pressure_support_strategy'
        )
        
        self.test_market_alert = MarketAlert(
            symbol='600519.SH',
            alert_type='price_volatility',
            level=AlertLevel.HIGH,
            message='价格波动率异常: 5.2%',
            current_value=0.052,
            threshold=0.03,
            timestamp=datetime.now()
        )
    
    def tearDown(self):
        """测试后清理"""
        self.loop.close()
    
    def test_wecom_notifier_initialization(self):
        """测试企微通知器初始化"""
        notifier = WeComNotifier(self.webhook_url, mention_all=True)
        
        self.assertEqual(notifier.webhook_url, self.webhook_url)
        self.assertTrue(notifier.mention_all)
        self.assertIsNone(notifier.session)
    
    @patch('aiohttp.ClientSession')
    def test_wecom_notifier_initialize_success(self, mock_session_class):
        """测试企微通知器成功初始化"""
        # 模拟成功的HTTP响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {'errcode': 0, 'errmsg': 'ok'}
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None
        
        mock_session = AsyncMock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        notifier = WeComNotifier(self.webhook_url)
        
        async def test_init():
            result = await notifier.initialize()
            self.assertTrue(result)
            
            # 验证发送了测试消息
            mock_session.post.assert_called_once()
            call_args = mock_session.post.call_args
            self.assertEqual(call_args[0][0], self.webhook_url)
        
        self.loop.run_until_complete(test_init())
    
    @patch('aiohttp.ClientSession')
    def test_wecom_notifier_initialize_failure(self, mock_session_class):
        """测试企微通知器初始化失败"""
        # 模拟失败的HTTP响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {'errcode': 40001, 'errmsg': 'invalid key'}
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None
        
        mock_session = AsyncMock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        notifier = WeComNotifier(self.webhook_url)
        
        async def test_init_failure():
            result = await notifier.initialize()
            self.assertFalse(result)
        
        self.loop.run_until_complete(test_init_failure())
    
    @patch('aiohttp.ClientSession')
    def test_wecom_send_trade_signal(self, mock_session_class):
        """测试发送交易信号"""
        # 模拟成功响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {'errcode': 0, 'errmsg': 'ok'}
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None
        
        mock_session = AsyncMock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        notifier = WeComNotifier(self.webhook_url)
        notifier.session = mock_session
        
        async def test_send_signal():
            result = await notifier.send_trade_signal(self.test_trade_signal)
            self.assertTrue(result)
            
            # 验证消息格式
            mock_session.post.assert_called()
            call_args = mock_session.post.call_args
            message_data = call_args[1]['json']
            
            self.assertEqual(message_data['msgtype'], 'markdown')
            self.assertIn('交易信号', message_data['markdown']['content'])
            self.assertIn('000001.SZ', message_data['markdown']['content'])
            self.assertIn('BUY', message_data['markdown']['content'])
        
        self.loop.run_until_complete(test_send_signal())
    
    @patch('aiohttp.ClientSession')
    def test_wecom_send_market_alert(self, mock_session_class):
        """测试发送市场预警"""
        # 模拟成功响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {'errcode': 0, 'errmsg': 'ok'}
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None
        
        mock_session = AsyncMock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        notifier = WeComNotifier(self.webhook_url)
        notifier.session = mock_session
        
        async def test_send_alert():
            result = await notifier.send_market_alert(self.test_market_alert)
            self.assertTrue(result)
            
            # 验证消息格式
            mock_session.post.assert_called()
            call_args = mock_session.post.call_args
            message_data = call_args[1]['json']
            
            self.assertEqual(message_data['msgtype'], 'markdown')
            self.assertIn('市场预警', message_data['markdown']['content'])
            self.assertIn('600519.SH', message_data['markdown']['content'])
            self.assertIn('HIGH', message_data['markdown']['content'])
        
        self.loop.run_until_complete(test_send_alert())
    
    @patch('aiohttp.ClientSession')
    def test_wecom_send_system_status(self, mock_session_class):
        """测试发送系统状态"""
        # 模拟成功响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {'errcode': 0, 'errmsg': 'ok'}
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None
        
        mock_session = AsyncMock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        notifier = WeComNotifier(self.webhook_url)
        notifier.session = mock_session
        
        status = {
            'system_name': '量化交易系统',
            'status': '运行中',
            'uptime': '2小时15分钟',
            'monitored_stocks': 5,
            'active_strategies': 1,
            'today_trades': 3,
            'healthy': True
        }
        
        async def test_send_status():
            result = await notifier.send_system_status(status)
            self.assertTrue(result)
            
            # 验证消息格式
            mock_session.post.assert_called()
            call_args = mock_session.post.call_args
            message_data = call_args[1]['json']
            
            self.assertEqual(message_data['msgtype'], 'markdown')
            self.assertIn('系统状态更新', message_data['markdown']['content'])
            self.assertIn('运行中', message_data['markdown']['content'])
        
        self.loop.run_until_complete(test_send_status())
    
    @patch('aiohttp.ClientSession')
    def test_wecom_send_daily_summary(self, mock_session_class):
        """测试发送每日总结"""
        # 模拟成功响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {'errcode': 0, 'errmsg': 'ok'}
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None
        
        mock_session = AsyncMock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        notifier = WeComNotifier(self.webhook_url)
        notifier.session = mock_session
        
        summary = {
            'date': '2024-01-15',
            'total_trades': 8,
            'buy_trades': 5,
            'sell_trades': 3,
            'total_pnl': 2350.00,
            'win_rate': 0.75,
            'max_profit': 800.00,
            'max_loss': -200.00,
            'positions_count': 3,
            'cash_balance': 50000.00,
            'total_assets': 75000.00
        }
        
        async def test_send_summary():
            result = await notifier.send_daily_summary(summary)
            self.assertTrue(result)
            
            # 验证消息格式
            mock_session.post.assert_called()
            call_args = mock_session.post.call_args
            message_data = call_args[1]['json']
            
            self.assertEqual(message_data['msgtype'], 'markdown')
            self.assertIn('每日交易总结', message_data['markdown']['content'])
            self.assertIn('¥2,350.00', message_data['markdown']['content'])
        
        self.loop.run_until_complete(test_send_summary())
    
    @patch('aiohttp.ClientSession')
    def test_wecom_send_custom_message(self, mock_session_class):
        """测试发送自定义消息"""
        # 模拟成功响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {'errcode': 0, 'errmsg': 'ok'}
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None
        
        mock_session = AsyncMock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        notifier = WeComNotifier(self.webhook_url)
        notifier.session = mock_session
        
        async def test_send_custom():
            # 测试文本消息
            result = await notifier.send_custom_message('测试消息', MessageType.TEXT)
            self.assertTrue(result)
            
            # 测试Markdown消息
            result = await notifier.send_custom_message('## 测试标题\n测试内容', MessageType.MARKDOWN)
            self.assertTrue(result)
            
            # 验证调用次数
            self.assertEqual(mock_session.post.call_count, 2)
        
        self.loop.run_until_complete(test_send_custom())
    
    def test_wecom_message_building(self):
        """测试消息构建"""
        notifier = WeComNotifier(self.webhook_url)
        
        # 测试交易信号消息构建
        message = notifier._build_trade_signal_message(self.test_trade_signal)
        
        self.assertEqual(message['msgtype'], 'markdown')
        self.assertIn('交易信号', message['markdown']['content'])
        self.assertIn('000001.SZ', message['markdown']['content'])
        self.assertIn('BUY', message['markdown']['content'])
        self.assertIn('¥12.50', message['markdown']['content'])
        self.assertIn('1,000股', message['markdown']['content'])
        
        # 测试市场预警消息构建
        alert_message = notifier._build_market_alert_message(self.test_market_alert)
        
        self.assertEqual(alert_message['msgtype'], 'markdown')
        self.assertIn('市场预警', alert_message['markdown']['content'])
        self.assertIn('600519.SH', alert_message['markdown']['content'])
        self.assertIn('HIGH', alert_message['markdown']['content'])
    
    def test_wecom_confidence_color(self):
        """测试信心度颜色映射"""
        notifier = WeComNotifier(self.webhook_url)
        
        # 测试不同信心度的颜色
        high_confidence_color = notifier._get_confidence_color(0.9)
        medium_confidence_color = notifier._get_confidence_color(0.7)
        low_confidence_color = notifier._get_confidence_color(0.4)
        
        self.assertEqual(high_confidence_color, 'info')
        self.assertEqual(medium_confidence_color, 'warning')
        self.assertEqual(low_confidence_color, 'comment')
    
    @patch('aiohttp.ClientSession')
    def test_wecom_error_handling(self, mock_session_class):
        """测试企微通知错误处理"""
        # 模拟网络错误
        mock_session = AsyncMock()
        mock_session.post.side_effect = Exception('网络错误')
        mock_session_class.return_value = mock_session
        
        notifier = WeComNotifier(self.webhook_url)
        notifier.session = mock_session
        
        async def test_error_handling():
            result = await notifier.send_trade_signal(self.test_trade_signal)
            self.assertFalse(result)
        
        self.loop.run_until_complete(test_error_handling())
    
    @patch('aiohttp.ClientSession')
    def test_wecom_http_error_handling(self, mock_session_class):
        """测试HTTP错误处理"""
        # 模拟HTTP错误响应
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None
        
        mock_session = AsyncMock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        notifier = WeComNotifier(self.webhook_url)
        notifier.session = mock_session
        
        async def test_http_error():
            result = await notifier.send_trade_signal(self.test_trade_signal)
            self.assertFalse(result)
        
        self.loop.run_until_complete(test_http_error())
    
    def test_notification_manager_initialization(self):
        """测试通知管理器初始化"""
        manager = NotificationManager()
        
        self.assertTrue(hasattr(manager, 'enabled'))
        self.assertTrue(manager.enabled)
        self.assertIsNone(manager.wecom_notifier)
    
    @patch('src.notification.wecom_notifier.WeComNotifier')
    def test_notification_manager_initialize_success(self, mock_notifier_class):
        """测试通知管理器成功初始化"""
        # 模拟WeComNotifier
        mock_notifier = AsyncMock()
        mock_notifier.initialize.return_value = True
        mock_notifier_class.return_value = mock_notifier
        
        manager = NotificationManager()
        
        async def test_init():
            result = await manager.initialize()
            self.assertTrue(result)
            self.assertIsNotNone(manager.wecom_notifier)
        
        self.loop.run_until_complete(test_init())
    
    def test_notification_manager_disabled(self):
        """测试通知管理器禁用状态"""
        # 禁用通知
        self.mock_config.notification.wecom_enabled = False
        
        manager = NotificationManager()
        
        async def test_disabled():
            result = await manager.initialize()
            self.assertTrue(result)  # 禁用状态下也应该返回True
            
            # 发送通知应该直接返回True（不实际发送）
            result = await manager.notify_trade_signal(self.test_trade_signal)
            self.assertTrue(result)
        
        self.loop.run_until_complete(test_disabled())
    
    def test_notification_manager_missing_webhook(self):
        """测试缺少Webhook URL的情况"""
        # 清空Webhook URL
        self.mock_config.notification.wecom_webhook_url = ''
        
        manager = NotificationManager()
        
        async def test_missing_webhook():
            result = await manager.initialize()
            self.assertFalse(result)
        
        self.loop.run_until_complete(test_missing_webhook())
    
    @patch('src.notification.wecom_notifier.WeComNotifier')
    def test_notification_manager_all_methods(self, mock_notifier_class):
        """测试通知管理器所有通知方法"""
        # 模拟WeComNotifier
        mock_notifier = AsyncMock()
        mock_notifier.initialize.return_value = True
        mock_notifier.send_trade_signal.return_value = True
        mock_notifier.send_market_alert.return_value = True
        mock_notifier.send_system_status.return_value = True
        mock_notifier.send_daily_summary.return_value = True
        mock_notifier.send_custom_message.return_value = True
        mock_notifier_class.return_value = mock_notifier
        
        manager = NotificationManager()
        
        async def test_all_methods():
            await manager.initialize()
            
            # 测试所有通知方法
            result1 = await manager.notify_trade_signal(self.test_trade_signal)
            result2 = await manager.notify_market_alert(self.test_market_alert)
            result3 = await manager.notify_system_status({'status': 'running'})
            result4 = await manager.notify_daily_summary({'total_pnl': 1000})
            result5 = await manager.send_custom_notification('测试消息')
            
            self.assertTrue(all([result1, result2, result3, result4, result5]))
            
            # 验证所有方法都被调用
            mock_notifier.send_trade_signal.assert_called_once()
            mock_notifier.send_market_alert.assert_called_once()
            mock_notifier.send_system_status.assert_called_once()
            mock_notifier.send_daily_summary.assert_called_once()
            mock_notifier.send_custom_message.assert_called_once()
        
        self.loop.run_until_complete(test_all_methods())
    
    @patch('aiohttp.ClientSession')
    def test_wecom_mention_all_feature(self, mock_session_class):
        """测试@所有人功能"""
        # 模拟成功响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {'errcode': 0, 'errmsg': 'ok'}
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None
        
        mock_session = AsyncMock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        # 启用@所有人
        notifier = WeComNotifier(self.webhook_url, mention_all=True)
        notifier.session = mock_session
        
        async def test_mention_all():
            result = await notifier.send_trade_signal(self.test_trade_signal)
            self.assertTrue(result)
            
            # 验证消息包含@all
            call_args = mock_session.post.call_args
            message_data = call_args[1]['json']
            self.assertIn('<@all>', message_data['markdown']['content'])
        
        self.loop.run_until_complete(test_mention_all())
    
    @patch('aiohttp.ClientSession')
    def test_wecom_timeout_handling(self, mock_session_class):
        """测试超时处理"""
        # 模拟超时
        mock_session = AsyncMock()
        mock_session.post.side_effect = asyncio.TimeoutError('请求超时')
        mock_session_class.return_value = mock_session
        
        notifier = WeComNotifier(self.webhook_url)
        notifier.session = mock_session
        
        async def test_timeout():
            result = await notifier.send_trade_signal(self.test_trade_signal)
            self.assertFalse(result)
        
        self.loop.run_until_complete(test_timeout())
    
    def test_message_type_enum(self):
        """测试消息类型枚举"""
        self.assertEqual(MessageType.TEXT.value, 'text')
        self.assertEqual(MessageType.MARKDOWN.value, 'markdown')
        self.assertEqual(MessageType.IMAGE.value, 'image')
        self.assertEqual(MessageType.NEWS.value, 'news')


if __name__ == '__main__':
    unittest.main()