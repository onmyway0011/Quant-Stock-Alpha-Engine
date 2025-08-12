#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础使用示例

展示如何使用量化股票交易系统的核心功能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.stock_crawler import EnhancedDataProvider
from src.ai_analysis import TradingAgentsAdapter
from src.core.config import ConfigManager
from src.core.monitor import StockMonitor
from src.strategy.pressure_support_strategy import PressureSupportStrategy


async def basic_stock_analysis_example():
    """基础股票分析示例"""
    print("🔍 基础股票分析示例")
    print("=" * 50)
    
    # 1. 初始化配置
    config = ConfigManager()
    
    # 2. 创建增强数据提供者
    provider = EnhancedDataProvider(config.get_config())
    
    # 3. 分析单只股票
    symbol = '000001.SZ'  # 平安银行
    print(f"\n📊 分析股票: {symbol}")
    
    try:
        # 获取增强股票数据
        stock_data = await provider.get_enhanced_stock_data(
            symbol=symbol,
            include_indicators=True,
            include_patterns=True
        )
        
        if stock_data:
            print(f"\n=== {stock_data.basic_data.name} 分析结果 ===")
            print(f"当前价格: ¥{stock_data.basic_data.current_price:.2f}")
            print(f"涨跌幅: {stock_data.basic_data.change_percent:.2f}%")
            print(f"成交量: {stock_data.basic_data.volume:,}")
            
            # 技术指标分析
            print(f"\n📈 技术指标 ({len(stock_data.indicators)}个):")
            for name, indicator in list(stock_data.indicators.items())[:5]:  # 显示前5个
                if hasattr(indicator, 'values') and len(indicator.values) > 0:
                    latest_value = indicator.values[-1]
                    if hasattr(latest_value, '__len__') and len(latest_value) > 1:
                        print(f"  {name}: {latest_value[0]:.4f}")
                    else:
                        print(f"  {name}: {latest_value:.4f}")
            
            # K线形态分析
            print(f"\n📊 K线形态 ({len(stock_data.patterns)}个):")
            pattern_count = 0
            for name, pattern in stock_data.patterns.items():
                if pattern.signals and pattern_count < 3:  # 显示前3个有信号的形态
                    print(f"  {pattern.chinese_name}: {pattern.signals[-1]}")
                    pattern_count += 1
            
            # 分析摘要
            summary = stock_data.analysis_summary
            print(f"\n📋 分析摘要:")
            print(f"  整体情绪: {summary.get('overall_sentiment', 'neutral').upper()}")
            print(f"  风险等级: {summary.get('risk_level', 'medium').upper()}")
            
            if 'recommendations' in summary:
                print(f"\n💡 投资建议:")
                for rec in summary['recommendations'][:3]:  # 显示前3个建议
                    print(f"  • {rec}")
        else:
            print(f"❌ 无法获取{symbol}的数据")
            
    except Exception as e:
        print(f"❌ 分析失败: {e}")
    
    finally:
        await provider.close()


async def batch_analysis_example():
    """批量分析示例"""
    print("\n\n📊 批量股票分析示例")
    print("=" * 50)
    
    # 初始化
    config = ConfigManager()
    provider = EnhancedDataProvider(config.get_config())
    
    # 要分析的股票列表
    symbols = ['000001.SZ', '000002.SZ', '600519.SH', '600036.SH', '000858.SZ']
    
    try:
        # 批量获取数据
        print(f"\n🔄 正在分析 {len(symbols)} 只股票...")
        results = await provider.get_multiple_enhanced_data(
            symbols=symbols,
            include_indicators=True,
            include_patterns=False  # 为了速度，跳过形态分析
        )
        
        print(f"\n📈 批量分析结果:")
        print("-" * 80)
        print(f"{'股票代码':<12} {'股票名称':<12} {'当前价格':<10} {'涨跌幅':<8} {'情绪':<8} {'评分':<6}")
        print("-" * 80)
        
        for symbol, data in results.items():
            name = data.basic_data.name[:8] + '...' if len(data.basic_data.name) > 8 else data.basic_data.name
            price = f"¥{data.basic_data.current_price:.2f}"
            change = f"{data.basic_data.change_percent:+.2f}%"
            sentiment = data.analysis_summary.get('overall_sentiment', 'neutral')[:6]
            score = data.analysis_summary.get('scores', {}).get('overall', 50)
            
            print(f"{symbol:<12} {name:<12} {price:<10} {change:<8} {sentiment:<8} {score:<6.1f}")
        
        # 市场概览
        overview = await provider.get_market_overview(list(results.keys()))
        if overview and 'market_sentiment' in overview:
            print(f"\n📊 市场概览:")
            sentiment = overview['market_sentiment']
            print(f"  看涨股票: {sentiment['bullish']} 只")
            print(f"  看跌股票: {sentiment['bearish']} 只")
            print(f"  中性股票: {sentiment['neutral']} 只")
            print(f"  看涨比例: {sentiment['bullish_ratio']:.1%}")
            
            if 'market_performance' in overview:
                perf = overview['market_performance']
                print(f"  平均涨跌: {perf['avg_change_percent']:+.2f}%")
        
    except Exception as e:
        print(f"❌ 批量分析失败: {e}")
    
    finally:
        await provider.close()


