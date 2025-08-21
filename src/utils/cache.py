#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存策略实现模块

提供多级缓存支持，包括内存缓存和Redis缓存
"""

import asyncio
import json
import pickle
import time
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List, Union, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
import hashlib

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from .logger import get_logger
from .exceptions import CacheException, ConnectionException


@dataclass
class CacheItem:
    """缓存项"""
    key: str
    value: Any
    created_at: float
    expires_at: Optional[float] = None
    access_count: int = 0
    last_accessed: float = 0
    
    def __post_init__(self):
        if self.last_accessed == 0:
            self.last_accessed = self.created_at
    
    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
    
    @property
    def age(self) -> float:
        """获取缓存项年龄（秒）"""
        return time.time() - self.created_at
    
    def touch(self):
        """更新访问时间和次数"""
        self.last_accessed = time.time()
        self.access_count += 1


class CacheBackend(ABC):
    """缓存后端抽象基类"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """清空缓存"""
        pass
    
    @abstractmethod
    async def keys(self, pattern: str = "*") -> List[str]:
        """获取匹配的键列表"""
        pass


class MemoryCache(CacheBackend):
    """内存缓存实现"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheItem] = {}
        self._lock = asyncio.Lock()
        self.logger = get_logger(self.__class__.__name__)
        
        # 启动清理任务
        asyncio.create_task(self._cleanup_task())
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        async with self._lock:
            item = self._cache.get(key)
            if item is None:
                return None
            
            if item.is_expired:
                del self._cache[key]
                return None
            
            item.touch()
            return item.value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            async with self._lock:
                # 检查缓存大小限制
                if len(self._cache) >= self.max_size and key not in self._cache:
                    await self._evict_lru()
                
                now = time.time()
                expires_at = None
                if ttl is not None:
                    expires_at = now + ttl
                elif self.default_ttl > 0:
                    expires_at = now + self.default_ttl
                
                self._cache[key] = CacheItem(
                    key=key,
                    value=value,
                    created_at=now,
                    expires_at=expires_at
                )
                return True
        except Exception as e:
            self.logger.error(f"设置缓存失败: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        async with self._lock:
            return self._cache.pop(key, None) is not None
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        async with self._lock:
            item = self._cache.get(key)
            if item is None:
                return False
            
            if item.is_expired:
                del self._cache[key]
                return False
            
            return True
    
    async def clear(self) -> bool:
        """清空缓存"""
        async with self._lock:
            self._cache.clear()
            return True
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """获取匹配的键列表"""
        import fnmatch
        async with self._lock:
            # 清理过期项
            expired_keys = [k for k, v in self._cache.items() if v.is_expired]
            for k in expired_keys:
                del self._cache[k]
            
            # 返回匹配的键
            if pattern == "*":
                return list(self._cache.keys())
            else:
                return [k for k in self._cache.keys() if fnmatch.fnmatch(k, pattern)]
    
    async def _evict_lru(self):
        """LRU淘汰策略"""
        if not self._cache:
            return
        
        # 找到最少使用的项
        lru_key = min(self._cache.keys(), 
                     key=lambda k: (self._cache[k].access_count, self._cache[k].last_accessed))
        del self._cache[lru_key]
        self.logger.debug(f"LRU淘汰缓存项: {lru_key}")
    
    async def _cleanup_task(self):
        """定期清理过期项"""
        while True:
            try:
                await asyncio.sleep(300)  # 每5分钟清理一次
                async with self._lock:
                    expired_keys = [k for k, v in self._cache.items() if v.is_expired]
                    for k in expired_keys:
                        del self._cache[k]
                    
                    if expired_keys:
                        self.logger.debug(f"清理过期缓存项: {len(expired_keys)}个")
            except Exception as e:
                self.logger.error(f"缓存清理任务异常: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_items = len(self._cache)
        expired_items = sum(1 for item in self._cache.values() if item.is_expired)
        
        return {
            'total_items': total_items,
            'expired_items': expired_items,
            'valid_items': total_items - expired_items,
            'max_size': self.max_size,
            'utilization': total_items / self.max_size if self.max_size > 0 else 0
        }


class RedisCache(CacheBackend):
    """Redis缓存实现"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 key_prefix: str = "trading:", default_ttl: int = 3600):
        if not REDIS_AVAILABLE:
            raise ConnectionException("Redis库未安装，请运行: pip install redis")
        
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl
        self.redis_client: Optional[redis.Redis] = None
        self.logger = get_logger(self.__class__.__name__)
    
    async def _ensure_connection(self):
        """确保Redis连接"""
        if self.redis_client is None:
            try:
                self.redis_client = redis.from_url(self.redis_url)
                await self.redis_client.ping()
                self.logger.info("Redis连接建立成功")
            except Exception as e:
                raise ConnectionException(f"Redis连接失败: {e}")
    
    def _make_key(self, key: str) -> str:
        """生成完整的键名"""
        return f"{self.key_prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            await self._ensure_connection()
            full_key = self._make_key(key)
            data = await self.redis_client.get(full_key)
            
            if data is None:
                return None
            
            # 尝试反序列化
            try:
                return pickle.loads(data)
            except (pickle.PickleError, TypeError):
                # 如果pickle失败，尝试JSON
                try:
                    return json.loads(data.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # 如果都失败，返回原始字符串
                    return data.decode('utf-8')
        
        except Exception as e:
            self.logger.error(f"Redis获取缓存失败: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            await self._ensure_connection()
            full_key = self._make_key(key)
            
            # 序列化数据
            try:
                data = pickle.dumps(value)
            except (pickle.PickleError, TypeError):
                # 如果pickle失败，尝试JSON
                try:
                    data = json.dumps(value).encode('utf-8')
                except (TypeError, ValueError):
                    # 如果都失败，转换为字符串
                    data = str(value).encode('utf-8')
            
            # 设置TTL
            expire_time = ttl if ttl is not None else self.default_ttl
            
            if expire_time > 0:
                await self.redis_client.setex(full_key, expire_time, data)
            else:
                await self.redis_client.set(full_key, data)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Redis设置缓存失败: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            await self._ensure_connection()
            full_key = self._make_key(key)
            result = await self.redis_client.delete(full_key)
            return result > 0
        
        except Exception as e:
            self.logger.error(f"Redis删除缓存失败: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            await self._ensure_connection()
            full_key = self._make_key(key)
            result = await self.redis_client.exists(full_key)
            return result > 0
        
        except Exception as e:
            self.logger.error(f"Redis检查键存在失败: {e}")
            return False
    
    async def clear(self) -> bool:
        """清空缓存"""
        try:
            await self._ensure_connection()
            pattern = self._make_key("*")
            keys = await self.redis_client.keys(pattern)
            
            if keys:
                await self.redis_client.delete(*keys)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Redis清空缓存失败: {e}")
            return False
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """获取匹配的键列表"""
        try:
            await self._ensure_connection()
            full_pattern = self._make_key(pattern)
            keys = await self.redis_client.keys(full_pattern)
            
            # 移除前缀
            prefix_len = len(self.key_prefix)
            return [key.decode('utf-8')[prefix_len:] for key in keys]
        
        except Exception as e:
            self.logger.error(f"Redis获取键列表失败: {e}")
            return []
    
    async def close(self):
        """关闭连接"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None


class MultiLevelCache:
    """多级缓存实现"""
    
    def __init__(self, l1_cache: CacheBackend, l2_cache: Optional[CacheBackend] = None):
        self.l1_cache = l1_cache  # 一级缓存（通常是内存）
        self.l2_cache = l2_cache  # 二级缓存（通常是Redis）
        self.logger = get_logger(self.__class__.__name__)
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        # 先从L1缓存获取
        value = await self.l1_cache.get(key)
        if value is not None:
            return value
        
        # 如果L1缓存未命中，从L2缓存获取
        if self.l2_cache:
            value = await self.l2_cache.get(key)
            if value is not None:
                # 回写到L1缓存
                await self.l1_cache.set(key, value)
                return value
        
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        # 同时设置L1和L2缓存
        l1_result = await self.l1_cache.set(key, value, ttl)
        l2_result = True
        
        if self.l2_cache:
            l2_result = await self.l2_cache.set(key, value, ttl)
        
        return l1_result and l2_result
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        l1_result = await self.l1_cache.delete(key)
        l2_result = True
        
        if self.l2_cache:
            l2_result = await self.l2_cache.delete(key)
        
        return l1_result or l2_result
    
    async def clear(self) -> bool:
        """清空缓存"""
        l1_result = await self.l1_cache.clear()
        l2_result = True
        
        if self.l2_cache:
            l2_result = await self.l2_cache.clear()
        
        return l1_result and l2_result


def cache_key_generator(*args, **kwargs) -> str:
    """生成缓存键"""
    # 将参数转换为字符串并生成哈希
    key_parts = []
    
    for arg in args:
        if hasattr(arg, '__dict__'):
            # 对象类型，使用类名
            key_parts.append(arg.__class__.__name__)
        else:
            key_parts.append(str(arg))
    
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")
    
    key_string = "|".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(ttl: int = 3600, key_func: Optional[Callable] = None, 
          cache_backend: Optional[CacheBackend] = None):
    """缓存装饰器
    
    Args:
        ttl: 缓存时间（秒）
        key_func: 自定义键生成函数
        cache_backend: 缓存后端，默认使用全局缓存
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{cache_key_generator(*args, **kwargs)}"
            
            # 获取缓存后端
            backend = cache_backend or get_default_cache()
            
            # 尝试从缓存获取
            cached_result = await backend.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            await backend.set(cache_key, result, ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 对于同步函数，需要在事件循环中运行
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(async_wrapper(*args, **kwargs))
        
        # 根据函数类型返回相应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# 全局缓存实例
_default_cache: Optional[CacheBackend] = None


def get_default_cache() -> CacheBackend:
    """获取默认缓存实例"""
    global _default_cache
    if _default_cache is None:
        _default_cache = MemoryCache()
    return _default_cache


def set_default_cache(cache: CacheBackend):
    """设置默认缓存实例"""
    global _default_cache
    _default_cache = cache


def init_cache_from_config(config: Dict[str, Any]) -> CacheBackend:
    """从配置初始化缓存"""
    cache_config = config.get('cache', {})
    cache_type = cache_config.get('type', 'memory')
    
    if cache_type == 'memory':
        return MemoryCache(
            max_size=cache_config.get('max_size', 1000),
            default_ttl=cache_config.get('default_ttl', 3600)
        )
    elif cache_type == 'redis':
        return RedisCache(
            redis_url=cache_config.get('redis_url', 'redis://localhost:6379'),
            key_prefix=cache_config.get('key_prefix', 'trading:'),
            default_ttl=cache_config.get('default_ttl', 3600)
        )
    elif cache_type == 'multi':
        l1_cache = MemoryCache(
            max_size=cache_config.get('l1_max_size', 500),
            default_ttl=cache_config.get('l1_ttl', 1800)
        )
        l2_cache = RedisCache(
            redis_url=cache_config.get('redis_url', 'redis://localhost:6379'),
            key_prefix=cache_config.get('key_prefix', 'trading:'),
            default_ttl=cache_config.get('l2_ttl', 7200)
        )
        return MultiLevelCache(l1_cache, l2_cache)
    else:
        raise ValueError(f"不支持的缓存类型: {cache_type}")