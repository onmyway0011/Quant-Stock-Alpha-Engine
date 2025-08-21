#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全工具模块

提供敏感信息保护、数据脱敏、输入验证等安全功能
"""

import re
import hashlib
import secrets
import base64
from typing import Any, Dict, List, Optional, Union, Pattern
from functools import wraps
from dataclasses import dataclass

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

from .logger import get_logger
from .exceptions import SecurityException, ValidationException


@dataclass
class SensitiveField:
    """敏感字段配置"""
    field_name: str
    mask_char: str = '*'
    show_length: int = 4
    mask_type: str = 'partial'  # 'partial', 'full', 'hash'


class DataMasker:
    """数据脱敏器"""
    
    # 预定义的敏感字段模式
    SENSITIVE_PATTERNS = {
        'api_key': re.compile(r'(api[_-]?key|token|secret)', re.IGNORECASE),
        'password': re.compile(r'(password|passwd|pwd)', re.IGNORECASE),
        'phone': re.compile(r'(phone|mobile|tel)', re.IGNORECASE),
        'email': re.compile(r'(email|mail)', re.IGNORECASE),
        'id_card': re.compile(r'(id[_-]?card|identity)', re.IGNORECASE),
        'credit_card': re.compile(r'(credit[_-]?card|card[_-]?number)', re.IGNORECASE),
        'bank_account': re.compile(r'(bank[_-]?account|account[_-]?number)', re.IGNORECASE),
    }
    
    def __init__(self, custom_patterns: Optional[Dict[str, Pattern]] = None):
        self.logger = get_logger(self.__class__.__name__)
        self.patterns = self.SENSITIVE_PATTERNS.copy()
        if custom_patterns:
            self.patterns.update(custom_patterns)
    
    def mask_string(self, value: str, mask_char: str = '*', 
                   show_length: int = 4, mask_type: str = 'partial') -> str:
        """字符串脱敏
        
        Args:
            value: 原始字符串
            mask_char: 掩码字符
            show_length: 显示长度
            mask_type: 脱敏类型 ('partial', 'full', 'hash')
        """
        if not value or not isinstance(value, str):
            return str(value)
        
        if mask_type == 'full':
            return mask_char * len(value)
        elif mask_type == 'hash':
            return hashlib.sha256(value.encode()).hexdigest()[:8]
        elif mask_type == 'partial':
            if len(value) <= show_length:
                return mask_char * len(value)
            
            if show_length == 0:
                return mask_char * len(value)
            
            # 显示前几位和后几位
            show_front = show_length // 2
            show_back = show_length - show_front
            
            if show_back == 0:
                return value[:show_front] + mask_char * (len(value) - show_front)
            else:
                return (value[:show_front] + 
                       mask_char * (len(value) - show_length) + 
                       value[-show_back:])
        
        return value
    
    def mask_api_key(self, api_key: str) -> str:
        """API密钥脱敏"""
        return self.mask_string(api_key, show_length=8, mask_type='partial')
    
    def mask_phone(self, phone: str) -> str:
        """手机号脱敏"""
        return self.mask_string(phone, show_length=7, mask_type='partial')
    
    def mask_email(self, email: str) -> str:
        """邮箱脱敏"""
        if '@' not in email:
            return self.mask_string(email, show_length=4)
        
        local, domain = email.split('@', 1)
        masked_local = self.mask_string(local, show_length=2)
        return f"{masked_local}@{domain}"
    
    def mask_dict(self, data: Dict[str, Any], 
                 sensitive_fields: Optional[List[SensitiveField]] = None) -> Dict[str, Any]:
        """字典数据脱敏"""
        if not isinstance(data, dict):
            return data
        
        result = {}
        
        for key, value in data.items():
            # 检查是否为敏感字段
            is_sensitive = False
            mask_config = SensitiveField(key)
            
            # 检查自定义敏感字段
            if sensitive_fields:
                for field in sensitive_fields:
                    if field.field_name.lower() == key.lower():
                        is_sensitive = True
                        mask_config = field
                        break
            
            # 检查预定义模式
            if not is_sensitive:
                for pattern_name, pattern in self.patterns.items():
                    if pattern.search(key):
                        is_sensitive = True
                        break
            
            # 递归处理嵌套结构
            if isinstance(value, dict):
                result[key] = self.mask_dict(value, sensitive_fields)
            elif isinstance(value, list):
                result[key] = [self.mask_dict(item, sensitive_fields) 
                              if isinstance(item, dict) else item for item in value]
            elif is_sensitive and isinstance(value, str):
                result[key] = self.mask_string(
                    value, 
                    mask_config.mask_char, 
                    mask_config.show_length, 
                    mask_config.mask_type
                )
            else:
                result[key] = value
        
        return result
    
    def mask_log_message(self, message: str) -> str:
        """日志消息脱敏"""
        # API密钥模式
        api_key_pattern = re.compile(r'(api[_-]?key|token|secret)[\s=:]+([\w\-\.]+)', re.IGNORECASE)
        message = api_key_pattern.sub(
            lambda m: f"{m.group(1)}={self.mask_api_key(m.group(2))}", 
            message
        )
        
        # 密码模式
        password_pattern = re.compile(r'(password|passwd|pwd)[\s=:]+([\w\-\.]+)', re.IGNORECASE)
        message = password_pattern.sub(
            lambda m: f"{m.group(1)}={self.mask_string(m.group(2), show_length=0)}", 
            message
        )
        
        # 手机号模式
        phone_pattern = re.compile(r'\b1[3-9]\d{9}\b')
        message = phone_pattern.sub(
            lambda m: self.mask_phone(m.group(0)), 
            message
        )
        
        # 邮箱模式
        email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        message = email_pattern.sub(
            lambda m: self.mask_email(m.group(0)), 
            message
        )
        
        return message


class InputValidator:
    """输入验证器"""
    
    # 股票代码模式
    STOCK_CODE_PATTERNS = {
        'A股': re.compile(r'^[0-9]{6}\.(SZ|SH)$'),
        '港股': re.compile(r'^[0-9]{5}\.(HK)$'),
        '美股': re.compile(r'^[A-Z]{1,5}$'),
    }
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    def validate_stock_symbol(self, symbol: str) -> bool:
        """验证股票代码"""
        if not symbol or not isinstance(symbol, str):
            return False
        
        symbol = symbol.upper().strip()
        
        for market, pattern in self.STOCK_CODE_PATTERNS.items():
            if pattern.match(symbol):
                return True
        
        return False
    
    def validate_price(self, price: Union[int, float]) -> bool:
        """验证价格"""
        try:
            price = float(price)
            return price > 0 and price < 1000000  # 价格范围限制
        except (ValueError, TypeError):
            return False
    
    def validate_quantity(self, quantity: Union[int, float]) -> bool:
        """验证数量"""
        try:
            quantity = int(quantity)
            return quantity > 0 and quantity <= 1000000  # 数量范围限制
        except (ValueError, TypeError):
            return False
    
    def validate_confidence(self, confidence: Union[int, float]) -> bool:
        """验证信心度"""
        try:
            confidence = float(confidence)
            return 0 <= confidence <= 1
        except (ValueError, TypeError):
            return False
    
    def validate_api_key(self, api_key: str) -> bool:
        """验证API密钥格式"""
        if not api_key or not isinstance(api_key, str):
            return False
        
        # 基本长度检查
        if len(api_key) < 16 or len(api_key) > 128:
            return False
        
        # 字符检查（只允许字母、数字、下划线、连字符）
        if not re.match(r'^[A-Za-z0-9_\-]+$', api_key):
            return False
        
        return True
    
    def validate_webhook_url(self, url: str) -> bool:
        """验证Webhook URL"""
        if not url or not isinstance(url, str):
            return False
        
        # URL格式检查
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'  # domain...
            r'(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # host...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(url_pattern.match(url))


class Encryptor:
    """加密器"""
    
    def __init__(self, password: Optional[str] = None):
        if not CRYPTO_AVAILABLE:
            raise SecurityException("加密库未安装，请运行: pip install cryptography")
        
        self.logger = get_logger(self.__class__.__name__)
        self._fernet = None
        
        if password:
            self._init_fernet(password)
    
    def _init_fernet(self, password: str):
        """初始化Fernet加密器"""
        # 生成密钥
        salt = b'trading_system_salt'  # 在生产环境中应该使用随机salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        self._fernet = Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """加密字符串"""
        if not self._fernet:
            raise SecurityException("加密器未初始化")
        
        try:
            encrypted_data = self._fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            raise SecurityException(f"加密失败: {e}")
    
    def decrypt(self, encrypted_data: str) -> str:
        """解密字符串"""
        if not self._fernet:
            raise SecurityException("加密器未初始化")
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self._fernet.decrypt(encrypted_bytes)
            return decrypted_data.decode()
        except Exception as e:
            raise SecurityException(f"解密失败: {e}")
    
    @staticmethod
    def generate_key() -> str:
        """生成随机密钥"""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """密码哈希"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # 使用PBKDF2进行密码哈希
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=100000,
        )
        
        hashed = base64.urlsafe_b64encode(kdf.derive(password.encode())).decode()
        return hashed, salt
    
    @staticmethod
    def verify_password(password: str, hashed: str, salt: str) -> bool:
        """验证密码"""
        try:
            new_hashed, _ = Encryptor.hash_password(password, salt)
            return new_hashed == hashed
        except Exception:
            return False


