#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化测试运行器

提供完整的测试套件执行和报告功能
"""

import os
import sys
import unittest
import time
import argparse
import traceback
from pathlib import Path
from io import StringIO
import json
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入测试模块
from tests.test_config import TestPydanticConfig
from tests.test_data_provider import TestDataProvider
from tests.test_strategy import TestStrategy
from tests.test_monitor import TestMonitor
from tests.test_notification import TestNotification
from tests.test_engine import TestEngine
from tests.test_web import TestWebInterface
from tests.test_integration import TestIntegration


class TestResult:
    """测试结果类"""
    
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.error_tests = 0
        self.skipped_tests = 0
        self.start_time = None
        self.end_time = None
        self.test_details = []
        self.failures = []
        self.errors = []
    
    @property
    def success_rate(self):
        """成功率"""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100
    
    @property
    def duration(self):
        """测试持续时间"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0
    
    def add_test_result(self, test_name, status, duration, error_msg=None):
        """添加测试结果"""
        self.test_details.append({
            'name': test_name,
            'status': status,
            'duration': duration,
            'error': error_msg
        })
        
        if status == 'PASS':
            self.passed_tests += 1
        elif status == 'FAIL':
            self.failed_tests += 1
            if error_msg:
                self.failures.append((test_name, error_msg))
        elif status == 'ERROR':
            self.error_tests += 1
            if error_msg:
                self.errors.append((test_name, error_msg))
        elif status == 'SKIP':
            self.skipped_tests += 1
        
        self.total_tests += 1


class CustomTestResult(unittest.TestResult):
    """自定义测试结果收集器"""
    
    def __init__(self, test_result_obj):
        super().__init__()
        self.test_result_obj = test_result_obj
        self.current_test_start = None
    
    def startTest(self, test):
        super().startTest(test)
        self.current_test_start = time.time()
    
    def addSuccess(self, test):
        super().addSuccess(test)
        duration = time.time() - self.current_test_start
        self.test_result_obj.add_test_result(
            self._get_test_name(test), 'PASS', duration
        )
    
    def addError(self, test, err):
        super().addError(test, err)
        duration = time.time() - self.current_test_start
        error_msg = self._format_error(err)
        self.test_result_obj.add_test_result(
            self._get_test_name(test), 'ERROR', duration, error_msg
        )
    
    def addFailure(self, test, err):
        super().addFailure(test, err)
        duration = time.time() - self.current_test_start
        error_msg = self._format_error(err)
        self.test_result_obj.add_test_result(
            self._get_test_name(test), 'FAIL', duration, error_msg
        )
    
    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        duration = time.time() - self.current_test_start
        self.test_result_obj.add_test_result(
            self._get_test_name(test), 'SKIP', duration, reason
        )
    
    def _get_test_name(self, test):
        """获取测试名称"""
        return f"{test.__class__.__name__}.{test._testMethodName}"
    
    def _format_error(self, err):
        """格式化错误信息"""
        try:
            return ''.join(traceback.format_exception(*err))
        except Exception:
            return str(err)


