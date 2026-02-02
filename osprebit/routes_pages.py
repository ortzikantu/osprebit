#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 Hao Wu <hao.wu@ortzikantu.com>
# SPDX-License-Identifier: GPL-3.0-only

"""
页面路由模块

本模块提供了应用的所有页面路由处理函数，包括仓库列表页、
首页、仓库目录树页面等。

主要功能：
    - 仓库列表页面
    - 首页
    - 仓库目录树页面
    - 面包屑导航生成
    - 分支和标签信息获取

使用示例：
    该模块由Litestar框架自动加载，无需手动调用。
"""

from litestar import Request
from litestar.response import Template
from pathlib import Path
import logging
import concurrent.futures
from datetime import datetime

from .config import CONFIG
from .git_ops import GitOperations
from .heatmap import get_heatmap_data
from .overview_stats import OverviewStats
from .routes_utils import (
    _get_earliest_commit_year,
    _sort_branches,
    _generate_breadcrumbs,
    _get_parent_url
)

logger = logging.getLogger("osprebit")


async def repo_list(request: Request) -> Template:
    """
    仓库列表页
    
    该函数处理仓库列表页面的请求，返回所有仓库的列表、
    热力图数据、最近提交等信息。
    
    Args:
        request (Request): Litestar请求对象
        
    Returns:
        Template: 仓库列表页面模板
    """
    git_ops = GitOperations(Path(CONFIG["repo_path"]))
    repos = git_ops.get_all_repos()
    
    year = request.query_params.get("year")
    if year:
        try:
            year = int(year)
        except ValueError:
            year = None
    
    from .heatmap import get_all_repos_heatmap_data
    heatmap_data = get_all_repos_heatmap_data(Path(CONFIG["repo_path"]), year=year)
    
    from .recent_commits import get_recent_commits
    recent_commits = get_recent_commits(Path(CONFIG["repo_path"]), limit=6)
    
    current_year = datetime.now().year
    earliest_year = _get_earliest_commit_year()
    overview_stats = OverviewStats().get_service_stats()
    
    return Template(
        template_name="repo_list.html",
        context={
            "site_name": CONFIG["site_name"],
            "version": CONFIG["version"],
            "repos": repos,
            "heatmap_data": heatmap_data,
            "recent_commits": recent_commits,
            "current_year": current_year,
            "earliest_year": earliest_year,
            "overview_stats": overview_stats,
        }
    )


async def home() -> Template:
    """
    首页
    
    该函数处理首页的请求，返回首页模板。
    
    Returns:
        Template: 首页模板
    """
    return Template(
        template_name="home.html",
        context={
            "site_name": CONFIG["site_name"],
            "repo_path": CONFIG["repo_path"],
            "port": CONFIG["port"],
            "version": CONFIG["version"]
        }
    )


async def repo_tree_root(repo_name: str, request: Request) -> Template:
    """
    仓库根目录
    
    该函数处理仓库根目录页面的请求，返回仓库的根目录信息，
    包括文件树、分支、标签、热力图等数据。
    
    Args:
        repo_name (str): 仓库名称
        request (Request): Litestar请求对象
        
    Returns:
        Template: 仓库根目录页面模板，如果仓库不存在返回404错误页面
    """
    try:
        git_ops = GitOperations.open_repo(repo_name)
        default_branch = git_ops.get_default_branch()
        branch = default_branch
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_tree_entries = executor.submit(git_ops.get_tree_entries, branch, "")
            future_branches = executor.submit(git_ops.get_branches)
            future_tags = executor.submit(git_ops.get_tags)
            future_heatmap = executor.submit(get_heatmap_data, git_ops.repo_path, year=None)
            future_repo_size = executor.submit(git_ops.get_repo_size)
            future_commit_count = executor.submit(git_ops.get_commit_count, branch)
            
            tree_entries = future_tree_entries.result()
            branches = future_branches.result()
            tags = future_tags.result()
            heatmap_data = future_heatmap.result()
            repo_size = future_repo_size.result()
            commit_count = future_commit_count.result()
        
        branches = _sort_branches(branches, default_branch)
        
        is_tag = branch in tags
        tag_info = None
        snapshot_urls = None
        
        if is_tag:
            tag_info = git_ops.get_tag_info(branch)
            snapshot_urls = {
                "tar.gz": git_ops.get_snapshot_url(branch, "tar.gz")
            }
        
        breadcrumbs = [{"name": repo_name, "url": f"/{repo_name}".replace("//", "/")}]
        
        year = request.query_params.get("year")
        if year:
            try:
                year = int(year)
            except ValueError:
                year = None
            if year:
                heatmap_data = get_heatmap_data(git_ops.repo_path, year=year)
        
        current_year = datetime.now().year
        earliest_year = _get_earliest_commit_year()
        
        logger.info(f"仓库 {repo_name} 体积: {repo_size}")
        logger.info(f"仓库 {repo_name} 分支 {branch} 提交次数: {commit_count}")

        return Template(
            template_name="repo_tree.html",
            context={
                "site_name": CONFIG["site_name"],
                "version": CONFIG["version"],
                "base_url": CONFIG["base_url"],
                "port": CONFIG["port"],
                "repo_name": repo_name,
                "branch": branch,
                "branches": branches,
                "tags": tags,
                "is_tag": is_tag,
                "tag_info": tag_info,
                "snapshot_urls": snapshot_urls,
                "path": "",
                "parent_url": "",
                "breadcrumbs": breadcrumbs,
                "tree_entries": tree_entries,
                "heatmap_data": heatmap_data,
                "current_year": current_year,
                "earliest_year": earliest_year,
                "repo_size": repo_size,
                "commit_count": commit_count,
            }
        )
    except ValueError as e:
        if "仓库" in str(e) and "不存在" in str(e):
            return Template(
                template_name="error.html",
                context={
                    "site_name": CONFIG["site_name"],
                    "version": CONFIG["version"],
                    "error_code": 404,
                    "error_message": "仓库不存在",
                    "error_details": str(e)
                },
                status_code=404
            )
        else:
            return Template(
                template_name="error.html",
                context={
                    "site_name": CONFIG["site_name"],
                    "version": CONFIG["version"],
                    "error_code": 500,
                    "error_message": "服务器内部错误",
                    "error_details": f"加载仓库失败: {str(e)}"
                },
                status_code=500
            )
    except Exception as e:
        return Template(
            template_name="error.html",
            context={
                "site_name": CONFIG["site_name"],
                "version": CONFIG["version"],
                "error_code": 500,
                "error_message": "服务器内部错误",
                "error_details": f"加载仓库失败: {str(e)}"
            },
            status_code=500
        )


