#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 Hao Wu <hao.wu@ortzikantu.com>
# SPDX-License-Identifier: GPL-3.0-only

"""
错误处理路由模块

本模块提供了全局异常处理器和特定HTTP状态码的错误处理函数，
用于统一处理应用中的各种错误情况。

主要功能：
    - 全局异常处理器（捕获所有未处理的异常）
    - 404错误处理器（资源未找到）
    - 500错误处理器（服务器内部错误）

使用示例：
    该模块由Litestar框架自动加载，无需手动调用。
"""

from litestar import Request
from litestar.exceptions import NotFoundException, InternalServerException
from litestar.response import Template
import logging
import traceback

from .config import CONFIG

logger = logging.getLogger("osprebit")


def global_exception_handler(request: Request, exc: Exception) -> Template:
    """
    全局异常处理器
    
    该函数捕获所有未处理的异常，记录错误日志并返回错误页面。
    
    Args:
        request (Request): Litestar请求对象
        exc (Exception): 异常对象
        
    Returns:
        Template: 错误页面模板，状态码为500
    """
    exc_traceback = traceback.format_exc()
    logger.error(f"Unhandled exception: {exc}\nTraceback: {exc_traceback}")
    
    return Template(
        template_name="error.html",
        context={
            "site_name": CONFIG["site_name"],
            "version": CONFIG["version"],
            "error_code": 500,
            "error_message": "服务器内部错误",
            "error_details": f"{str(exc)}\n\n{exc_traceback}" if logger.isEnabledFor(logging.DEBUG) else str(exc)
        },
        status_code=500
    )


def not_found_exception_handler(request: Request, exc: NotFoundException) -> Template:
    """
    404错误处理器
    
    该函数处理404错误（资源未找到），返回错误页面。
    
    Args:
        request (Request): Litestar请求对象
        exc (NotFoundException): 404异常对象
        
    Returns:
        Template: 错误页面模板，状态码为404
    """
    return Template(
        template_name="error.html",
        context={
            "site_name": CONFIG["site_name"],
            "version": CONFIG["version"],
            "error_code": 404,
            "error_message": "页面未找到",
            "error_details": str(exc)
        },
        status_code=404
    )


def internal_server_exception_handler(request: Request, exc: InternalServerException) -> Template:
    """
    500错误处理器
    
    该函数处理500错误（服务器内部错误），记录错误日志并返回错误页面。
    
    Args:
        request (Request): Litestar请求对象
        exc (InternalServerException): 500异常对象
        
    Returns:
        Template: 错误页面模板，状态码为500
    """
    exc_traceback = traceback.format_exc()
    logger.error(f"Internal server error: {exc}\nTraceback: {exc_traceback}")
    
    return Template(
        template_name="error.html",
        context={
            "site_name": CONFIG["site_name"],
            "version": CONFIG["version"],
            "error_code": 500,
            "error_message": "服务器内部错误",
            "error_details": str(exc)
        },
        status_code=500
    )