class TestRunner:
    """测试运行器"""
    
    def __init__(self, verbosity=2):
        self.verbosity = verbosity
        self.test_modules = {
            'config': TestPydanticConfig,
            'data_provider': TestDataProvider,
            'strategy': TestStrategy,
            'monitor': TestMonitor,
            'notification': TestNotification,
            'engine': TestEngine,
            'web': TestWebInterface,
            'integration': TestIntegration
        }
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始运行量化股票交易系统测试套件")
        print("=" * 60)
        
        test_result = TestResult()
        test_result.start_time = time.time()
        
        # 创建测试套件
        suite = unittest.TestSuite()
        
        for module_name, test_class in self.test_modules.items():
            print(f"\n📦 加载 {module_name} 测试模块...")
            module_suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
            suite.addTest(module_suite)
        
        # 可选加载：异常处理测试套件，不存在则跳过
        try:
            from tests.test_exceptions import TestExceptionHandling
            print("\n📦 加载 exceptions 测试模块...")
            suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestExceptionHandling))
        except ModuleNotFoundError:
            print("\n⚠️  未找到 exceptions 测试模块（tests/test_exceptions.py），跳过该模块")
        except Exception as e:
            print(f"\n⚠️  加载 exceptions 测试模块失败，跳过。原因: {e}")
        
        # 运行测试
        print(f"\n🧪 开始执行测试...")
        
        class TestResultClass(CustomTestResult):
            def __init__(self, stream, descriptions, verbosity):
                super().__init__(test_result)
        
        runner = unittest.TextTestRunner(
            stream=StringIO(),
            verbosity=self.verbosity,
            resultclass=TestResultClass
        )
        
        result = runner.run(suite)
        test_result.end_time = time.time()
        
        # 显示结果
        self._print_results(test_result)
        
        return test_result
    
    def run_specific_tests(self, test_names):
        """运行指定的测试"""
        print(f"🎯 运行指定测试: {', '.join(test_names)}")
        print("=" * 60)
        
        test_result = TestResult()
        test_result.start_time = time.time()
        
        suite = unittest.TestSuite()
        
        for test_name in test_names:
            if test_name in self.test_modules:
                print(f"\n📦 加载 {test_name} 测试模块...")
                test_class = self.test_modules[test_name]
                module_suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
                suite.addTest(module_suite)
            else:
                print(f"⚠️  未找到测试模块: {test_name}")
        
        if suite.countTestCases() == 0:
            print("❌ 没有找到有效的测试模块")
            return test_result
        
        # 运行测试
        print(f"\n🧪 开始执行测试...")
        
        class TestResultClass(CustomTestResult):
            def __init__(self, stream, descriptions, verbosity):
                super().__init__(test_result)
        
        runner = unittest.TextTestRunner(
            stream=StringIO(),
            verbosity=self.verbosity,
            resultclass=TestResultClass
        )
        
        result = runner.run(suite)
        test_result.end_time = time.time()
        
        # 显示结果
        self._print_results(test_result)
        
        return test_result
    
    def run_quick_tests(self):
        """运行快速测试（排除集成测试）"""
        print("⚡ 运行快速测试套件（排除集成测试）")
        print("=" * 60)
        
        quick_tests = [name for name in self.test_modules.keys() if name != 'integration']
        return self.run_specific_tests(quick_tests)
    
    def _print_results(self, test_result):
        """打印测试结果"""
        print("\n" + "=" * 60)
        print("📊 测试结果汇总")
        print("=" * 60)
        
        # 基本统计
        print(f"总测试数量: {test_result.total_tests}")
        print(f"通过: {test_result.passed_tests} ✅")
        print(f"失败: {test_result.failed_tests} ❌")
        print(f"错误: {test_result.error_tests} 💥")
        print(f"跳过: {test_result.skipped_tests} ⏭️")
        print(f"成功率: {test_result.success_rate:.1f}%")
        print(f"执行时间: {test_result.duration:.2f}秒")
        
        # 详细结果
        if self.verbosity >= 2:
            print("\n📋 详细测试结果:")
            print("-" * 60)
            
            for detail in test_result.test_details:
                status_icon = {
                    'PASS': '✅',
                    'FAIL': '❌',
                    'ERROR': '💥',
                    'SKIP': '⏭️'
                }.get(detail['status'], '❓')
                
                print(f"{status_icon} {detail['name']} ({detail['duration']:.3f}s)")
                
                if detail['error'] and self.verbosity >= 3:
                    print(f"   错误: {detail['error'][:100]}...")
        
        # 失败和错误详情
        if test_result.failures:
            print("\n❌ 失败详情:")
            print("-" * 60)
            for test_name, error in test_result.failures[:5]:  # 只显示前5个
                print(f"• {test_name}")
                if self.verbosity >= 3:
                    print(f"  {error[:200]}...\n")
        
        if test_result.errors:
            print("\n💥 错误详情:")
            print("-" * 60)
            for test_name, error in test_result.errors[:5]:  # 只显示前5个
                print(f"• {test_name}")
                if self.verbosity >= 3:
                    print(f"  {error[:200]}...\n")
        
        # 总结
        print("\n" + "=" * 60)
        if test_result.failed_tests == 0 and test_result.error_tests == 0:
            print("🎉 所有测试通过！系统功能正常。")
        elif test_result.success_rate >= 80:
            print("⚠️  大部分测试通过，系统基本可用，请检查失败项。")
        else:
            print("❌ 多项测试失败，请检查系统配置和环境。")
        
        print("\n💡 提示:")
        print("   - 使用 -v 3 参数查看详细错误信息")
        print("   - 使用 --quick 运行快速测试")
        print("   - 使用 --modules 指定特定模块测试")
    
    def generate_report(self, test_result, output_file=None):
        """生成测试报告"""
        if not output_file:
            output_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': test_result.total_tests,
                'passed_tests': test_result.passed_tests,
                'failed_tests': test_result.failed_tests,
                'error_tests': test_result.error_tests,
                'skipped_tests': test_result.skipped_tests,
                'success_rate': test_result.success_rate,
                'duration': test_result.duration
            },
            'test_details': test_result.test_details,
            'failures': [{'test': name, 'error': error} for name, error in test_result.failures],
            'errors': [{'test': name, 'error': error} for name, error in test_result.errors]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 测试报告已保存到: {output_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='量化股票交易系统测试运行器')
    parser.add_argument('-v', '--verbosity', type=int, choices=[0, 1, 2, 3], default=2,
                       help='详细程度 (0=静默, 1=简单, 2=详细, 3=非常详细)')
    parser.add_argument('--quick', action='store_true',
                       help='运行快速测试（排除集成测试）')
    parser.add_argument('--modules', nargs='+',
                       choices=['config', 'data_provider', 'strategy', 'monitor', 
                               'notification', 'engine', 'web', 'integration'],
                       help='指定要运行的测试模块')
    parser.add_argument('--report', type=str,
                       help='生成测试报告文件路径')
    parser.add_argument('--list', action='store_true',
                       help='列出所有可用的测试模块')
    
    args = parser.parse_args()
    
    runner = TestRunner(verbosity=args.verbosity)
    
    if args.list:
        print("📋 可用的测试模块:")
        for module_name in runner.test_modules.keys():
            print(f"  • {module_name}")
        return
    
    # 运行测试
    if args.quick:
        test_result = runner.run_quick_tests()
    elif args.modules:
        test_result = runner.run_specific_tests(args.modules)
    else:
        test_result = runner.run_all_tests()
    
    # 生成报告
    if args.report:
        runner.generate_report(test_result, args.report)
    
    # 返回适当的退出码
    if test_result.failed_tests > 0 or test_result.error_tests > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()