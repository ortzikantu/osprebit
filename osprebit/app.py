#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 Hao Wu <hao.wu@ortzikantu.com>
# SPDX-License-Identifier: GPL-3.0-only

"""
应用主模块

本模块是Osprebit应用的主入口，负责创建和配置Litestar应用实例。
包括路由注册、模板配置、静态文件服务、异常处理器等。

主要功能：
    - 创建Litestar应用实例
    - 注册所有路由处理器
    - 配置Jinja2模板引擎
    - 配置静态文件服务
    - 注册全局异常处理器
    - 提供应用启动入口

使用示例：
    该模块通常通过uvicorn启动：
    >>> uvicorn osprebit.app:app --host 0.0.0.0 --port 6789
"""

from litestar import Litestar, Request, Response
from litestar.exceptions import NotFoundException, InternalServerException
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.template.config import TemplateConfig
from litestar.static_files import create_static_files_router
from pathlib import Path
import traceback
import logging

from .config import CONFIG

logger = logging.getLogger("osprebit")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

from .routes import (
    home_route,
    repo_list_route,
    repo_tree_root_route,
    repo_tree_branch_route,
    repo_tree_route,
    repo_blob_route,
    repo_commits_route,
    repo_commit_route,
    repo_snapshot_route,
    git_info_refs_route,
    git_upload_pack_route,
    git_receive_pack_route
)
from .routes_errors import (
    global_exception_handler,
    not_found_exception_handler,
    internal_server_exception_handler
)

app = Litestar(
    route_handlers=[
        home_route,
        create_static_files_router(
            directories=[Path(__file__).parent / "static"],
            path="/static",
            name="static",
        ),
        repo_list_route, 
        repo_tree_root_route,
        repo_tree_branch_route,
        repo_tree_route,
        repo_blob_route,
        repo_commits_route,
        repo_commit_route,
        repo_snapshot_route,
        git_info_refs_route,
        git_upload_pack_route,
        git_receive_pack_route,
    ],
    template_config=TemplateConfig(
        directory=Path(__file__).parent / "templates",
        engine=JinjaTemplateEngine,
    ),
    debug=True,
    exception_handlers={
        Exception: global_exception_handler,
        NotFoundException: not_found_exception_handler,
        InternalServerException: internal_server_exception_handler,
    },
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "osprebit.app:app",
        host="0.0.0.0",
        port=CONFIG.get("port", 6789),
        timeout_keep_alive=300,
        timeout_graceful_shutdown=300,
        limit_concurrency=1000,
    )
