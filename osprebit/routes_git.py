#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 Hao Wu <hao.wu@ortzikantu.com>
# SPDX-License-Identifier: GPL-3.0-only

"""
Git协议路由模块

本模块提供了Git协议相关的路由处理函数，包括快照下载、
info/refs、upload-pack和receive-pack等Git HTTP协议端点。

主要功能：
    - 仓库快照下载（tar.gz格式）
    - Git info/refs端点（获取引用信息）
    - Git upload-pack端点（处理Pull/Fetch）
    - Git receive-pack端点（处理Push）
    - Git请求认证

使用示例：
    该模块由Litestar框架自动加载，无需手动调用。
"""

from litestar import Request, Response, get, post
from litestar.response import Template
from pathlib import Path
import logging
import subprocess
import tempfile
import os

from .config import CONFIG
from .git_ops import GitOperations
from .auth import authenticate_with_token

logger = logging.getLogger("osprebit")


async def repo_snapshot(repo_name: str, tag_name: str, format: str) -> Response:
    """
    下载snapshot
    
    该函数处理快照下载请求，生成指定标签的tar.gz格式快照文件。
    
    Args:
        repo_name (str): 仓库名称
        tag_name (str): 标签名称
        format (str): 快照格式，目前仅支持"tar.gz"
        
    Returns:
        Response: 快照文件响应，如果格式不支持返回400错误，
                 如果标签不存在返回404错误，如果生成失败返回500错误
    """
    try:
        if format != "tar.gz":
            return Template(
                template_name="error.html",
                context={
                    "site_name": CONFIG["site_name"],
                    "version": CONFIG["version"],
                    "error_code": 400,
                    "error_message": "不支持的格式",
                    "error_details": f"不支持的格式: {format}，仅支持 tar.gz 格式"
                },
                status_code=400
            )
        
        git_ops = GitOperations.open_repo(repo_name)
        
        tags = git_ops.get_tags()
        if tag_name not in tags:
            return Template(
                template_name="error.html",
                context={
                    "site_name": CONFIG["site_name"],
                    "version": CONFIG["version"],
                    "error_code": 404,
                    "error_message": "标签不存在",
                    "error_details": f"标签 {tag_name} 不存在"
                },
                status_code=404
            )
        
        repo_path = git_ops.repo_path
        
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as temp_file:
            temp_file_path = temp_file.name
        
        try:
            result = subprocess.run(
                ["git", "archive", "--format=tar.gz", "--output", temp_file_path, tag_name],
                cwd=str(repo_path),
                capture_output=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"git archive failed: {result.stderr.decode('utf-8', errors='ignore')}")
                return Template(
                    template_name="error.html",
                    context={
                        "site_name": CONFIG["site_name"],
                        "version": CONFIG["version"],
                        "error_code": 500,
                        "error_message": "生成快照失败",
                        "error_details": f"生成快照失败: {result.stderr.decode('utf-8', errors='ignore')}"
                    },
                    status_code=500
                )
            
            with open(temp_file_path, "rb") as f:
                content = f.read()
            
            headers = {
                "Content-Disposition": f"attachment; filename={repo_name}-{tag_name}.tar.gz",
                "Content-Type": "application/gzip",
                "Content-Length": str(len(content))
            }
            
            return Response(
                content=content,
                headers=headers,
                status_code=200
            )
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    except Exception as e:
        logger.error(f"下载snapshot失败: {e}")
        return Template(
            template_name="error.html",
            context={
                "site_name": CONFIG["site_name"],
                "version": CONFIG["version"],
                "error_code": 500,
                "error_message": "服务器内部错误",
                "error_details": f"下载snapshot失败: {str(e)}"
            },
            status_code=500
        )


