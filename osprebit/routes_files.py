#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 Hao Wu <hao.wu@ortzikantu.com>
# SPDX-License-Identifier: GPL-3.0-only

"""
文件路由模块

本模块提供了文件内容页面的路由处理函数，用于显示
仓库中指定分支和路径的文件内容。

主要功能：
    - 文件内容页面渲染
    - 文件路径验证
    - 面包屑导航生成
    - 文件内容分行显示

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


async def repo_blob(repo_name: str, branch: str, path: str) -> Template:
    """
    文件内容页
    
    该函数处理文件内容页面的请求，返回指定分支和路径的文件内容。
    包括文件内容、面包屑导航、分支列表等信息。
    
    Args:
        repo_name (str): 仓库名称
        branch (str): 分支名称
        path (str): 文件路径
        
    Returns:
        Template: 文件内容页面模板，如果文件路径为空返回400错误，
                 如果文件未找到返回404错误，如果发生其他错误返回500错误
    """
    if not path:
        return Template(
            template_name="error.html",
            context={
                "site_name": CONFIG["site_name"],
                "version": CONFIG["version"],
                "error_code": 400,
                "error_message": "文件路径不能为空",
                "error_details": "请提供有效的文件路径"
            },
            status_code=400
        )
    
    try:
        git_ops = GitOperations.open_repo(repo_name)
        blob_data = git_ops.get_blob_content(branch, path)
        branches = git_ops.get_branches()
        tags = git_ops.get_tags()
        
        default_branch = git_ops.get_default_branch()
        branches = _sort_branches(branches, default_branch)
        
        if "error" in blob_data:
            return Template(
                template_name="error.html",
                context={
                    "site_name": CONFIG["site_name"],
                    "version": CONFIG["version"],
                    "error_code": 404,
                    "error_message": "文件未找到",
                    "error_details": blob_data["error"]
                },
                status_code=404
            )
        
        file_path_parts = blob_data["file_path"].split("/")
        if len(file_path_parts) == 1:
            parent_url = f"/{repo_name}/tree/{branch}".replace("//", "/")
        else:
            parent_dir_path = "/".join(file_path_parts[:-1])
            parent_url = f"/{repo_name}/tree/{branch}/{parent_dir_path}".replace("//", "/")
        
        breadcrumbs = [{"name": repo_name, "url": f"/{repo_name}".replace("//", "/")}]
        breadcrumbs.append({"name": branch, "url": f"/{repo_name}/tree/{branch}".replace("//", "/")})
        if parent_dir_path:
            current_path = ""
            parts = [p for p in parent_dir_path.split("/") if p]
            for part in parts:
                current_path = f"{current_path}/{part}".lstrip("/")
                breadcrumbs.append({"name": part, "url": f"/{repo_name}/tree/{branch}/{current_path}".replace("//", "/")})
        breadcrumbs.append({"name": blob_data["file_name"], "url": ""})

        lines = blob_data["file_content"].split("\n")
        
        return Template(
            template_name="blob.html",
            context={
                "site_name": CONFIG["site_name"],
                "version": CONFIG["version"],
                "repo_name": repo_name,
                "branch": branch,
                "parent_url": parent_url,
                "branches": branches,
                "tags": tags,
                "breadcrumbs": breadcrumbs,
                "lines": lines,
                **blob_data,
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
                "error_details": f"获取文件内容失败: {str(e)}"
            },
            status_code=500
        )
