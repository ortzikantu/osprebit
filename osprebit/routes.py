#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 Hao Wu <hao.wu@ortzikantu.com>
# SPDX-License-Identifier: GPL-3.0-only

"""
路由模块

本模块提供了应用的所有路由处理函数，包括页面路由、文件路由、
提交路由、Git协议路由等。该模块将路由处理函数委托给
各个子模块中的具体实现函数。

主要功能：
    - 仓库列表和首页路由
    - 文件树和文件内容路由
    - 提交历史和详情路由
    - Git协议路由（info/refs、upload-pack、receive-pack）
    - 快照下载路由

使用示例：
    该模块由Litestar框架自动加载，无需手动调用。
"""

from litestar import get, post, Request
from litestar.response import Template, Response
from pathlib import Path
import logging

from .config import CONFIG

logger = logging.getLogger("osprebit")

from .routes_pages import (
    repo_list,
    home,
    repo_tree_root,
    _repo_tree_impl
)
from .routes_files import (
    repo_blob
)
from .routes_commits import (
    repo_commits,
    repo_commit
)
from .routes_git import (
    repo_snapshot,
    git_info_refs,
    git_upload_pack,
    git_receive_pack
)
from .routes_errors import (
    global_exception_handler,
    not_found_exception_handler,
    internal_server_exception_handler
)

@get("/")
async def repo_list_route(request: Request) -> Template:
    """
    仓库列表页路由
    
    该路由处理根路径的请求，返回所有仓库的列表页面。
    
    Args:
        request (Request): Litestar请求对象
        
    Returns:
        Template: 仓库列表页面模板
    """
    return await repo_list(request)

@get("/hello")
async def home_route() -> Template:
    """
    首页路由
    
    该路由处理/hello路径的请求，返回首页。
    
    Returns:
        Template: 首页模板
    """
    return await home()

@get("/{repo_name:str}")
async def repo_tree_root_route(repo_name: str, request: Request) -> Template:
    """
    仓库根目录路由
    
    该路由处理仓库名称路径的请求，返回仓库的根目录页面。
    
    Args:
        repo_name (str): 仓库名称
        request (Request): Litestar请求对象
        
    Returns:
        Template: 仓库根目录页面模板
    """
    return await repo_tree_root(repo_name, request)

@get("/{repo_name:str}/tree/{branch:str}")
async def repo_tree_branch_route(repo_name: str, branch: str, request: Request) -> Template:
    """
    仓库分支根目录路由
    
    该路由处理仓库分支路径的请求，返回指定分支的根目录页面。
    
    Args:
        repo_name (str): 仓库名称
        branch (str): 分支名称
        request (Request): Litestar请求对象
        
    Returns:
        Template: 仓库分支根目录页面模板
    """
    return await _repo_tree_impl(repo_name, branch, "", request)

@get("/{repo_name:str}/tree/{branch:str}/{path:path}")
async def repo_tree_route(repo_name: str, branch: str, path: str = "", request: Request = None) -> Template:
    """
    仓库目录树路由
    
    该路由处理仓库目录树路径的请求，返回指定分支和路径的目录页面。
    
    Args:
        repo_name (str): 仓库名称
        branch (str): 分支名称
        path (str): 目录路径，默认为空字符串
        request (Request): Litestar请求对象，默认为None
        
    Returns:
        Template: 仓库目录树页面模板
    """
    return await _repo_tree_impl(repo_name, branch, path, request)

@get("/{repo_name:str}/blob/{branch:str}/{path:path}")
async def repo_blob_route(repo_name: str, branch: str, path: str) -> Template:
    """
    文件内容页路由
    
    该路由处理文件内容路径的请求，返回指定分支和路径的文件内容页面。
    
    Args:
        repo_name (str): 仓库名称
        branch (str): 分支名称
        path (str): 文件路径
        
    Returns:
        Template: 文件内容页面模板
    """
    return await repo_blob(repo_name, branch, path)

@get("/{repo_name:str}/commits/{branch:str}")
async def repo_commits_route(repo_name: str, branch: str, request: Request) -> Template:
    """
    提交历史页面路由
    
    该路由处理提交历史路径的请求，返回指定分支的提交历史页面。
    
    Args:
        repo_name (str): 仓库名称
        branch (str): 分支名称
        request (Request): Litestar请求对象
        
    Returns:
        Template: 提交历史页面模板
    """
    return await repo_commits(repo_name, branch, request)

@get("/{repo_name:str}/commit/{branch:str}/{commit_id:str}")
async def repo_commit_route(repo_name: str, branch: str, commit_id: str) -> Template:
    """
    单个提交详情页面路由
    
    该路由处理提交详情路径的请求，返回指定提交的详情页面。
    
    Args:
        repo_name (str): 仓库名称
        branch (str): 分支名称
        commit_id (str): 提交ID
        
    Returns:
        Template: 提交详情页面模板
    """
    return await repo_commit(repo_name, branch, commit_id)

@get("/{repo_name:str}/snapshot/{tag_name:str}/{format:str}")
async def repo_snapshot_route(repo_name: str, tag_name: str, format: str) -> Response:
    """
    下载snapshot路由
    
    该路由处理快照下载路径的请求，返回指定标签的快照文件。
    
    Args:
        repo_name (str): 仓库名称
        tag_name (str): 标签名称
        format (str): 快照格式，如'tar.gz'
        
    Returns:
        Response: 快照文件响应
    """
    return await repo_snapshot(repo_name, tag_name, format)

@get("/{repo_name:str}/info/refs")
async def git_info_refs_route(request: Request) -> Response:
    """
    Git info/refs端点路由
    
    该路由处理Git协议的info/refs请求，用于Git客户端获取引用信息。
    
    Args:
        request (Request): Litestar请求对象
        
    Returns:
        Response: Git协议响应
    """
    return await git_info_refs(request)

@post("/{repo_name:str}/git-upload-pack")
async def git_upload_pack_route(request: Request) -> Response:
    """
    处理Git Pull/Fetch路由
    
    该路由处理Git协议的upload-pack请求，用于Git客户端拉取代码。
    
    Args:
        request (Request): Litestar请求对象
        
    Returns:
        Response: Git协议响应
    """
    return await git_upload_pack(request)

@post("/{repo_name:str}/git-receive-pack", body_type=None)
async def git_receive_pack_route(request: Request) -> Response:
    """
    处理Git Push路由
    
    该路由处理Git协议的receive-pack请求，用于Git客户端推送代码。
    
    Args:
        request (Request): Litestar请求对象
        
    Returns:
        Response: Git协议响应
    """
    return await git_receive_pack(request)
