#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 Hao Wu <hao.wu@ortzikantu.com>
# SPDX-License-Identifier: GPL-3.0-only

"""
路由工具函数模块

本模块提供了路由处理中使用的工具函数，包括获取最早提交年份、
排序分支、生成面包屑导航和获取上级目录URL等功能。

主要功能：
    - 获取所有仓库中最早的提交年份
    - 排序分支（默认分支在顶部）
    - 生成面包屑导航
    - 获取上级目录URL

使用示例：
    >>> earliest_year = _get_earliest_commit_year()
    >>> sorted_branches = _sort_branches(branches, "main")
    >>> breadcrumbs = _generate_breadcrumbs("myrepo", "main", "src/utils")
    >>> parent_url = _get_parent_url("myrepo", "main", "src/utils")
"""

from pathlib import Path
import logging
from datetime import datetime

from .config import CONFIG

logger = logging.getLogger("osprebit")


def _get_earliest_commit_year() -> int:
    """
    计算所有仓库中最早的commit年份
    
    该函数遍历所有仓库，查找所有分支的提交历史，
    返回最早的提交年份。
    
    Returns:
        int: 最早的提交年份，如果没有找到提交则返回当前年份
    """
    import pygit2
    current_year = datetime.now().year
    earliest_year = current_year
    
    try:
        repos_path = Path(CONFIG["repo_path"])
        
        if repos_path.exists():
            for repo_dir in repos_path.iterdir():
                if repo_dir.is_dir():
                    is_git_repo = (repo_dir / ".git").is_dir() or repo_dir.name.endswith('.git')
                    
                    if is_git_repo:
                        try:
                            repo = pygit2.Repository(str(repo_dir))
                            
                            branches = []
                            for branch_name in repo.branches.local:
                                branches.append(branch_name)
                            
                            for branch_name in branches:
                                try:
                                    branch = repo.branches[branch_name]
                                    commit = branch.peel(pygit2.Commit)
                                    
                                    visited = set()
                                    while commit:
                                        commit_id = str(commit.id)
                                        if commit_id in visited:
                                            break
                                        
                                        visited.add(commit_id)
                                        
                                        commit_date = datetime.fromtimestamp(commit.commit_time)
                                        
                                        if commit_date.year < earliest_year:
                                            earliest_year = commit_date.year
                                        
                                        if not commit.parents:
                                            break
                                        commit = commit.parents[0]
                                except Exception:
                                    pass
                        except Exception:
                            pass
    except Exception:
        pass
    
    return earliest_year


def _sort_branches(branches, default_branch):
    """
    排序分支
    
    该函数对分支列表进行排序，默认分支排在最前面，
    其他分支按最后提交时间倒序排列。
    
    Args:
        branches (list): 分支列表，每个元素包含name和commit_time字段
        default_branch (str): 默认分支名称
        
    Returns:
        list: 排序后的分支列表
    """
    sorted_branches = []
    default_branch_obj = None
    other_branches = []
    
    for b in branches:
        if b["name"] == default_branch:
            default_branch_obj = b
        else:
            other_branches.append(b)
    
    other_branches.sort(key=lambda x: x["commit_time"] if x["commit_time"] else datetime.min, reverse=True)
    
    if default_branch_obj:
        sorted_branches.append(default_branch_obj)
    sorted_branches.extend(other_branches)
    
    return sorted_branches


def _generate_breadcrumbs(repo_name, branch, path):
    """
    生成面包屑导航
    
    该函数根据仓库名称、分支名称和路径生成面包屑导航列表。
    
    Args:
        repo_name (str): 仓库名称
        branch (str): 分支名称
        path (str): 当前路径
        
    Returns:
        list: 面包屑导航列表，每个元素包含name和url字段
    """
    breadcrumbs = [{"name": repo_name, "url": f"/{repo_name}".replace("//", "/")}]
    
    if branch:
        breadcrumbs.append({"name": branch, "url": f"/{repo_name}/tree/{branch}".replace("//", "/")})
    
    if path:
        current_path = ""
        path_parts = [p for p in path.split("/") if p]
        for part in path_parts:
            current_path = f"{current_path}/{part}".lstrip("/")
            breadcrumbs.append({"name": part, "url": f"/{repo_name}/tree/{branch}/{current_path}".replace("//", "/")})
    
    return breadcrumbs


def _get_parent_url(repo_name, branch, path):
    """
    获取上级目录URL
    
    该函数根据仓库名称、分支名称和当前路径返回上级目录的URL。
    
    Args:
        repo_name (str): 仓库名称
        branch (str): 分支名称
        path (str): 当前路径
        
    Returns:
        str: 上级目录的URL
    """
    if not path:
        return f"/{repo_name}"
    
    path_parts = [p for p in path.split("/") if p]
    if len(path_parts) == 0:
        return f"/{repo_name}/tree/{branch}".replace("//", "/")
    else:
        parent_path = "/".join(path_parts[:-1])
        return f"/{repo_name}/tree/{branch}/{parent_path}".rstrip("/").replace("//", "/")
