#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 Hao Wu <hao.wu@ortzikantu.com>
# SPDX-License-Identifier: GPL-3.0-only

"""
Git提交操作模块

本模块提供了Git仓库提交相关的操作功能，包括获取提交历史、
提交详情、提交数量等功能。

主要功能：
    - 获取指定路径的最后提交信息
    - 获取分支的提交总数
    - 获取提交历史列表
    - 获取提交详细信息

使用示例：
    >>> history = get_commit_history(git_ops, "main", limit=10)
    >>> detail = get_commit_detail(git_ops, commit_id)
"""

import pygit2
import subprocess
import logging
from datetime import datetime, timezone

from .models import CommitInfo
from .cache_manager import cache_manager

logger = logging.getLogger("osprebit")


def _get_last_commit_for_path(self, path, commit):
    """
    获取指定路径在指定提交之前的最后一次提交
    
    该方法是一个内部方法，用于获取指定路径在指定提交之前的
    最后一次提交信息。使用git log命令获取提交信息，并使用
    缓存来提高性能。
    
    Args:
        self: GitOperations对象
        path (str): 路径
        commit (Commit): pygit2.Commit对象
        
    Returns:
        dict|None: 提交信息字典，包含以下键：
            - id (str): 提交ID
            - author (str): 提交作者
            - email (str): 提交者邮箱
            - time (datetime): 提交时间
            - message (str): 提交信息
            如果获取失败则返回None
    """
    cache_key = f"last_commit_{self.repo_path.name}_{str(commit.id)}_{path}"
    
    cached_result = cache_manager.get(cache_key, max_age=86400)
    if cached_result is not None:
        return cached_result
    
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--follow", "--format=%H|%an|%ae|%at|%s", str(commit.id), "--", path],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            timeout=3
        )
        
        if result.returncode == 0:
            if result.stdout and result.stdout.strip():
                parts = result.stdout.strip().split("|", 4)
                if len(parts) == 5:
                    commit_id, author, email, timestamp, message = parts
                    commit_time = datetime.fromtimestamp(int(timestamp))
                    commit_info = CommitInfo(
                        id=commit_id,
                        author=author,
                        email=email,
                        time=commit_time,
                        message=message
                    )
                    commit_info_dict = commit_info.to_dict()
                    cache_manager.set(cache_key, commit_info_dict)
                    return commit_info_dict
        elif result.returncode == 128:
            logger.debug(f"Git log returned error 128 for path '{path}'")
    except subprocess.TimeoutExpired:
        logger.debug(f"Git log command timed out for path '{path}'")
    except Exception as e:
        logger.debug(f"获取文件提交信息失败: {e}, path: {path}")
    
    return None


def get_commit_count(self, branch):
    """
    获取指定分支的提交总数
    
    该方法返回指定分支的提交总数，使用git rev-list命令
    获取提交数量，并使用缓存来提高性能。如果git命令失败，
    则使用pygit2库作为备用方案。
    
    Args:
        self: GitOperations对象
        branch (str): 分支名称
        
    Returns:
        int: 提交总数
    """
    self.check_repo_change()
    
    cache_key = f"commit_count_{self.repo_path.name}_{branch}"
    
    cached_result = cache_manager.get(cache_key, max_age=86400)
    if cached_result is not None:
        logger.info(f"从缓存获取提交数: {cached_result}")
        return cached_result
    
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", branch],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            commit_count = int(result.stdout.strip())
            cache_manager.set(cache_key, commit_count)
            logger.info(f"获取提交数成功: {commit_count}")
            return commit_count
        else:
            logger.warning(f"获取提交数失败: {result.stderr}")
            return _get_commit_count_pygit2(self, branch)
    except subprocess.TimeoutExpired:
        logger.error(f"获取提交数超时")
        return _get_commit_count_pygit2(self, branch)
    except Exception as e:
        logger.error(f"获取提交数失败: {e}")
        return _get_commit_count_pygit2(self, branch)


