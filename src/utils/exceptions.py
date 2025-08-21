#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义异常类模块

定义系统中使用的各种异常类型，提供更精确的错误处理
"""

from typing import Optional, Dict, Any


class TradingSystemException(Exception):
    """交易系统基础异常类"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
    
    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'context': self.context
        }


# 数据相关异常
class DataException(TradingSystemException):
    """数据相关异常基类"""
    pass


class DataSourceException(DataException):
    """数据源异常"""
    pass


class DataValidationException(DataException):
    """数据验证异常"""
    pass


class DataFormatException(DataException):
    """数据格式异常"""
    pass


class DataTimeoutException(DataException):
    """数据获取超时异常"""
    pass


# 网络相关异常
class NetworkException(TradingSystemException):
    """网络相关异常基类"""
    pass


class ConnectionException(NetworkException):
    """连接异常"""
    pass


class APIException(NetworkException):
    """API调用异常"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response_data: Optional[Dict] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.response_data = response_data
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            'status_code': self.status_code,
            'response_data': self.response_data
        })
        return result


class RateLimitException(APIException):
    """API限流异常"""
    pass


# 配置相关异常
class ConfigException(TradingSystemException):
    """配置相关异常基类"""
    pass


class ConfigValidationException(ConfigException):
    """配置验证异常"""
    pass


class ConfigLoadException(ConfigException):
    """配置加载异常"""
    pass


class MissingConfigException(ConfigException):
    """缺少配置异常"""
    pass


# 交易相关异常
class TradingException(TradingSystemException):
    """交易相关异常基类"""
    pass


class RiskException(TradingException):
    """风险管理异常"""
    pass


class PositionException(TradingException):
    """持仓异常"""
    pass


class OrderException(TradingException):
    """订单异常"""
    pass


class InsufficientFundsException(TradingException):
    """资金不足异常"""
    pass


# 策略相关异常
class StrategyException(TradingSystemException):
    """策略相关异常基类"""
    pass


class StrategyInitException(StrategyException):
    """策略初始化异常"""
    pass


class StrategyExecutionException(StrategyException):
    """策略执行异常"""
    pass


class SignalGenerationException(StrategyException):
    """信号生成异常"""
    pass


# AI分析相关异常
class AIAnalysisException(TradingSystemException):
    """AI分析相关异常基类"""
    pass


class LLMException(AIAnalysisException):
    """大语言模型异常"""
    pass


class ModelNotAvailableException(AIAnalysisException):
    """模型不可用异常"""
    pass


class AnalysisTimeoutException(AIAnalysisException):
    """分析超时异常"""
    pass


# 通知相关异常
class NotificationException(TradingSystemException):
    """通知相关异常基类"""
    pass


class MessageSendException(NotificationException):
    """消息发送异常"""
    pass


class WebhookException(NotificationException):
    """Webhook异常"""
    pass


# 监控相关异常
class MonitoringException(TradingSystemException):
    """监控相关异常基类"""
    pass


class AlertException(MonitoringException):
    """预警异常"""
    pass


class MetricsException(MonitoringException):
    """指标异常"""
    pass


# 工作流相关异常
class WorkflowException(TradingSystemException):
    """工作流相关异常基类"""
    pass


class WorkflowExecutionException(WorkflowException):
    """工作流执行异常"""
    pass


class TaskException(WorkflowException):
    """任务异常"""
    pass


# 缓存相关异常
class CacheException(TradingSystemException):
    """缓存相关异常基类"""
    pass


class CacheConnectionException(CacheException):
    """缓存连接异常"""
    pass


class CacheSerializationException(CacheException):
    """缓存序列化异常"""
    pass


# 安全相关异常
class SecurityException(TradingSystemException):
    """安全相关异常基类"""
    pass


class ValidationException(SecurityException):
    """验证异常"""
    pass


class EncryptionException(SecurityException):
    """加密异常"""
    pass


# 异常处理装饰器
def handle_exceptions(exception_map: Optional[Dict[type, type]] = None,
                     default_exception: type = TradingSystemException,
                     log_errors: bool = True):
    """异常处理装饰器
    
    Args:
        exception_map: 异常映射字典，将原始异常映射为自定义异常
        default_exception: 默认异常类型
        log_errors: 是否记录错误日志
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 如果已经是自定义异常，直接抛出
                if isinstance(e, TradingSystemException):
                    raise
                
                # 根据异常映射转换异常类型
                if exception_map:
                    for original_exc, custom_exc in exception_map.items():
                        if isinstance(e, original_exc):
                            raise custom_exc(str(e), context={'original_error': str(e)}) from e
                
                # 记录错误日志
                if log_errors and hasattr(args[0], 'logger'):
                    args[0].logger.error(f"未处理的异常: {e}", exc_info=True)
                
                # 抛出默认异常
                raise default_exception(f"系统内部错误: {str(e)}", 
                                       context={'original_error': str(e)}) from e
        
        return wrapper
    return decorator


# 异步异常处理装饰器
def handle_async_exceptions(exception_map: Optional[Dict[type, type]] = None,
                           default_exception: type = TradingSystemException,
                           log_errors: bool = True):
    """异步异常处理装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # 如果已经是自定义异常，直接抛出
                if isinstance(e, TradingSystemException):
                    raise
                
                # 根据异常映射转换异常类型
                if exception_map:
                    for original_exc, custom_exc in exception_map.items():
                        if isinstance(e, original_exc):
                            raise custom_exc(str(e), context={'original_error': str(e)}) from e
                
                # 记录错误日志
                if log_errors and hasattr(args[0], 'logger'):
                    args[0].logger.error(f"未处理的异常: {e}", exc_info=True)
                
                # 抛出默认异常
                raise default_exception(f"系统内部错误: {str(e)}", 
                                       context={'original_error': str(e)}) from e
        
        return wrapper
    return decorator


# 异常上下文管理器
class ExceptionContext:
    """异常上下文管理器"""
    
    def __init__(self, operation: str, logger=None):
        self.operation = operation
        self.logger = logger
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            error_msg = f"操作 '{self.operation}' 执行失败: {exc_val}"
            if self.logger:
                self.logger.error(error_msg, exc_info=True)
            
            # 如果不是自定义异常，包装为自定义异常
            if not isinstance(exc_val, TradingSystemException):
                raise TradingSystemException(
                    error_msg,
                    context={
                        'operation': self.operation,
                        'original_error': str(exc_val),
                        'error_type': exc_type.__name__
                    }
                ) from exc_val
        
        return False  # 不抑制异常