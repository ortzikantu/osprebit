#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 Hao Wu <hao.wu@ortzikantu.com>
# SPDX-License-Identifier: GPL-3.0-only

"""
提交路由模块

本模块提供了提交历史和提交详情页面的路由处理函数，
用于显示仓库的提交历史和单个提交的详细信息。

主要功能：
    - 提交历史页面渲染
    - 提交详情页面渲染
    - 分页支持
    - 分支和标签信息获取

使用示例：
    该模块由Litestar框架自动加载，无需手动调用。
"""

from litestar import Request
from litestar.response import Template
from pathlib import Path
import logging
from datetime import datetime

from .config import CONFIG
from .git_ops import GitOperations
from .routes_utils import _sort_branches

logger = logging.getLogger("osprebit")


async def repo_commits(repo_name: str, branch: str, request: Request) -> Template:
    """
    提交历史页面
    
    该函数处理提交历史页面的请求，返回指定分支的提交历史列表。
    支持分页显示，每页显示50条提交记录。
    
    Args:
        repo_name (str): 仓库名称
        branch (str): 分支名称
        request (Request): Litestar请求对象
        
    Returns:
        Template: 提交历史页面模板，如果发生错误返回500错误页面
    """
    try:
        git_ops = GitOperations.open_repo(repo_name)
        
        page = request.query_params.get("page", "1")
        per_page = 50
        
        try:
            page = int(page)
        except ValueError:
            page = 1
        
        page = max(1, page)
        
        offset = (page - 1) * per_page
        
        total_commits = git_ops.get_commit_count(branch)
        
        per_page = 50
        total_pages = (total_commits + per_page - 1) // per_page
        total_pages = max(1, total_pages)
        
        page = min(page, total_pages)
        
        offset = (page - 1) * per_page
        
        commits = git_ops.get_commit_history(branch, limit=per_page, offset=offset)
        branches = git_ops.get_branches()
        tags = git_ops.get_tags()
        
        default_branch = git_ops.get_default_branch()
        branches = _sort_branches(branches, default_branch)
        
        has_next = page < total_pages
        has_prev = page > 1
        next_page = page + 1 if has_next else None
        prev_page = page - 1 if has_prev else None
        
        return Template(
            template_name="commits.html",
            context={
                "site_name": CONFIG["site_name"],
                "version": CONFIG["version"],
                "repo_name": repo_name,
                "branch": branch,
                "branches": branches,
                "tags": tags,
                "commits": commits,
                "page": page,
                "per_page": per_page,
                "has_next": has_next,
                "has_prev": has_prev,
                "next_page": next_page,
                "prev_page": prev_page,
                "total_pages": total_pages,
            }
        )
    except Exception as e:
        return Template(
            template_name="error.html",
            context={
                "site_name": CONFIG["site_name"],
                "version": CONFIG["version"],
                "error_code": 500,
                "error_message": "服务器内部错误",
                "error_details": f"获取提交历史失败: {str(e)}"
            },
            status_code=500
        )


async def repo_commit(repo_name: str, branch: str, commit_id: str) -> Template:
    """
    单个提交详情页面
    
    该函数处理提交详情页面的请求，返回指定提交的详细信息，
    包括提交信息、作者、时间、文件变更等。
    
    Args:
        repo_name (str): 仓库名称
        branch (str): 分支名称
        commit_id (str): 提交ID
        
    Returns:
        Template: 提交详情页面模板，如果发生错误返回500错误页面
    """
    try:
        git_ops = GitOperations.open_repo(repo_name)
        commit_info = git_ops.get_commit_detail(commit_id)
        branches = git_ops.get_branches()
        tags = git_ops.get_tags()
        
        default_branch = git_ops.get_default_branch()
        branches = _sort_branches(branches, default_branch)
        
        return Template(
            template_name="commit.html",
            context={
                "site_name": CONFIG["site_name"],
                "version": CONFIG["version"],
                "repo_name": repo_name,
                "branch": branch,
                "branches": branches,
                "tags": tags,
                "commit": commit_info,
            }
        )
    except Exception as e:
        return Template(
            template_name="error.html",
            context={
                "site_name": CONFIG["site_name"],
                "version": CONFIG["version"],
                "error_code": 500,
                "error_message": "服务器内部错误",
                "error_details": f"获取提交详情失败: {str(e)}"
            },
            status_code=500
        )