def _get_commit_count_pygit2(self, branch):
    """
    使用pygit2获取指定分支的提交总数
    
    该方法是一个内部方法，使用pygit2库获取指定分支的提交总数。
    当git命令失败或超时时，作为备用方案使用。
    
    Args:
        self: GitOperations对象
        branch (str): 分支名称
        
    Returns:
        int: 提交总数，如果获取失败则返回0
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
                    raise ValueError(f"分支或标签 {branch} 不存在")

        if obj.type == 4:
            target = repo.get(obj.target)
            while target.type != 1:
                if target.type == 4:
                    target = repo.get(target.target)
                else:
                    raise ValueError(f"标签 {branch} 不指向一个提交")
            commit_id = target.id
        else:
            commit_id = obj.id

        commit_count = 0
        for commit in repo.walk(commit_id):
            commit_count += 1

        return commit_count
    except Exception as e:
        logger.error(f"获取提交数失败(pygit2): {e}")
        return 0


def get_commit_history(self, branch, limit=50, offset=0):
    """
    获取指定分支的提交历史
    
    该方法返回指定分支的提交历史列表，支持分页。
    提交按时间倒序排列，最新的提交在前。
    
    Args:
        self: GitOperations对象
        branch (str): 分支名称
        limit (int, optional): 每页数量，默认为50
        offset (int, optional): 偏移量，默认为0
        
    Returns:
        list[dict]: 提交历史列表，每个元素包含以下键：
            - id (str): 提交ID
            - short_id (str): 短提交ID（前7位）
            - author (str): 提交作者
            - email (str): 提交者邮箱
            - time (datetime): 提交时间
            - message (str): 提交信息
            
    Raises:
        ValueError: 如果分支或标签不存在
        
    Examples:
        >>> commits = get_commit_history(git_ops, "main", limit=10)
        >>> for commit in commits:
        ...     print(f"{commit['short_id']}: {commit['message']}")
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
                    raise ValueError(f"分支或标签 {branch} 不存在")

        if obj.type == 4:
            target = repo.get(obj.target)
            while target.type != 1:
                if target.type == 4:
                    target = repo.get(target.target)
                else:
                    raise ValueError(f"标签 {branch} 不指向一个提交")
            commit_id = target.id
        else:
            commit_id = obj.id

        commits = []
        skipped = 0
        for commit in repo.walk(commit_id, pygit2.GIT_SORT_TIME):
            if skipped < offset:
                skipped += 1
                continue
            
            commit_id = str(commit.id)
            commit_info = CommitInfo(
                id=commit_id,
                short_id=commit_id[:7],
                author=commit.author.name,
                email=commit.author.email,
                time=datetime.fromtimestamp(commit.author.time, timezone.utc),
                message=commit.message.strip()
            )
            commits.append(commit_info.to_dict())
            if len(commits) >= limit:
                break

        return commits
    except Exception as e:
        logger.error(f"获取提交历史失败: {e}")
        return []


def get_commit_detail(self, commit_id):
    """
    获取指定提交的详细信息
    
    该方法返回指定提交的详细信息，包括提交信息、作者、
    提交时间、父提交、修改的文件列表等。
    
    Args:
        self: GitOperations对象
        commit_id (str): 提交ID
        
    Returns:
        dict: 提交详细信息字典，包含以下键：
            - id (str): 提交ID
            - short_id (str): 短提交ID（前7位）
            - author (str): 提交作者
            - email (str): 提交者邮箱
            - time (datetime): 提交时间
            - message (str): 提交信息
            - parents (list): 父提交ID列表
            - changed_files (list): 修改的文件列表，每个元素包含path、status、diff等键
            
    Raises:
        Exception: 如果提交不存在或获取失败
        
    Examples:
        >>> detail = get_commit_detail(git_ops, commit_id)
        >>> print(f"提交: {detail['short_id']}")
        >>> print(f"作者: {detail['author']}")
        >>> print(f"信息: {detail['message']}")
    """
    try:
        repo = pygit2.Repository(str(self.repo_path))
        commit = repo.get(commit_id)
        
        parents = []
        for parent in commit.parents:
            parent_id = str(parent.id)
            parents.append({
                "id": parent_id,
                "short_id": parent_id[:7],
                "message": parent.message.strip()
            })
        
        changed_files = []
        try:
            if commit.parents:
                parent = commit.parents[0]
                diff = repo.diff(parent, commit)
                for patch in diff:
                    new_path = None
                    old_path = None
                    try:
                        if patch.delta.new_file:
                            new_path = patch.delta.new_file.path
                        if patch.delta.old_file:
                            old_path = patch.delta.old_file.path
                    except:
                        pass
                    
                    file_path = new_path if new_path else old_path
                    if file_path:
                        diff_text = patch.text
                        changed_files.append({
                            "path": file_path,
                            "status": patch.delta.status_char(),
                            "additions": 0,
                            "deletions": 0,
                            "diff": diff_text
                        })
        except Exception as e:
            logger.error(f"获取文件变更失败: {e}")
        
        commit_id_str = str(commit.id)
        commit_info = {
            "id": commit_id_str,
            "short_id": commit_id_str[:7],
            "author": commit.author.name,
            "email": commit.author.email,
            "time": datetime.fromtimestamp(commit.author.time, timezone.utc),
            "message": commit.message.strip(),
            "parents": parents,
            "changed_files": changed_files
        }
        
        return commit_info
    except Exception as e:
        logger.error(f"获取提交详情失败: {e}")
        raise
