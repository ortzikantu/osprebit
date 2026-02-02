#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 Hao Wu <hao.wu@ortzikantu.com>
# SPDX-License-Identifier: GPL-3.0-only

"""
Git操作核心模块

本模块提供了Git仓库操作的核心功能，包括仓库的初始化和打开。
该模块是Git操作的基础类，其他Git操作模块都依赖于这个类。

主要功能：
    - 仓库初始化
    - 仓库打开和验证

使用示例：
    >>> git_ops = GitOperations.open_repo("my-repo")
    >>> print(f"仓库路径: {git_ops.repo_path}")
"""

from pathlib import Path
import pygit2
import logging
from datetime import datetime, timezone

from .models import TreeEntry, CommitInfo, RepoInfo
from .config import CONFIG

logger = logging.getLogger("osprebit")


class GitOperations:
    """
    Git操作核心类
    
    该类提供了Git仓库操作的核心功能，包括仓库的初始化和打开。
    该类是所有Git操作的基础类，其他Git操作模块都依赖于这个类。
    
    Attributes:
        repo_path (Path): 仓库路径
        
    Examples:
        >>> git_ops = GitOperations.open_repo("my-repo")
        >>> print(f"仓库路径: {git_ops.repo_path}")
    """
    
    def __init__(self, repo_path):
        """
        初始化Git操作对象
        
        该方法创建一个新的Git操作对象，并设置仓库路径。
        
        Args:
            repo_path (Path): 仓库路径
            
        Examples:
            >>> repo_path = Path("/path/to/repo")
            >>> git_ops = GitOperations(repo_path)
            >>> print(f"仓库路径: {git_ops.repo_path}")
        """
        self.repo_path = repo_path

    @classmethod
    def open_repo(cls, repo_name):
        """
        打开指定的Git仓库
        
        该方法根据仓库名称打开Git仓库，支持两种仓库格式：
        1. 裸仓库（.git后缀）
        2. 工作目录仓库（包含.git目录）
        
        Args:
            repo_name (str): 仓库名称
            
        Returns:
            GitOperations: Git操作对象
            
        Raises:
            ValueError: 如果仓库不存在或不是有效的Git仓库
            
        Examples:
            >>> git_ops = GitOperations.open_repo("my-repo")
            >>> print(f"仓库路径: {git_ops.repo_path}")
            
            >>> git_ops = GitOperations.open_repo("my-repo.git")
            >>> print(f"裸仓库路径: {git_ops.repo_path}")
        """
        repo_path_with_git = Path(CONFIG["repo_path"]) / f"{repo_name}.git"
        if repo_path_with_git.exists():
            return cls(repo_path_with_git)
        
        repo_path = Path(CONFIG["repo_path"]) / repo_name
        if repo_path.exists():
            is_git_repo = (repo_path / ".git").is_dir() or repo_path.name.endswith('.git')
            if is_git_repo:
                return cls(repo_path)
            else:
                raise ValueError(f"路径 {repo_path} 不是有效的git仓库")
        
        raise ValueError(f"仓库 {repo_name} 不存在")