async def handle_git_request(request: Request, service: str) -> Response:
    """
    处理Git HTTP请求
    
    该函数是Git HTTP协议的通用处理函数，处理info/refs、
    upload-pack和receive-pack等Git协议请求。
    
    Args:
        request (Request): Litestar请求对象
        service (str): Git服务名称，如"git-upload-pack"或"git-receive-pack"
        
    Returns:
        Response: Git协议响应，如果仓库不存在返回404，
                 如果认证失败返回401，如果处理失败返回500或504
    """
    try:
        repo_name = request.path_params.get("repo_name")
        if not repo_name:
            return Response(status_code=404)

        repo_path = Path(CONFIG["repo_path"]) / f"{repo_name}.git"
        if not repo_path.exists():
            repo_path = Path(CONFIG["repo_path"]) / repo_name
        if not repo_path.exists():
            return Response(content=b"", status_code=404)

        if service == "git-receive-pack":
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                logger.info(f"Git info/refs without auth header from {request.client.host if request.client else 'unknown'}")
                return Response(
                    content=b"",
                    status_code=401,
                    headers={"WWW-Authenticate": "Basic realm=Git Push"}
                )
            
            logger.info(f"Git info/refs with auth header: {auth_header[:20]}... from {request.client.host if request.client else 'unknown'}")
            
            try:
                if not authenticate_with_token(auth_header):
                    logger.warning(f"Invalid token from {request.client.host if request.client else 'unknown'}")
                    return Response(content=b"", status_code=401)
                logger.info(f"Valid token from {request.client.host if request.client else 'unknown'}")
            except Exception as e:
                logger.error(f"Auth error: {e} from {request.client.host if request.client else 'unknown'}")
                return Response(content=b"", status_code=401)

        if request.method == "GET":
            git_command = service.replace("git-", "")
            result = subprocess.run(
                ["git", git_command, "--advertise-refs", str(repo_path)],
                capture_output=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"Git {service} --advertise-refs failed: {result.stderr.decode('utf-8', errors='ignore')}")
                return Response(content=b"", status_code=500)
            
            service_line = f"# service={service}\n"
            pkt_len = len(service_line) + 4
            pkt_header = f"{pkt_len:04x}{service_line}0000"
            response_content = pkt_header.encode("utf-8") + result.stdout
            
            return Response(
                content=response_content,
                status_code=200,
                headers={
                    "Content-Type": f"application/x-{service}-advertisement",
                    "Cache-Control": "no-cache"
                }
            )
        else:
            git_command = service.replace("git-", "")
            
            process = subprocess.Popen(
                ["git", git_command, "--stateless-rpc", str(repo_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1024*1024
            )
            
            try:
                async for chunk in request.stream():
                    process.stdin.write(chunk)
                    process.stdin.flush()
                
                process.stdin.close()
                
                stdout, stderr = process.communicate(timeout=300)
                
                if process.returncode != 0:
                    logger.error(f"Git {service} failed: {stderr.decode('utf-8', errors='ignore')}")
                    return Response(content=b"", status_code=500)
                
                return Response(
                    content=stdout,
                    status_code=200,
                    headers={
                        "Content-Type": f"application/x-{service}-result",
                        "Cache-Control": "no-cache"
                    }
                )
            except subprocess.TimeoutExpired:
                process.kill()
                logger.error(f"Git {service} timeout")
                return Response(content=b"", status_code=504)
            except Exception as e:
                if process:
                    process.kill()
                logger.error(f"Git {service} error: {str(e)}")
                return Response(content=b"", status_code=500)
    except Exception as e:
        logger.error(f"Git request error: {e}")
        return Response(content=b"", status_code=500)


async def git_info_refs(request: Request) -> Response:
    """
    Git info/refs端点
    
    该函数处理Git协议的info/refs请求，用于Git客户端获取引用信息。
    
    Args:
        request (Request): Litestar请求对象
        
    Returns:
        Response: Git协议响应
    """
    service = request.query_params.get("service")
    if not service or not service.startswith("git-"):
        return Response(status_code=400)
    return await handle_git_request(request, service)


async def git_upload_pack(request: Request) -> Response:
    """
    处理Git Pull/Fetch
    
    该函数处理Git协议的upload-pack请求，用于Git客户端拉取代码。
    
    Args:
        request (Request): Litestar请求对象
        
    Returns:
        Response: Git协议响应
    """
    return await handle_git_request(request, "git-upload-pack")


async def git_receive_pack(request: Request) -> Response:
    """
    处理Git Push
    
    该函数处理Git协议的receive-pack请求，用于Git客户端推送代码。
    需要进行身份验证，推送成功后会清空仓库缓存。
    
    Args:
        request (Request): Litestar请求对象
        
    Returns:
        Response: Git协议响应，如果认证失败返回401，
                 如果处理失败返回500错误
    """
    try:
        repo_name = request.path_params.get("repo_name")
        if not repo_name:
            return Response(content=b"", status_code=404)

        repo_path = Path(CONFIG["repo_path"]) / f"{repo_name}.git"
        if not repo_path.exists():
            repo_path = Path(CONFIG["repo_path"]) / repo_name
        if not repo_path.exists():
            return Response(content=b"", status_code=404)

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.info(f"Git push without auth header from {request.client.host if request.client else 'unknown'}")
            return Response(
                content=b"",
                status_code=401,
                headers={"WWW-Authenticate": "Token realm=Git Push"}
            )
        
        logger.info(f"Git push with auth header: {auth_header[:20]}... from {request.client.host if request.client else 'unknown'}")
        
        try:
            if not authenticate_with_token(auth_header):
                logger.warning(f"Invalid token from {request.client.host if request.client else 'unknown'}")
                return Response(content=b"", status_code=401)
            logger.info(f"Valid token from {request.client.host if request.client else 'unknown'}")
        except Exception as e:
            logger.error(f"Auth error: {e} from {request.client.host if request.client else 'unknown'}")
            return Response(content=b"", status_code=401)

        import subprocess
        
        process = subprocess.Popen(
            ["git", "receive-pack", "--stateless-rpc", str(repo_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )
        
        try:
            while True:
                message = await request.receive()
                if message["type"] == "http.request":
                    body = message.get("body", b"")
                    if body:
                        process.stdin.write(body)
                        process.stdin.flush()
                    if not message.get("more_body", False):
                        break
                elif message["type"] == "http.disconnect":
                    break
        finally:
            process.stdin.close()
        
        stdout, stderr = process.communicate(timeout=300)
        
        if process.returncode != 0:
            logger.error(f"Git receive-pack failed: {stderr.decode('utf-8', errors='ignore')}")
            return Response(content=b"", status_code=500)
        
        from .cache_manager import cache_manager
        cache_manager.clear_repo_cache(repo_name)
        logger.info(f"仓库 {repo_name} 发生变化，已清空缓存")
        
        return Response(
            content=stdout,
            status_code=200,
            headers={
                "Content-Type": "application/x-git-receive-pack-result",
                "Cache-Control": "no-cache"
            }
        )
    except Exception as e:
        logger.error(f"Git receive-pack error: {e}")
        return Response(content=b"", status_code=500)
