#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 Hao Wu <hao.wu@ortzikantu.com>
# SPDX-License-Identifier: GPL-3.0-only

"""
Git文件树操作模块

本模块提供了Git仓库文件树相关的操作功能，包括获取文件树条目
和文件内容读取等功能。

主要功能：
    - 获取指定分支和路径的文件树
    - 获取指定分支和路径的文件内容

使用示例：
    >>> entries = get_tree_entries(git_ops, "main", "src")
    >>> content = get_blob_content(git_ops, "main", "README.md")
"""

import pygit2
import logging
from datetime import datetime, timezone

from .models import TreeEntry, CommitInfo
from .cache_manager import cache_manager

logger = logging.getLogger("osprebit")


def get_tree_entries(self, branch, path):
    """
    获取指定分支和路径的文件树
    
    该方法返回指定分支和路径下的文件和目录列表，包括每个条目的
    最后一次提交信息。目录和文件分别排序后返回，目录在前。
    
    Args:
        self: GitOperations对象
        branch (str): 分支名称
        path (str): 路径，空字符串表示根目录
        
    Returns:
        list[dict]: 文件树条目列表，每个元素包含以下键：
            - name (str): 文件或目录名称
            - path (str): 完整路径
            - type (str): 类型，'dir'表示目录，'file'表示文件
            - size (int): 文件大小（字节），目录为0
            - commit_id (str|None): 最后一次提交ID
            - commit_time (datetime|None): 最后一次提交时间
            - commit_author (str|None): 最后一次提交作者
            - commit_message (str|None): 最后一次提交信息
            
    Raises:
        ValueError: 如果分支或标签不存在，或路径不是目录
        
    Examples:
        >>> entries = get_tree_entries(git_ops, "main", "src")
        >>> for entry in entries:
        ...     print(f"{entry['type']}: {entry['name']}")
    """
    self.check_repo_change()
    
    try:
        repo = pygit2.Repository(str(self.repo_path))
        
        try:
            if repo.is_empty:
                return []
        except Exception:
            pass
        
        try:
            obj = repo.revparse_single(branch)
        except Exception:
            try:
                obj = repo.revparse_single(f"refs/heads/{branch}")
            except Exception:
                try:
                    obj = repo.revparse_single(f"refs/tags/{branch}")
                except Exception:
                    try:
                        if repo.is_empty:
                            return []
                    except Exception:
                        pass
                    raise ValueError(f"分支或标签 {branch} 不存在")

        if obj.type == 4:
            target = repo.get(obj.target)
            while target.type != 1:
                if target.type == 4:
                    target = repo.get(target.target)
                else:
                    raise ValueError(f"标签 {branch} 不指向一个提交")
            commit = target
        else:
            commit = obj

        tree = commit.tree

        if path:
            for part in path.split("/"):
                if part:
                    tree = tree[part]
                    if tree.type != 2:
                        raise ValueError(f"{path} 不是目录")

        entries = []
        dirs = []
        files = []
        for entry in tree:
            if path:
                entry_path = f"{path}/{entry.name}".lstrip("/")
            else:
                entry_path = entry.name
            
            if entry.type == 2:
                commit_info = self._get_last_commit_for_path(entry_path, commit)
                tree_entry = TreeEntry(
                    name=entry.name,
                    path=entry_path,
                    type="dir",
                    commit_id=commit_info['id'] if commit_info else None,
                    commit_time=commit_info['time'] if commit_info else None,
                    commit_author=commit_info['author'] if commit_info else None,
                    commit_message=commit_info['message'] if commit_info else None
                )
                dirs.append(tree_entry.to_dict())
            elif entry.type == 3:
                commit_info = self._get_last_commit_for_path(entry_path, commit)
                file_size = 0
                try:
                    blob = repo[entry.id]
                    if blob.type == 3:
                        file_size = blob.size
                except:
                    pass
                
                tree_entry = TreeEntry(
                    name=entry.name,
                    path=entry_path,
                    type="file",
                    size=file_size,
                    commit_id=commit_info['id'] if commit_info else None,
                    commit_time=commit_info['time'] if commit_info else None,
                    commit_author=commit_info['author'] if commit_info else None,
                    commit_message=commit_info['message'] if commit_info else None
                )
                files.append(tree_entry.to_dict())
            else:
                logger.warning(f"未知的entry类型: {entry.type} for {entry.name}")
        
        dirs.sort(key=lambda x: x["name"].lower())
        files.sort(key=lambda x: x["name"].lower())
        entries = dirs + files

        return entries
    except Exception as e:
        logger.error(f"获取目录树失败: {e}")
        raise


def get_blob_content(self, branch, path):
    """
    获取指定分支和路径的文件内容
    
    该方法返回指定分支和路径的文件内容，包括文件大小和
    最后一次提交信息。
    
    Args:
        self: GitOperations对象
        branch (str): 分支名称
        path (str): 文件路径
        
    Returns:
        dict: 包含文件信息和内容的字典，包含以下键：
            - file_name (str): 文件名
            - file_path (str): 文件路径
            - file_content (str): 文件内容
            - file_size (int): 文件大小（字节）
            - commit_id (str|None): 最后一次提交ID
            - commit_author (str|None): 最后一次提交作者
            - commit_time (datetime|None): 最后一次提交时间
            - commit_message (str|None): 最后一次提交信息
            - error (str): 如果出错则包含错误信息
            
    Examples:
        >>> content = get_blob_content(git_ops, "main", "README.md")
        >>> print(f"文件大小: {content['file_size']} 字节")
        >>> print(content['file_content'])
    """
    try:
        repo = pygit2.Repository(str(self.repo_path))
        try:
            obj = repo.revparse_single(branch)
        except Exception:
            try:
                obj = repo.revparse_single(f"refs/heads/{branch}")
            except Exception:
                try:
                    obj = repo.revparse_single(f"refs/tags/{branch}")
                except Exception:
                    return {"error": f"分支或标签 {branch} 不存在"}

        if obj.type == 4:
            target = repo.get(obj.target)
            while target.type != 1:
                if target.type == 4:
                    target = repo.get(target.target)
                else:
                    return {"error": f"标签 {branch} 不指向一个提交"}
            commit = target
        else:
            commit = obj

        tree = commit.tree

        current = tree
        for part in path.split("/"):
            if part:
                if part not in current:
                    return {"error": f"文件 {path} 不存在"}
                current = current[part]
                if current.type == "tree":
                    return {"error": f"{path} 是目录，不是文件"}

        blob = repo[current.id]
        file_content = blob.data.decode("utf-8", errors="replace")

        commit_info = self._get_last_commit_for_path(path, commit)

        return {
            "file_name": path.split("/")[-1],
            "file_path": path,
            "file_content": file_content,
            "file_size": blob.size,
            "commit_id": commit_info['id'] if commit_info else None,
            "commit_author": commit_info['author'] if commit_info else None,
            "commit_time": commit_info['time'] if commit_info else None,
            "commit_message": commit_info['message'] if commit_info else None
        }
    except Exception as e:
        logger.error(f"获取文件内容失败: {e}")
        return {"error": f"获取文件内容失败: {str(e)}"}