async def _repo_tree_impl(repo_name: str, branch: str, path: str, request: Request = None) -> Template:
    """
    仓库目录树实现
    
    该函数是仓库目录树页面的内部实现函数，处理指定分支和路径的
    目录树请求，返回目录树信息。
    
    Args:
        repo_name (str): 仓库名称
        branch (str): 分支名称
        path (str): 目录路径
        request (Request): Litestar请求对象，默认为None
        
    Returns:
        Template: 仓库目录树页面模板，如果仓库不存在或路径无效返回错误页面
    """
    try:
        git_ops = GitOperations.open_repo(repo_name)
        tree_entries = git_ops.get_tree_entries(branch, path)
        branches = git_ops.get_branches()
        tags = git_ops.get_tags()
        
        default_branch = git_ops.get_default_branch()
        branches = _sort_branches(branches, default_branch)
        
        is_tag = branch in tags
        tag_info = None
        snapshot_urls = None
        
        if is_tag:
            tag_info = git_ops.get_tag_info(branch)
            snapshot_urls = {
                "tar.gz": git_ops.get_snapshot_url(branch, "tar.gz")
            }
        
        parent_url = _get_parent_url(repo_name, branch, path)
        breadcrumbs = _generate_breadcrumbs(repo_name, branch, path)
        
        year = None
        if request:
            year = request.query_params.get("year")
            if year:
                try:
                    year = int(year)
                except ValueError:
                    year = None
        
        heatmap_data = get_heatmap_data(git_ops.repo_path, year=year)
        current_year = datetime.now().year
        earliest_year = _get_earliest_commit_year()
        repo_size = git_ops.get_repo_size()
        commit_count = git_ops.get_commit_count(branch)

        return Template(
            template_name="repo_tree.html",
            context={
                "site_name": CONFIG["site_name"],
                "version": CONFIG["version"],
                "base_url": CONFIG["base_url"],
                "port": CONFIG["port"],
                "repo_name": repo_name,
                "branch": branch,
                "branches": branches,
                "tags": tags,
                "is_tag": is_tag,
                "tag_info": tag_info,
                "snapshot_urls": snapshot_urls,
                "path": path,
                "parent_url": parent_url,
                "breadcrumbs": breadcrumbs,
                "tree_entries": tree_entries,
                "heatmap_data": heatmap_data,
                "current_year": current_year,
                "earliest_year": earliest_year,
                "repo_size": repo_size,
                "commit_count": commit_count,
            }
        )
    except ValueError as e:
        if "仓库" in str(e) and "不存在" in str(e):
            return Template(
                template_name="error.html",
                context={
                    "site_name": CONFIG["site_name"],
                    "version": CONFIG["version"],
                    "error_code": 404,
                    "error_message": "仓库不存在",
                    "error_details": str(e)
                },
                status_code=404
            )
        else:
            return Template(
                template_name="error.html",
                context={
                    "site_name": CONFIG["site_name"],
                    "version": CONFIG["version"],
                    "error_code": 404,
                    "error_message": "资源未找到",
                    "error_details": str(e)
                },
                status_code=404
            )
    except Exception as e:
        return Template(
            template_name="error.html",
            context={
                "site_name": CONFIG["site_name"],
                "version": CONFIG["version"],
                "error_code": 500,
                "error_message": "服务器内部错误",
                "error_details": f"加载目录失败: {str(e)}"
            },
            status_code=500
        )
