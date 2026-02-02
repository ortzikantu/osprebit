#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 Hao Wu <hao.wu@ortzikantu.com>
# SPDX-License-Identifier: GPL-3.0-only

"""
缓存管理模块

本模块提供了缓存管理功能，用于缓存仓库状态、文件树、
提交历史等数据，以提高应用性能。

主要功能：
    - 仓库状态缓存和变化检测
    - 通用缓存存储和检索
    - 缓存过期管理
    - 仓库级别的缓存清理

使用示例：
    >>> cache_manager.set("my_key", {"data": "value"})
    >>> data = cache_manager.get("my_key", max_age=3600)
    >>> cache_manager.delete("my_key")
"""

import os
import json
import time
from pathlib import Path
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("osprebit")

class CacheManager:
    """
    缓存管理器
    
    该类提供了缓存管理的所有功能，包括缓存存储、检索、
    过期管理和仓库状态跟踪。
    """
    
    def __init__(self, cache_dir: str = ".cache"):
        """
        初始化缓存管理器
        
        该方法初始化缓存管理器，创建缓存目录和仓库状态目录。
        
        Args:
            cache_dir (str): 缓存目录路径，默认为".cache"
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        self.repo_state_dir = self.cache_dir / "repo_state"
        self.repo_state_dir.mkdir(exist_ok=True)
        
    def get_cache_path(self, key: str) -> Path:
        """
        获取缓存文件路径
        
        该方法根据缓存键生成对应的缓存文件路径。
        
        Args:
            key (str): 缓存键
            
        Returns:
            Path: 缓存文件路径
        """
        safe_key = key.replace("/", "_")
        return self.cache_dir / f"{safe_key}.json"
    
    def get_repo_state_path(self, repo_name: str) -> Path:
        """
        获取仓库状态文件路径
        
        该方法根据仓库名称生成对应的仓库状态文件路径。
        
        Args:
            repo_name (str): 仓库名称
            
        Returns:
            Path: 仓库状态文件路径
        """
        return self.repo_state_dir / f"{repo_name}.json"
    
    def get_repo_state(self, repo_name: str) -> Optional[Dict[str, str]]:
        """
        获取仓库状态
        
        该方法从缓存中读取仓库状态，包含各分支的HEAD提交ID。
        
        Args:
            repo_name (str): 仓库名称
            
        Returns:
            Optional[Dict[str, str]]: 仓库状态字典，键为分支名称，
                                    值为HEAD提交ID，如果不存在则返回None
        """
        state_path = self.get_repo_state_path(repo_name)
        if not state_path.exists():
            return None
        
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"读取仓库状态失败: {e}")
            return None
    
    def set_repo_state(self, repo_name: str, state: Dict[str, str]) -> bool:
        """
        设置仓库状态
        
        该方法将仓库状态写入缓存。
        
        Args:
            repo_name (str): 仓库名称
            state (Dict[str, str]): 仓库状态字典，键为分支名称，值为HEAD提交ID
            
        Returns:
            bool: 是否成功
        """
        try:
            state_path = self.get_repo_state_path(repo_name)
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.debug(f"写入仓库状态失败: {e}")
            return False
    
    def check_repo_change(self, repo_name: str, current_state: Dict[str, str]) -> bool:
        """
        检查仓库是否发生变化
        
        该方法比较当前仓库状态与缓存的状态，判断仓库是否发生了变化。
        如果仓库发生变化，会更新缓存的状态。
        
        Args:
            repo_name (str): 仓库名称
            current_state (Dict[str, str]): 当前仓库状态
            
        Returns:
            bool: 如果仓库发生变化返回True，否则返回False
        """
        old_state = self.get_repo_state(repo_name)
        
        if not old_state:
            self.set_repo_state(repo_name, current_state)
            return True
        
        if old_state != current_state:
            self.set_repo_state(repo_name, current_state)
            return True
        
        return False
    
    def clear_repo_cache(self, repo_name: str) -> bool:
        """
        清空指定仓库的所有缓存
        
        该方法删除与指定仓库相关的所有缓存文件。
        
        Args:
            repo_name (str): 仓库名称
            
        Returns:
            bool: 是否成功
        """
        try:
            for cache_file in self.cache_dir.glob(f"*_{repo_name}_*.json"):
                cache_file.unlink()
            logger.info(f"清空仓库 {repo_name} 的缓存")
            return True
        except Exception as e:
            logger.debug(f"清空仓库缓存失败: {e}")
            return False
    
    def get(self, key: str, max_age: int = 3600) -> Optional[Any]:
        """
        获取缓存
        
        该方法从缓存中读取数据，如果缓存不存在或已过期则返回None。
        
        Args:
            key (str): 缓存键
            max_age (int): 最大缓存年龄（秒），默认为3600秒（1小时）
            
        Returns:
            Optional[Any]: 缓存数据，如果不存在或过期则返回None
        """
        try:
            cache_path = self.get_cache_path(key)
            if not cache_path.exists():
                return None
            
            mtime = cache_path.stat().st_mtime
            if time.time() - mtime > max_age:
                return None
            
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            logger.debug(f"缓存命中: {key}")
            return data
        except Exception as e:
            logger.debug(f"读取缓存失败: {e}")
            return None
    
    def set(self, key: str, data: Any) -> bool:
        """
        设置缓存
        
        该方法将数据写入缓存。
        
        Args:
            key (str): 缓存键
            data (Any): 缓存数据，必须是可JSON序列化的对象
            
        Returns:
            bool: 是否成功
        """
        try:
            cache_path = self.get_cache_path(key)
            
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"缓存设置: {key}")
            return True
        except Exception as e:
            logger.debug(f"写入缓存失败: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        该方法删除指定键的缓存文件。
        
        Args:
            key (str): 缓存键
            
        Returns:
            bool: 是否成功
        """
        try:
            cache_path = self.get_cache_path(key)
            if cache_path.exists():
                cache_path.unlink()
            return True
        except Exception as e:
            logger.debug(f"删除缓存失败: {e}")
            return False
    
    def clear(self) -> bool:
        """
        清空所有缓存
        
        该方法删除所有缓存文件和仓库状态文件。
        
        Returns:
            bool: 是否成功
        """
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            for state_file in self.repo_state_dir.glob("*.json"):
                state_file.unlink()
            return True
        except Exception as e:
            logger.debug(f"清空缓存失败: {e}")
            return False

cache_manager = CacheManager()
