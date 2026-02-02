#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 Hao Wu <hao.wu@ortzikantu.com>
# SPDX-License-Identifier: GPL-3.0-only

"""
数据模型模块

本模块定义了应用中使用的数据模型类，包括文件树条目、
提交信息和仓库信息等。

主要功能：
    - TreeEntry: 文件树条目模型
    - CommitInfo: 提交信息模型
    - RepoInfo: 仓库信息模型

使用示例：
    >>> entry = TreeEntry("README.md", "README.md", "file", size=1024)
    >>> entry_dict = entry.to_dict()
"""

from datetime import datetime
from typing import Dict, Any

class TreeEntry:
    """
    文件树条目模型
    
    该类表示文件树中的一个条目，可以是文件或目录。
    """
    
    def __init__(self, name, path, type, size=None, commit_id=None, commit_time=None, commit_author=None, commit_message=None):
        """
        初始化文件树条目
        
        Args:
            name (str): 文件或目录名称
            path (str): 完整路径
            type (str): 类型，"dir"表示目录，"file"表示文件
            size (int, optional): 文件大小（字节），目录为0
            commit_id (str, optional): 最后一次提交ID
            commit_time (datetime, optional): 最后一次提交时间
            commit_author (str, optional): 最后一次提交作者
            commit_message (str, optional): 最后一次提交信息
        """
        self.name = name
        self.path = path
        self.type = type
        self.size = size
        self.commit_id = commit_id
        self.commit_time = commit_time
        self.commit_author = commit_author
        self.commit_message = commit_message
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            Dict[str, Any]: 包含所有属性的字典
        """
        return {
            "name": self.name,
            "path": self.path,
            "type": self.type,
            "size": self.size,
            "commit_id": self.commit_id,
            "commit_time": self.commit_time,
            "commit_author": self.commit_author,
            "commit_message": self.commit_message
        }

class CommitInfo:
    """
    提交信息模型
    
    该类表示一个Git提交的信息。
    """
    
    def __init__(self, id, author, email, time, message, short_id=None):
        """
        初始化提交信息
        
        Args:
            id (str): 提交ID
            author (str): 提交作者
            email (str): 提交者邮箱
            time (datetime): 提交时间
            message (str): 提交信息
            short_id (str, optional): 短提交ID，默认为前7位
        """
        self.id = id
        self.author = author
        self.email = email
        self.time = time
        self.message = message
        self.short_id = short_id if short_id else id[:7]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            Dict[str, Any]: 包含所有属性的字典
        """
        return {
            "id": self.id,
            "author": self.author,
            "email": self.email,
            "time": self.time,
            "message": self.message,
            "short_id": self.short_id
        }

class RepoInfo:
    """
    仓库信息模型
    
    该类表示一个Git仓库的信息。
    """
    
    def __init__(self, name, path, default_branch, description="", owner=""):
        """
        初始化仓库信息
        
        Args:
            name (str): 仓库名称
            path (str): 仓库路径
            default_branch (str): 默认分支名称
            description (str, optional): 仓库描述，默认为空字符串
            owner (str, optional): 仓库所有者，默认为空字符串
        """
        self.name = name
        self.path = path
        self.default_branch = default_branch
        self.description = description
        self.owner = owner
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            Dict[str, Any]: 包含所有属性的字典
        """
        return {
            "name": self.name,
            "path": self.path,
            "default_branch": self.default_branch,
            "description": self.description,
            "owner": self.owner
        }
