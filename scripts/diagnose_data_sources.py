#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据源诊断工具

用于检测和修复数据获取问题
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import config
from src.data.data_provider import DataManager, TushareProvider, AkshareProvider, SinaProvider
from src.utils.logger import get_logger


class DataSourceDiagnostic:
    """数据源诊断器"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.test_symbols = ['000001.SZ', '600519.SH', '000002.SZ']
        self.test_start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        self.test_end_date = datetime.now().strftime('%Y-%m-%d')
    
    async def diagnose_all(self) -> Dict[str, Any]:
        """诊断所有数据源"""
        print("🔍 开始数据源诊断...")
        print("=" * 60)
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'test_symbols': self.test_symbols,
            'test_period': f"{self.test_start_date} 到 {self.test_end_date}",
            'providers': {},
            'data_manager': {},
            'recommendations': []
        }
        
        # 诊断各个数据提供者
        await self._diagnose_tushare(results)
        await self._diagnose_akshare(results)
        await self._diagnose_sina(results)
        
        # 诊断数据管理器
        await self._diagnose_data_manager(results)
        
        # 生成建议
        self._generate_recommendations(results)
        
        # 显示诊断结果
        self._display_results(results)
        
        return results
    
    async def _diagnose_tushare(self, results: Dict[str, Any]):
        """诊断Tushare数据源"""
        print("\n📊 诊断Tushare数据源...")
        
        provider_result = {
            'name': 'Tushare',
            'available': False,
            'initialized': False,
            'token_configured': False,
            'realtime_test': {'success': False, 'error': None},
            'historical_test': {'success': False, 'error': None, 'records': 0},
            'basic_info_test': {'success': False, 'error': None}
        }
        
        try:
            # 检查token配置
            token = config.data.tushare_token
            provider_result['token_configured'] = bool(token)
            
            if not token:
                provider_result['error'] = "Tushare token未配置"
                print("  ❌ Tushare token未配置")
                results['providers']['tushare'] = provider_result
                return
            
            # 创建提供者实例
            provider = TushareProvider(token)
            
            # 测试初始化
            try:
                initialized = await provider.initialize()
                provider_result['initialized'] = initialized
                provider_result['available'] = provider.is_available
                
                if not initialized:
                    print("  ❌ Tushare初始化失败")
                    results['providers']['tushare'] = provider_result
                    return
                
                print("  ✅ Tushare初始化成功")
                
                # 测试实时数据
                try:
                    realtime_data = await provider.get_realtime_data([self.test_symbols[0]])
                    if realtime_data:
                        provider_result['realtime_test']['success'] = True
                        print("  ✅ 实时数据获取成功")
                    else:
                        print("  ⚠️ 实时数据获取为空")
                except Exception as e:
                    provider_result['realtime_test']['error'] = str(e)
                    print(f"  ❌ 实时数据获取失败: {e}")
                
                # 测试历史数据
                try:
                    historical_data = await provider.get_historical_data(
                        self.test_symbols[0], 
                        self.test_start_date, 
                        self.test_end_date
                    )
                    if not historical_data.empty:
                        provider_result['historical_test']['success'] = True
                        provider_result['historical_test']['records'] = len(historical_data)
                        print(f"  ✅ 历史数据获取成功，共{len(historical_data)}条记录")
                    else:
                        print("  ⚠️ 历史数据获取为空")
                except Exception as e:
                    provider_result['historical_test']['error'] = str(e)
                    print(f"  ❌ 历史数据获取失败: {e}")
                
                # 测试基本信息
                try:
                    basic_info = await provider.get_basic_info(self.test_symbols[0])
                    if basic_info:
                        provider_result['basic_info_test']['success'] = True
                        print("  ✅ 基本信息获取成功")
                    else:
                        print("  ⚠️ 基本信息获取为空")
                except Exception as e:
                    provider_result['basic_info_test']['error'] = str(e)
                    print(f"  ❌ 基本信息获取失败: {e}")
                
            except Exception as e:
                provider_result['error'] = str(e)
                print(f"  ❌ Tushare初始化异常: {e}")
        
        except Exception as e:
            provider_result['error'] = str(e)
            print(f"  ❌ Tushare诊断异常: {e}")
        
        results['providers']['tushare'] = provider_result
    
    async def _diagnose_akshare(self, results: Dict[str, Any]):
        """诊断Akshare数据源"""
        print("\n📈 诊断Akshare数据源...")
        
        provider_result = {
            'name': 'Akshare',
            'available': False,
            'initialized': False,
            'realtime_test': {'success': False, 'error': None},
            'historical_test': {'success': False, 'error': None, 'records': 0},
            'basic_info_test': {'success': False, 'error': None}
        }
        
        try:
            # 创建提供者实例
            provider = AkshareProvider()
            
            # 测试初始化
            try:
                initialized = await provider.initialize()
                provider_result['initialized'] = initialized
                provider_result['available'] = provider.is_available
                
                if not initialized:
                    print("  ❌ Akshare初始化失败")
                    results['providers']['akshare'] = provider_result
                    return
                
                print("  ✅ Akshare初始化成功")
                
                # 测试实时数据
                try:
                    realtime_data = await provider.get_realtime_data([self.test_symbols[0]])
                    if realtime_data:
                        provider_result['realtime_test']['success'] = True
                        print("  ✅ 实时数据获取成功")
                    else:
                        print("  ⚠️ 实时数据获取为空")
                except Exception as e:
                    provider_result['realtime_test']['error'] = str(e)
                    print(f"  ❌ 实时数据获取失败: {e}")
                
                # 测试历史数据
                try:
                    historical_data = await provider.get_historical_data(
                        self.test_symbols[0], 
                        self.test_start_date, 
                        self.test_end_date
                    )
                    if not historical_data.empty:
                        provider_result['historical_test']['success'] = True
                        provider_result['historical_test']['records'] = len(historical_data)
                        print(f"  ✅ 历史数据获取成功，共{len(historical_data)}条记录")
                    else:
                        print("  ⚠️ 历史数据获取为空")
                except Exception as e:
                    provider_result['historical_test']['error'] = str(e)
                    print(f"  ❌ 历史数据获取失败: {e}")
                
                # 测试基本信息
                try:
                    basic_info = await provider.get_basic_info(self.test_symbols[0])
                    if basic_info:
                        provider_result['basic_info_test']['success'] = True
                        print("  ✅ 基本信息获取成功")
                    else:
                        print("  ⚠️ 基本信息获取为空")
                except Exception as e:
                    provider_result['basic_info_test']['error'] = str(e)
                    print(f"  ❌ 基本信息获取失败: {e}")
                
            except Exception as e:
                provider_result['error'] = str(e)
                print(f"  ❌ Akshare初始化异常: {e}")
        
        except Exception as e:
            provider_result['error'] = str(e)
            print(f"  ❌ Akshare诊断异常: {e}")
        
        results['providers']['akshare'] = provider_result
    
    async def _diagnose_sina(self, results: Dict[str, Any]):
        """诊断Sina数据源"""
        print("\n🌐 诊断Sina数据源...")
        
        provider_result = {
            'name': 'Sina',
            'available': False,
            'initialized': False,
            'realtime_test': {'success': False, 'error': None},
            'historical_test': {'success': False, 'error': None, 'records': 0},
            'basic_info_test': {'success': False, 'error': None}
        }
        
        try:
            # 创建提供者实例
            provider = SinaProvider()
            
            # 测试初始化
            try:
                initialized = await provider.initialize()
                provider_result['initialized'] = initialized
                provider_result['available'] = provider.is_available
                
                if not initialized:
                    print("  ❌ Sina初始化失败")
                    results['providers']['sina'] = provider_result
                    return
                
                print("  ✅ Sina初始化成功")
                
                # 测试实时数据
                try:
                    realtime_data = await provider.get_realtime_data([self.test_symbols[0]])
                    if realtime_data:
                        provider_result['realtime_test']['success'] = True
                        print("  ✅ 实时数据获取成功")
                    else:
                        print("  ⚠️ 实时数据获取为空")
                except Exception as e:
                    provider_result['realtime_test']['error'] = str(e)
                    print(f"  ❌ 实时数据获取失败: {e}")
                
                # Sina通常不提供历史数据和基本信息
                print("  ℹ️ Sina主要提供实时数据")
                
            except Exception as e:
                provider_result['error'] = str(e)
                print(f"  ❌ Sina初始化异常: {e}")
        
        except Exception as e:
            provider_result['error'] = str(e)
            print(f"  ❌ Sina诊断异常: {e}")
        
        results['providers']['sina'] = provider_result
    
    async def _diagnose_data_manager(self, results: Dict[str, Any]):
        """诊断数据管理器"""
        print("\n🔧 诊断数据管理器...")
        
        manager_result = {
            'initialized': False,
            'primary_provider': None,
            'backup_provider': None,
            'realtime_provider': None,
            'realtime_test': {'success': False, 'error': None},
            'historical_test': {'success': False, 'error': None, 'records': 0}
        }
        
        try:
            # 创建数据管理器
            data_manager = DataManager()
            
            # 初始化
            await data_manager.initialize()
            manager_result['initialized'] = True
            
            # 获取配置的数据源
            manager_result['primary_provider'] = config.data.sources.primary
            manager_result['backup_provider'] = config.data.sources.backup
            manager_result['realtime_provider'] = config.data.sources.realtime
            
            print(f"  ✅ 数据管理器初始化成功")
            print(f"  📊 主要数据源: {manager_result['primary_provider']}")
            print(f"  🔄 备用数据源: {manager_result['backup_provider']}")
            print(f"  ⚡ 实时数据源: {manager_result['realtime_provider']}")
            
            # 测试实时数据
            try:
                realtime_data = await data_manager.get_realtime_data([self.test_symbols[0]])
                if realtime_data:
                    manager_result['realtime_test']['success'] = True
                    print("  ✅ 数据管理器实时数据获取成功")
                else:
                    print("  ⚠️ 数据管理器实时数据获取为空")
            except Exception as e:
                manager_result['realtime_test']['error'] = str(e)
                print(f"  ❌ 数据管理器实时数据获取失败: {e}")
            
            # 测试历史数据
            try:
                historical_data = await data_manager.get_historical_data(
                    self.test_symbols[0], 
                    self.test_start_date, 
                    self.test_end_date
                )
                if not historical_data.empty:
                    manager_result['historical_test']['success'] = True
                    manager_result['historical_test']['records'] = len(historical_data)
                    print(f"  ✅ 数据管理器历史数据获取成功，共{len(historical_data)}条记录")
                else:
                    print("  ⚠️ 数据管理器历史数据获取为空")
            except Exception as e:
                manager_result['historical_test']['error'] = str(e)
                print(f"  ❌ 数据管理器历史数据获取失败: {e}")
            
            await data_manager.close()
            
        except Exception as e:
            manager_result['error'] = str(e)
            print(f"  ❌ 数据管理器诊断异常: {e}")
        
        results['data_manager'] = manager_result
    
    def _generate_recommendations(self, results: Dict[str, Any]):
        """生成修复建议"""
        recommendations = []
        
        # 检查Tushare
        tushare = results['providers'].get('tushare', {})
        if not tushare.get('token_configured'):
            recommendations.append({
                'priority': 'high',
                'issue': 'Tushare token未配置',
                'solution': '在.env文件中设置TUSHARE_TOKEN环境变量',
                'command': 'echo "TUSHARE_TOKEN=your_token_here" >> .env'
            })
        elif not tushare.get('initialized'):
            recommendations.append({
                'priority': 'high',
                'issue': 'Tushare初始化失败',
                'solution': '检查token是否有效，或联系Tushare客服',
                'command': None
            })
        
        # 检查Akshare
        akshare = results['providers'].get('akshare', {})
        if not akshare.get('initialized'):
            recommendations.append({
                'priority': 'medium',
                'issue': 'Akshare初始化失败',
                'solution': '检查网络连接，或更新akshare版本',
                'command': 'pip install --upgrade akshare'
            })
        
        # 检查历史数据
        if not results['data_manager'].get('historical_test', {}).get('success'):
            recommendations.append({
                'priority': 'high',
                'issue': '历史数据获取失败',
                'solution': '确保至少一个数据源可用，检查网络连接',
                'command': None
            })
        
        # 检查实时数据
        if not results['data_manager'].get('realtime_test', {}).get('success'):
            recommendations.append({
                'priority': 'medium',
                'issue': '实时数据获取失败',
                'solution': '检查Sina数据源连接，或使用其他实时数据源',
                'command': None
            })
        
        results['recommendations'] = recommendations
    
    def _display_results(self, results: Dict[str, Any]):
        """显示诊断结果"""
        print("\n" + "=" * 60)
        print("📋 诊断结果汇总")
        print("=" * 60)
        
        # 数据源状态
        print("\n📊 数据源状态:")
        for name, provider in results['providers'].items():
            status = "✅" if provider.get('available') else "❌"
            print(f"  {status} {provider['name']}: {'可用' if provider.get('available') else '不可用'}")
        
        # 数据管理器状态
        dm = results['data_manager']
        dm_status = "✅" if dm.get('initialized') else "❌"
        print(f"\n🔧 数据管理器: {dm_status} {'正常' if dm.get('initialized') else '异常'}")
        
        # 功能测试结果
        print("\n🧪 功能测试结果:")
        realtime_ok = dm.get('realtime_test', {}).get('success', False)
        historical_ok = dm.get('historical_test', {}).get('success', False)
        
        print(f"  {'✅' if realtime_ok else '❌'} 实时数据获取: {'成功' if realtime_ok else '失败'}")
        print(f"  {'✅' if historical_ok else '❌'} 历史数据获取: {'成功' if historical_ok else '失败'}")
        
        if historical_ok:
            records = dm.get('historical_test', {}).get('records', 0)
            print(f"    📈 获取到{records}条历史记录")
        
        # 修复建议
        recommendations = results['recommendations']
        if recommendations:
            print("\n💡 修复建议:")
            for i, rec in enumerate(recommendations, 1):
                priority_icon = "🔴" if rec['priority'] == 'high' else "🟡"
                print(f"  {priority_icon} {i}. {rec['issue']}")
                print(f"     解决方案: {rec['solution']}")
                if rec['command']:
                    print(f"     执行命令: {rec['command']}")
                print()
        else:
            print("\n🎉 所有数据源工作正常！")
        
        print("=" * 60)


async def main():
    """主函数"""
    print("🔍 量化交易系统数据源诊断工具")
    print("=" * 60)
    
    diagnostic = DataSourceDiagnostic()
    
    try:
        results = await diagnostic.diagnose_all()
        
        # 保存诊断结果
        import json
        report_file = project_root / "logs" / f"data_source_diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n📄 诊断报告已保存到: {report_file}")
        
    except Exception as e:
        print(f"\n❌ 诊断过程中发生异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())