async def ai_analysis_example():
    """AI分析示例（需要配置API密钥）"""
    print("\n\n🤖 AI智能分析示例")
    print("=" * 50)
    
    try:
        # 创建AI分析适配器（使用模拟模式）
        from src.ai_analysis.trading_agents_adapter import MockTradingAgentsAdapter
        
        ai_adapter = MockTradingAgentsAdapter({
            'llm_provider': 'dashscope',
            'deep_think_llm': 'qwen-plus'
        })
        
        symbol = '000001.SZ'
        print(f"\n🧠 AI分析股票: {symbol}")
        
        # 执行AI分析
        result = await ai_adapter.analyze_stock(symbol)
        
        if result:
            print(f"\n=== AI分析结果 ===")
            print(f"股票代码: {result.symbol}")
            print(f"分析日期: {result.analysis_date}")
            print(f"AI决策: {result.decision['action']}")
            print(f"信心度: {result.confidence:.1%}")
            print(f"风险评分: {result.risk_score:.1%}")
            print(f"推理过程: {result.reasoning}")
            
            print(f"\n💡 AI投资建议:")
            for rec in result.recommendations:
                print(f"  • {rec}")
            
            # 智能体报告摘要
            print(f"\n🤖 智能体分析:")
            for agent, report in result.agent_reports.items():
                if report and isinstance(report, dict):
                    if 'recommendation' in report:
                        print(f"  {agent}: {report['recommendation']}")
                    elif 'trend' in report:
                        print(f"  {agent}: {report['trend']}")
                    elif 'sentiment' in report:
                        print(f"  {agent}: {report['sentiment']}")
        else:
            print("❌ AI分析失败")
            
    except Exception as e:
        print(f"❌ AI分析异常: {e}")
        print("💡 提示: 需要安装AI依赖并配置API密钥才能使用真实AI分析功能")


async def strategy_example():
    """交易策略示例"""
    print("\n\n📈 交易策略示例")
    print("=" * 50)
    
    try:
        # 初始化配置和策略
        config = ConfigManager()
        strategy = PressureSupportStrategy(config.get_config())
        
        symbol = '000001.SZ'
        print(f"\n⚡ 生成交易信号: {symbol}")
        
        # 生成交易信号
        signal = await strategy.generate_signal(symbol)
        
        if signal:
            print(f"\n=== 交易信号 ===")
            print(f"股票代码: {signal.symbol}")
            print(f"交易动作: {signal.action}")
            print(f"建议价格: ¥{signal.price:.2f}")
            print(f"建议数量: {signal.quantity} 股")
            print(f"信心度: {signal.confidence:.1%}")
            print(f"信号原因: {signal.reason}")
            
            if signal.stop_loss:
                print(f"止损价格: ¥{signal.stop_loss:.2f}")
            if signal.take_profit:
                print(f"止盈价格: ¥{signal.take_profit:.2f}")
        else:
            print("❌ 未生成交易信号")
            
        # 获取策略信息
        info = strategy.get_strategy_info()
        print(f"\n📋 策略信息:")
        print(f"  策略名称: {info['name']}")
        print(f"  策略描述: {info['description']}")
        print(f"  分析周期: {info['parameters']['analysis_period']} 个月")
        
    except Exception as e:
        print(f"❌ 策略分析失败: {e}")


async def monitoring_example():
    """股票监控示例"""
    print("\n\n👁️ 股票监控示例")
    print("=" * 50)
    
    try:
        # 初始化监控器
        config = ConfigManager()
        monitor = StockMonitor(config.get_config())
        
        # 添加预警回调
        def alert_callback(alert):
            print(f"🚨 预警: {alert['symbol']} - {alert['type']} - {alert['message']}")
        
        monitor.add_alert_callback(alert_callback)
        
        print("\n🔍 开始监控股票...")
        
        # 模拟监控（实际使用中会持续运行）
        await monitor.start_monitoring()
        
        # 等待一段时间让监控运行
        await asyncio.sleep(2)
        
        # 获取监控状态
        status = monitor.get_status()
        print(f"\n📊 监控状态:")
        print(f"  监控股票数: {status['monitored_stocks']}")
        print(f"  运行状态: {status['status']}")
        print(f"  预警队列: {status['alert_queue_size']}")
        
        # 获取最近预警
        recent_alerts = monitor.get_recent_alerts(5)
        if recent_alerts:
            print(f"\n🔔 最近预警:")
            for alert in recent_alerts:
                print(f"  {alert['timestamp']}: {alert['symbol']} - {alert['message']}")
        
        await monitor.stop_monitoring()
        
    except Exception as e:
        print(f"❌ 监控示例失败: {e}")


def print_usage_info():
    """打印使用说明"""
    print("🚀 量化股票交易系统 - 基础使用示例")
    print("=" * 60)
    print("\n本示例展示了系统的核心功能:")
    print("  1. 📊 基础股票分析 - 获取实时数据和技术指标")
    print("  2. 📈 批量股票分析 - 同时分析多只股票")
    print("  3. 🤖 AI智能分析 - 多智能体协作分析")
    print("  4. ⚡ 交易策略 - 生成买卖信号")
    print("  5. 👁️ 股票监控 - 实时监控和预警")
    print("\n💡 使用提示:")
    print("  - 确保已安装所有依赖: pip install -r requirements.txt")
    print("  - 配置API密钥以获得完整功能")
    print("  - 查看config.yaml了解配置选项")
    print("\n⚠️ 免责声明:")
    print("  本系统仅供学习研究使用，不构成投资建议")
    print("  投资有风险，入市需谨慎！")


async def main():
    """主函数"""
    print_usage_info()
    
    try:
        # 运行所有示例
        await basic_stock_analysis_example()
        await batch_analysis_example()
        await ai_analysis_example()
        await strategy_example()
        await monitoring_example()
        
        print("\n\n🎉 所有示例运行完成！")
        print("\n📚 更多信息:")
        print("  - 查看 README.md 了解详细使用说明")
        print("  - 访问 http://127.0.0.1:8080 使用Web配置界面")
        print("  - 运行 scripts/run_tests.py 进行系统测试")
        
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，示例结束")
    except Exception as e:
        print(f"\n\n❌ 示例运行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())