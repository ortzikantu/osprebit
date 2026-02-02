#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 Hao Wu <hao.wu@ortzikantu.com>
# SPDX-License-Identifier: GPL-3.0-only

"""
Git操作模块

本模块提供了Git仓库操作的核心接口，包括仓库管理、分支管理、
提交历史查询、文件内容读取等功能。该模块将Git操作拆分为多个
子模块以提高代码的可维护性和可读性。

主要功能：
    - 仓库列表获取和查询
    - 分支和标签管理
    - 提交历史查询
    - 文件树和内容读取
    - 仓库状态和大小查询

使用示例：
    >>> git_ops = GitOperations.open_repo("my-repo")
    >>> branches = git_ops.get_branches()
    >>> commits = git_ops.get_commit_history("main", limit=10)
"""

from pathlib import Path
import logging

from .config import CONFIG
from .git_ops_core import GitOperations as GitOperationsCore
from .git_ops_repos import (
    get_all_repos,
    get_branches,
    get_default_branch,
    get_tags,
    get_tag_info,
    get_snapshot_url
)
from .git_ops_tree import (
    get_tree_entries,
    get_blob_content
)
from .git_ops_commits import (
    _get_last_commit_for_path,
    get_commit_count,
    _get_commit_count_pygit2,
    get_commit_history,
    get_commit_detail
)
from .git_ops_utils import (
    get_repo_state,
    check_repo_change,
    get_repo_size,
    _get_repo_size_python,
    _format_size
)

logger = logging.getLogger("osprebit")


