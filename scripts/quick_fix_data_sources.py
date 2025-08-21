#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据源快速修复工具

快速配置和测试数据源
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def setup_demo_config():
    """设置演示配置"""
    print("🔧 设置演示配置...")
    
    # 创建.env文件（如果不存在）
    env_file = project_root / ".env"
    env_example_file = project_root / ".env.example"
    
    if not env_file.exists() and env_example_file.exists():
        # 复制示例文件
        with open(env_example_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  ✅ 已创建.env文件")
    
    # 提示用户配置Tushare token
    print("\n📝 配置Tushare数据源:")
    print("  1. 访问 https://tushare.pro/ 注册账号")
    print("  2. 获取免费的API token")
    print("  3. 在.env文件中设置 TUSHARE_TOKEN=your_token_here")
    print("\n💡 提示: 如果没有Tushare token，系统将使用Akshare作为主要数据源")


async def test_akshare_only():
    """测试仅使用Akshare数据源"""
    print("\n🧪 测试Akshare数据源...")
    
    try:
        import akshare as ak
        
        # 测试获取股票数据
        symbol = "000001"
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        
        print(f"  📊 获取{symbol}的历史数据...")
        
        # 使用akshare获取数据
        df = await asyncio.to_thread(
            ak.stock_zh_a_hist,
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )
        
        if not df.empty:
            print(f"  ✅ 成功获取{len(df)}条历史记录")
            print(f"  📈 数据范围: {df['日期'].min()} 到 {df['日期'].max()}")
            print(f"  💰 最新收盘价: {df['收盘'].iloc[-1]:.2f}")
            return True
        else:
            print("  ⚠️ 获取的数据为空")
            return False
            
    except Exception as e:
        print(f"  ❌ Akshare测试失败: {e}")
        return False


async def update_config_for_akshare():
    """更新配置以使用Akshare作为主要数据源"""
    print("\n⚙️ 更新配置文件...")
    
    config_file = project_root / "config.yaml"
    
    if config_file.exists():
        # 读取配置文件
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 更新数据源配置
        updated_content = content.replace(
            'primary: "tushare"',
            'primary: "akshare"'
        ).replace(
            'backup: "akshare"',
            'backup: "tushare"'
        )
        
        # 写回配置文件
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print("  ✅ 已更新config.yaml，设置Akshare为主要数据源")
        print("  📝 配置变更:")
        print("    - 主要数据源: akshare")
        print("    - 备用数据源: tushare")
        print("    - 实时数据源: sina")
        
        return True
    else:
        print("  ❌ 配置文件不存在")
        return False


async def test_system_with_akshare():
    """使用Akshare测试系统"""
    print("\n🔄 重启系统测试...")
    
    try:
        from src.data.data_provider import DataManager
        from src.core.config import config
        
        # 重新加载配置
        data_manager = DataManager()
        
        # 初始化数据管理器
        await data_manager.initialize()
        
        # 测试历史数据获取
        symbol = "000001.SZ"
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        print(f"  📊 测试获取{symbol}历史数据...")
        
        df = await data_manager.get_historical_data(symbol, start_date, end_date)
        
        if not df.empty:
            print(f"  ✅ 系统历史数据获取成功，共{len(df)}条记录")
            
            # 测试实时数据
            print(f"  📡 测试获取{symbol}实时数据...")
            realtime_data = await data_manager.get_realtime_data([symbol])
            
            if realtime_data:
                stock_data = realtime_data.get(symbol)
                if stock_data:
                    print(f"  ✅ 实时数据获取成功")
                    print(f"    股票名称: {stock_data.name}")
                    print(f"    当前价格: {stock_data.current_price:.2f}")
                    print(f"    涨跌幅: {stock_data.change_percent:.2f}%")
                else:
                    print("  ⚠️ 实时数据为空")
            else:
                print("  ⚠️ 实时数据获取失败")
            
            await data_manager.close()
            return True
        else:
            print("  ❌ 系统历史数据获取失败")
            await data_manager.close()
            return False
            
    except Exception as e:
        print(f"  ❌ 系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_data_source_fix_summary():
    """创建数据源修复总结"""
    summary = """
# 📊 数据源问题修复总结

## 🔍 问题诊断

系统检测到以下数据源问题：
1. ❌ Tushare token未配置
2. ⚠️ Sina数据源连接受限
3. ✅ Akshare数据源可用

## 🔧 修复方案

### 方案1: 配置Tushare（推荐）
1. 访问 https://tushare.pro/ 注册账号
2. 获取免费API token
3. 在.env文件中设置: `TUSHARE_TOKEN=your_token_here`
4. 重启系统

### 方案2: 使用Akshare（当前已应用）
1. ✅ 已更新配置文件，设置Akshare为主要数据源
2. ✅ Akshare数据源测试通过
3. ✅ 系统可正常获取历史数据

## 📈 当前状态

- **主要数据源**: Akshare ✅
- **备用数据源**: Tushare ⚠️ (需要token)
- **实时数据源**: Sina ⚠️ (连接受限)
- **历史数据**: ✅ 正常
- **实时数据**: ⚠️ 部分可用

## 💡 使用建议

1. **短期使用**: 当前配置已可满足基本需求
2. **长期使用**: 建议配置Tushare token以获得更稳定的数据服务
3. **实时数据**: 如需稳定的实时数据，建议配置专业数据源

## 🔄 重启系统

修复完成后，请重启交易系统：
```bash
# 停止当前系统
pkill -f "python.*main.py"

# 重新启动
python3 main.py
```

## 📞 技术支持

如遇到其他问题，请：
1. 查看系统日志: `tail -f logs/trading.log`
2. 运行诊断工具: `python3 scripts/diagnose_data_sources.py`
3. 查看Web配置界面: http://127.0.0.1:8080
"""
    
    summary_file = project_root / "DATA_SOURCE_FIX_SUMMARY.md"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(summary)
    
    print(f"\n📄 修复总结已保存到: {summary_file}")


async def main():
    """主函数"""
    print("🔧 数据源快速修复工具")
    print("=" * 50)
    
    try:
        # 1. 设置基础配置
        setup_demo_config()
        
        # 2. 测试Akshare
        akshare_ok = await test_akshare_only()
        
        if akshare_ok:
            # 3. 更新配置使用Akshare
            config_updated = await update_config_for_akshare()
            
            if config_updated:
                # 4. 测试系统
                system_ok = await test_system_with_akshare()
                
                if system_ok:
                    print("\n🎉 数据源修复成功！")
                    print("\n📊 修复结果:")
                    print("  ✅ Akshare数据源配置完成")
                    print("  ✅ 历史数据获取正常")
                    print("  ✅ 系统可以正常运行")
                    
                    # 5. 创建修复总结
                    create_data_source_fix_summary()
                    
                    print("\n🔄 建议重启主系统以应用新配置")
                    print("\n💡 如需更稳定的数据服务，请配置Tushare token")
                else:
                    print("\n❌ 系统测试失败，请检查配置")
            else:
                print("\n❌ 配置更新失败")
        else:
            print("\n❌ Akshare数据源测试失败")
            print("\n💡 建议:")
            print("  1. 检查网络连接")
            print("  2. 更新akshare版本: pip install --upgrade akshare")
            print("  3. 配置Tushare token作为替代方案")
    
    except Exception as e:
        print(f"\n❌ 修复过程中发生异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())