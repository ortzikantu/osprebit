#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 Hao Wu <hao.wu@ortzikantu.com>
# SPDX-License-Identifier: GPL-3.0-only

"""
最近提交记录模块

本模块提供了获取所有仓库最新提交记录和贡献统计信息的功能。

主要功能：
    - get_recent_commits: 获取所有仓库的最新提交记录
    - get_contribution_stats: 获取贡献统计信息

使用示例：
    >>> from pathlib import Path
    >>> from osprebit.recent_commits import get_recent_commits
    >>> repo_path = Path("/path/to/repos")
    >>> recent_commits = get_recent_commits(repo_path, limit=10)
"""

from pathlib import Path
from typing import List, Dict
from datetime import datetime, timezone
import pygit2
import logging

logger = logging.getLogger("osprebit")


def get_recent_commits(repo_path: Path, limit: int = 6) -> List[Dict]:
    """
    获取所有仓库的最新提交记录
    
    Args:
        repo_path: 仓库根目录路径
        limit: 返回的最大记录数
    
    Returns:
        按时间排序的最新提交记录列表
    """
    all_commits = []
    
    # 遍历所有仓库目录
    try:
        # 直接遍历目录，与heatmap.py相同的方法
        for repo_dir in repo_path.iterdir():
            if repo_dir.is_dir():
                # 检查是否是git仓库
                if (repo_dir / ".git").is_dir() or repo_dir.name.endswith('.git'):
                    try:
                        # 获取仓库名称（去掉.git后缀）
                        repo_name = repo_dir.name
                        if repo_name.endswith('.git'):
                            repo_name = repo_name[:-4]
                        
                        # 直接使用pygit2打开仓库，避免使用GitOperations
                        try:
                            repo = pygit2.Repository(str(repo_dir))
                            
                            # 获取所有本地分支
                            local_branches = list(repo.branches.local)
                            
                            # 遍历所有分支
                            for branch_name in local_branches:
                                try:
                                    # 获取分支引用
                                    branch = repo.branches[branch_name]
                                    commit = branch.peel()
                                    
                                    # 遍历提交历史
                                    visited = set()
                                    for commit in repo.walk(commit.id):
                                        commit_id = str(commit.id)
                                        if commit_id in visited:
                                            break
                                        
                                        visited.add(commit_id)
                                        
                                        # 格式化提交时间（使用本地时间）
                                        commit_date = datetime.fromtimestamp(commit.author.time).strftime("%Y-%m-%d %H:%M")
                                        
                                        # 获取提交信息的第一行作为标题
                                        title = commit.message.split("\n")[0]
                                        if len(title) > 30:
                                            title = title[:30] + "..."
                                        
                                        # 添加到总列表
                                        all_commits.append({
                                            "repo_name": repo_name,
                                            "title": title,
                                            "author": commit.author.name,
                                            "date": commit_date,
                                            "commit_id": commit_id,
                                            "timestamp": commit.author.time  # 用于排序
                                        })
                                        
                                        # 限制每个分支的提交数量
                                        if len(visited) >= 10:
                                            break
                                except Exception:
                                    # 忽略单个分支的错误，继续处理其他分支
                                    pass
                        except Exception:
                            # 忽略仓库打开失败的错误
                            pass
                    except Exception:
                        # 忽略单个仓库的错误，继续处理其他仓库
                        pass
    except Exception:
        # 忽略整体错误，返回空列表
        pass
    

    
    # 按时间戳排序，获取最新的记录
    if all_commits:
        all_commits.sort(key=lambda x: x["timestamp"], reverse=True)
    
    # 返回指定数量的记录
    return all_commits[:limit]


def get_contribution_stats(repo_path: Path) -> Dict:
    """
    获取贡献统计信息
    
    Args:
        repo_path: 仓库根目录路径
    
    Returns:
        贡献统计信息
    """
    stats = {
        "total_commits": 0,
        "total_repos": 0,
        "recent_commits": []
    }
    
    all_commits = []
    
    try:
        # 遍历所有仓库目录
        for repo_dir in repo_path.iterdir():
            if repo_dir.is_dir():
                # 检查是否是git仓库
                if (repo_dir / ".git").is_dir() or repo_dir.name.endswith('.git'):
                    stats["total_repos"] += 1
                    try:
                        # 获取仓库名称（去掉.git后缀）
                        repo_name = repo_dir.name
                        if repo_name.endswith('.git'):
                            repo_name = repo_name[:-4]
                        
                        # 直接使用pygit2打开仓库
                        try:
                            repo = pygit2.Repository(str(repo_dir))
                            
                            # 获取所有本地分支
                            local_branches = list(repo.branches.local)
                            
                            # 遍历所有分支
                            for branch_name in local_branches:
                                try:
                                    # 获取分支引用
                                    branch = repo.branches[branch_name]
                                    commit = branch.peel()
                                    
                                    # 遍历提交历史
                                    visited = set()
                                    commit_count = 0
                                    for commit in repo.walk(commit.id):
                                        commit_id = str(commit.id)
                                        if commit_id in visited:
                                            break
                                        
                                        visited.add(commit_id)
                                        commit_count += 1
                                        
                                        # 格式化提交时间（使用本地时间）
                                        commit_date = datetime.fromtimestamp(commit.author.time).strftime("%Y-%m-%d %H:%M")
                                        
                                        # 获取提交信息的第一行作为标题
                                        message = commit.message.split("\n")[0]
                                        if len(message) > 50:
                                            message = message[:50] + "..."
                                        
                                        # 添加到总列表
                                        all_commits.append({
                                            "repo_name": repo_name,
                                            "message": message,
                                            "author": commit.author.name,
                                            "date": commit_date,
                                            "commit_id": commit_id,
                                            "timestamp": commit.author.time  # 用于排序
                                        })
                                        
                                        # 限制每个分支的提交数量
                                        if commit_count >= 100:
                                            break
                                except Exception as e:
                                    logger.debug(f"处理分支 {branch_name} 失败: {e}")
                                    # 忽略单个分支的错误，继续处理其他分支
                                    pass
                        except Exception as e:
                            logger.debug(f"打开仓库 {repo_name} 失败: {e}")
                            # 忽略仓库打开失败的错误
                            pass
                    except Exception as e:
                        logger.debug(f"处理仓库 {repo_dir.name} 失败: {e}")
                        # 忽略单个仓库的错误，继续处理其他仓库
                        pass
    except Exception as e:
        logger.error(f"获取贡献统计信息失败: {e}")
        # 忽略整体错误，返回当前统计信息
        pass
    
    # 更新总提交数
    stats["total_commits"] = len(all_commits)
    
    # 排序并获取最新的6条
    if all_commits:
        all_commits.sort(key=lambda x: x["timestamp"], reverse=True)
        stats["recent_commits"] = all_commits[:6]
    
    return stats