class GitOperations(GitOperationsCore):
    """
    Git操作类
    
    该类提供了对Git仓库进行各种操作的接口，包括仓库管理、
    分支管理、提交历史查询、文件内容读取等功能。该类继承自
    GitOperationsCore，并通过委托模式调用各个子模块中的函数。
    
    Attributes:
        repo_path (Path): 仓库路径
        
    Examples:
        >>> git_ops = GitOperations.open_repo("my-repo")
        >>> branches = git_ops.get_branches()
        >>> for branch in branches:
        ...     print(branch["name"])
    """
    
    def get_all_repos(self):
        """
        获取所有仓库列表
        
        该方法会扫描配置的仓库目录，返回所有Git仓库的详细信息，
        包括仓库名称、路径、默认分支、描述、所有者和最后一次提交信息。
        
        Returns:
            list[dict]: 仓库信息列表，每个元素包含以下键：
                - name (str): 仓库名称
                - path (str): 仓库路径
                - default_branch (str): 默认分支名称
                - description (str): 仓库描述
                - owner (str): 仓库所有者
                - last_commit (dict|None): 最后一次提交信息，包含time、author、message
                
        Examples:
            >>> repos = git_ops.get_all_repos()
            >>> for repo in repos:
            ...     print(f"{repo['name']}: {repo['description']}")
        """
        return get_all_repos(self)
    
    def get_branches(self):
        """
        获取仓库的所有分支
        
        该方法返回仓库中所有本地分支的列表，包括分支名称和
        最后一次提交的时间。
        
        Returns:
            list[dict]: 分支信息列表，每个元素包含以下键：
                - name (str): 分支名称
                - commit_time (datetime|None): 最后一次提交时间，如果获取失败则为None
                
        Examples:
            >>> branches = git_ops.get_branches()
            >>> for branch in branches:
            ...     print(f"{branch['name']}: {branch['commit_time']}")
        """
        return get_branches(self)
    
    def get_default_branch(self):
        """
        获取仓库的默认分支
        
        该方法会尝试获取HEAD引用指向的分支，如果失败则返回
        第一个本地分支。
        
        Returns:
            str: 默认分支名称
            
        Examples:
            >>> default_branch = git_ops.get_default_branch()
            >>> print(f"默认分支: {default_branch}")
        """
        return get_default_branch(self)
    
    def get_tags(self):
        """
        获取仓库的所有标签
        
        该方法返回仓库中所有标签的列表。
        
        Returns:
            list[str]: 标签名称列表
            
        Examples:
            >>> tags = git_ops.get_tags()
            >>> for tag in tags:
            ...     print(f"标签: {tag}")
        """
        return get_tags(self)
    
    def get_tag_info(self, tag_name):
        """
        获取指定标签的详细信息
        
        该方法返回指定标签的详细信息，包括标签指向的提交ID、
        提交时间、作者和提交信息。
        
        Args:
            tag_name (str): 标签名称
            
        Returns:
            dict|None: 标签信息字典，包含以下键：
                - name (str): 标签名称
                - commit_id (str): 提交ID
                - commit_time (datetime): 提交时间
                - author (str): 提交作者
                - message (str): 提交信息
                如果标签不存在则返回None
                
        Examples:
            >>> tag_info = git_ops.get_tag_info("v1.0.0")
            >>> if tag_info:
            ...     print(f"标签 {tag_info['name']} 由 {tag_info['author']} 创建")
        """
        return get_tag_info(self, tag_name)
    
    def get_snapshot_url(self, tag_name, format='tar.gz'):
        """
        获取指定标签的快照下载URL
        
        该方法生成指定标签的快照下载URL，支持tar.gz格式。
        
        Args:
            tag_name (str): 标签名称
            format (str, optional): 快照格式，默认为'tar.gz'
            
        Returns:
            str: 快照下载URL
            
        Examples:
            >>> url = git_ops.get_snapshot_url("v1.0.0")
            >>> print(f"下载URL: {url}")
        """
        return get_snapshot_url(self, tag_name, format)
    
    def get_tree_entries(self, branch, path):
        """
        获取指定分支和路径的文件树
        
        该方法返回指定分支和路径下的文件和目录列表。
        
        Args:
            branch (str): 分支名称
            path (str): 路径，空字符串表示根目录
            
        Returns:
            list[dict]: 文件树条目列表，每个元素包含以下键：
                - name (str): 文件或目录名称
                - type (str): 类型，'tree'表示目录，'blob'表示文件
                - size (int): 文件大小（字节）
                - last_commit (dict): 最后一次提交信息
                
        Examples:
            >>> entries = git_ops.get_tree_entries("main", "src")
            >>> for entry in entries:
            ...     print(f"{entry['type']}: {entry['name']}")
        """
        return get_tree_entries(self, branch, path)
    
    def get_blob_content(self, branch, path):
        """
        获取指定分支和路径的文件内容
        
        该方法返回指定分支和路径的文件内容。
        
        Args:
            branch (str): 分支名称
            path (str): 文件路径
            
        Returns:
            tuple: 包含两个元素的元组：
                - content (str): 文件内容
                - size (int): 文件大小（字节）
                
        Examples:
            >>> content, size = git_ops.get_blob_content("main", "README.md")
            >>> print(f"文件大小: {size} 字节")
            >>> print(content)
        """
        return get_blob_content(self, branch, path)
    
    def _get_last_commit_for_path(self, path, commit):
        """
        获取指定路径在指定提交之前的最后一次提交
        
        该方法是一个内部方法，用于获取指定路径在指定提交之前的
        最后一次提交信息。
        
        Args:
            path (str): 路径
            commit (Commit): pygit2.Commit对象
            
        Returns:
            dict: 提交信息字典，包含id、time、author、message等键
        """
        return _get_last_commit_for_path(self, path, commit)
    
    def get_commit_count(self, branch):
        """
        获取指定分支的提交总数
        
        该方法返回指定分支的提交总数。
        
        Args:
            branch (str): 分支名称
            
        Returns:
            int: 提交总数
            
        Examples:
            >>> count = git_ops.get_commit_count("main")
            >>> print(f"main分支共有 {count} 次提交")
        """
        return get_commit_count(self, branch)
    
    def _get_commit_count_pygit2(self, branch):
        """
        使用pygit2获取指定分支的提交总数
        
        该方法是一个内部方法，使用pygit2库获取指定分支的提交总数。
        
        Args:
            branch (str): 分支名称
            
        Returns:
            int: 提交总数
        """
        return _get_commit_count_pygit2(self, branch)
    
    def get_commit_history(self, branch, limit=50, offset=0):
        """
        获取指定分支的提交历史
        
        该方法返回指定分支的提交历史列表，支持分页。
        
        Args:
            branch (str): 分支名称
            limit (int, optional): 每页数量，默认为50
            offset (int, optional): 偏移量，默认为0
            
        Returns:
            list[dict]: 提交历史列表，每个元素包含以下键：
                - id (str): 提交ID
                - short_id (str): 短提交ID（前7位）
                - time (datetime): 提交时间
                - author (str): 提交作者
                - message (str): 提交信息
                - parents (list): 父提交ID列表
                
        Examples:
            >>> commits = git_ops.get_commit_history("main", limit=10)
            >>> for commit in commits:
            ...     print(f"{commit['short_id']}: {commit['message']}")
        """
        return get_commit_history(self, branch, limit, offset)
    
    def get_commit_detail(self, commit_id):
        """
        获取指定提交的详细信息
        
        该方法返回指定提交的详细信息，包括提交信息、作者、
        提交时间、父提交、修改的文件列表等。
        
        Args:
            commit_id (str): 提交ID
            
        Returns:
            dict: 提交详细信息字典，包含以下键：
                - id (str): 提交ID
                - short_id (str): 短提交ID（前7位）
                - time (datetime): 提交时间
                - author (dict): 作者信息，包含name和email
                - committer (dict): 提交者信息，包含name和email
                - message (str): 提交信息
                - parents (list): 父提交ID列表
                - tree_id (str): 树对象ID
                - diff (list): 修改的文件列表
                
        Examples:
            >>> detail = git_ops.get_commit_detail(commit_id)
            >>> print(f"提交: {detail['short_id']}")
            >>> print(f"作者: {detail['author']['name']}")
            >>> print(f"信息: {detail['message']}")
        """
        return get_commit_detail(self, commit_id)
    
    def get_repo_state(self):
        """
        获取仓库状态
        
        该方法返回仓库的当前状态，包括各分支的HEAD提交ID。
        
        Returns:
            dict|None: 仓库状态字典，键为分支名称，值为HEAD提交ID，
                       如果获取失败则返回None
        """
        return get_repo_state(self)
    
    def check_repo_change(self):
        """
        检查仓库是否发生变化
        
        该方法比较仓库的当前状态与缓存的状态，判断仓库是否发生了变化。
        
        Returns:
            bool: 如果仓库发生变化返回True，否则返回False
        """
        return check_repo_change(self)
    
    def get_repo_size(self):
        """
        获取仓库大小
        
        该方法返回仓库的总大小，包括所有文件和对象。
        
        Returns:
            str: 格式化后的大小字符串，如"1.2 MB"
            
        Examples:
            >>> size = git_ops.get_repo_size()
            >>> print(f"仓库大小: {size}")
        """
        return get_repo_size(self)
    
    def _get_repo_size_python(self):
        """
        使用Python获取仓库大小
        
        该方法是一个内部方法，使用Python获取仓库的总大小。
        
        Returns:
            int: 仓库大小（字节）
        """
        return _get_repo_size_python(self)
    
    def _format_size(self, size_bytes):
        """
        格式化大小
        
        该方法是一个内部方法，将字节数转换为人类可读的格式。
        
        Args:
            size_bytes (int): 字节数
            
        Returns:
            str: 格式化后的大小字符串，如"1.2 MB"
        """
        return _format_size(self, size_bytes)
