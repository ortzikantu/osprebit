#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 Hao Wu <hao.wu@ortzikantu.com>
# SPDX-License-Identifier: GPL-3.0-only

"""
Git工具函数模块

本模块提供了Git仓库的工具函数，包括仓库状态检查、
变化检测、大小计算和格式化等功能。

主要功能：
    - 获取仓库状态
    - 检查仓库是否发生变化
    - 获取仓库大小
    - 格式化大小显示

使用示例：
    >>> state = get_repo_state(git_ops)
    >>> changed = check_repo_change(git_ops)
    >>> size = get_repo_size(git_ops)
"""

import pygit2
import subprocess
import logging
import os

from .cache_manager import cache_manager

logger = logging.getLogger("osprebit")


def get_repo_state(self):
    """
    获取仓库状态
    
    该方法返回仓库的当前状态，包括各分支的HEAD提交ID。
    
    Args:
        self: GitOperations对象
        
    Returns:
        dict: 仓库状态字典，键为分支名称，值为HEAD提交ID
              如果获取失败则返回空字典
              
    Examples:
        >>> state = get_repo_state(git_ops)
        >>> for branch, commit_id in state.items():
        ...     print(f"{branch}: {commit_id}")
    """
    try:
        repo = pygit2.Repository(str(self.repo_path))
        state = {}
        
        for branch_name in repo.branches.local:
            try:
                branch = repo.branches[branch_name]
                commit = branch.peel()
                state[branch_name] = str(commit.id)
            except Exception as e:
                logger.debug(f"获取分支 {branch_name} 状态失败: {e}")
        
        return state
    except Exception as e:
        logger.error(f"获取仓库状态失败: {e}")
        return {}


def check_repo_change(self):
    """
    检查仓库是否发生变化
    
    该方法比较仓库的当前状态与缓存的状态，判断仓库是否发生了变化。
    如果仓库发生变化，会清空该仓库的缓存。
    
    Args:
        self: GitOperations对象
        
    Returns:
        bool: 如果仓库发生变化返回True，否则返回False
              
    Examples:
        >>> if check_repo_change(git_ops):
        ...     print("仓库已发生变化")
    """
    repo_name = self.repo_path.name
    current_state = self.get_repo_state()
    
    if cache_manager.check_repo_change(repo_name, current_state):
        cache_manager.clear_repo_cache(repo_name)
        logger.info(f"仓库 {repo_name} 发生变化，已清空缓存")
        return True
    
    return False


def get_repo_size(self):
    """
    获取仓库大小
    
    该方法返回仓库的总大小，包括所有文件和对象。
    使用du命令获取大小，并使用缓存来提高性能。
    如果du命令失败，则使用Python遍历文件作为备用方案。
    
    Args:
        self: GitOperations对象
        
    Returns:
        str: 格式化后的大小字符串，如"1.2 MB"
              
    Examples:
        >>> size = get_repo_size(git_ops)
        >>> print(f"仓库大小: {size}")
    """
    self.check_repo_change()
    
    cache_key = f"repo_size_{self.repo_path.name}"
    
    cached_result = cache_manager.get(cache_key, max_age=86400)
    if cached_result is not None:
        logger.info(f"从缓存获取仓库体积: {cached_result}")
        return cached_result
    
    try:
        result = subprocess.run(
            ["du", "-s", "-b"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            total_size = int(result.stdout.strip().split()[0])
            formatted_size = self._format_size(total_size)
            cache_manager.set(cache_key, formatted_size)
            logger.info(f"获取仓库体积成功: {formatted_size}")
            return formatted_size
        else:
            logger.warning(f"获取仓库体积失败: {result.stderr}")
            return _get_repo_size_python(self)
    except subprocess.TimeoutExpired:
        logger.error(f"获取仓库体积超时")
        return _get_repo_size_python(self)
    except Exception as e:
        logger.error(f"获取仓库体积失败: {e}")
        return _get_repo_size_python(self)


def _get_repo_size_python(self):
    """
    使用Python获取仓库大小
    
    该方法是一个内部方法，使用Python遍历文件来获取仓库的总大小。
    当du命令失败或超时时，作为备用方案使用。
    支持裸仓库和工作目录仓库。
    
    Args:
        self: GitOperations对象
        
    Returns:
        str: 格式化后的大小字符串，如果获取失败则返回"计算中..."
    """
    try:
        total_size = 0
        
        repo_path_str = str(self.repo_path)
        is_bare_repo = self.repo_path.name.endswith('.git')
        
        if is_bare_repo:
            for root, dirs, files in os.walk(repo_path_str):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        file_size = os.path.getsize(file_path)
                        total_size += file_size
                    except Exception:
                        pass
        else:
            git_dir = os.path.join(repo_path_str, ".git")
            if os.path.exists(git_dir):
                for root, dirs, files in os.walk(git_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            file_size = os.path.getsize(file_path)
                            total_size += file_size
                        except Exception:
                            pass
            
            for root, dirs, files in os.walk(repo_path_str):
                if '.git' in dirs:
                    dirs.remove('.git')
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        file_size = os.path.getsize(file_path)
                        total_size += file_size
                    except Exception:
                        pass
        
        formatted_size = self._format_size(total_size)
        return formatted_size
    except Exception as e:
        logger.error(f"获取仓库体积失败(Python): {e}")
        return "计算中..."


def _format_size(self, size_bytes):
    """
    格式化大小
    
    该方法是一个内部方法，将字节数转换为人类可读的格式。
    
    Args:
        self: GitOperations对象
        size_bytes (int): 字节数
        
    Returns:
        str: 格式化后的大小字符串，如"1.2 MB"
              
    Examples:
        >>> size = _format_size(git_ops, 1234567)
        >>> print(size)
        '1.18 MB'
    """
    if size_bytes == 0:
        return "0 B"
    elif size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