# 装饰器
def validate_input(**validators):
    """输入验证装饰器
    
    Args:
        **validators: 参数名到验证函数的映射
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取函数参数名
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # 验证参数
            for param_name, validator_func in validators.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    if not validator_func(value):
                        raise ValidationException(f"参数 {param_name} 验证失败: {value}")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def mask_sensitive_data(sensitive_fields: Optional[List[str]] = None):
    """敏感数据脱敏装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # 如果返回结果是字典，进行脱敏
            if isinstance(result, dict):
                masker = DataMasker()
                fields = [SensitiveField(field) for field in (sensitive_fields or [])]
                return masker.mask_dict(result, fields)
            
            return result
        
        return wrapper
    return decorator


# 全局实例
_data_masker = DataMasker()
_input_validator = InputValidator()


def mask_sensitive_info(data: Any) -> Any:
    """脱敏敏感信息"""
    if isinstance(data, dict):
        return _data_masker.mask_dict(data)
    elif isinstance(data, str):
        return _data_masker.mask_log_message(data)
    else:
        return data


def validate_stock_symbol(symbol: str) -> bool:
    """验证股票代码"""
    return _input_validator.validate_stock_symbol(symbol)


def validate_trading_params(price: float, quantity: int, confidence: float) -> bool:
    """验证交易参数"""
    return (validate_price(price) and 
            validate_quantity(quantity) and 
            validate_confidence(confidence))


def validate_price(price: Union[int, float]) -> bool:
    """验证价格"""
    return _input_validator.validate_price(price)


def validate_quantity(quantity: Union[int, float]) -> bool:
    """验证数量"""
    return _input_validator.validate_quantity(quantity)


def validate_confidence(confidence: Union[int, float]) -> bool:
    """验证信心度"""
    return _input_validator.validate_confidence(confidence)


def validate_api_key(api_key: str) -> bool:
    """验证API密钥"""
    return _input_validator.validate_api_key(api_key)


def validate_webhook_url(url: str) -> bool:
    """验证Webhook URL"""
    return _input_validator.validate_webhook_url(url)