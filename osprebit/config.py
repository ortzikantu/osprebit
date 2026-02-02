#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 Hao Wu <hao.wu@ortzikantu.com>
# SPDX-License-Identifier: GPL-3.0-only

"""
配置管理模块

本模块负责加载和管理应用的配置信息，包括从pyproject.toml
读取版本号，从配置文件读取用户自定义配置等。

主要功能：
    - 从pyproject.toml读取版本号
    - 加载默认配置
    - 从用户配置文件读取自定义配置
    - 提供全局配置对象

使用示例：
    >>> from osprebit.config import CONFIG
    >>> print(CONFIG["site_name"])
    >>> print(CONFIG["port"])
"""

import os
import tomllib
from pathlib import Path

def get_version():
    """
    从 pyproject.toml 获取版本号
    
    该方法从项目根目录的pyproject.toml文件中读取版本号。
    
    Returns:
        str: 版本号，如果读取失败则返回"0.1.0-dev"
    """
    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, "rb") as f:
                pyproject_data = tomllib.load(f)
                return pyproject_data.get("project", {}).get("version", "0.1.0-dev")
    except Exception as e:
        print(f"读取版本号失败: {e}")
    return "0.1.0-dev"

DEFAULT_CONFIG = {
    "site_name": "Osprebit",
    "repo_path": "/home/hao/workshop/osprebit/repos",
    "port": 6789,
    "base_url": "http://192.168.10.69",
    "version": get_version()
}

def load_config():
    """
    读取配置文件
    
    该方法从用户配置文件（~/.config/osprebit/config.toml）读取配置，
    并与默认配置合并。
    
    Returns:
        dict: 合并后的配置字典
    """
    config = DEFAULT_CONFIG.copy()
    
    config_path = Path.home() / ".config" / "osprebit" / "config.toml"
    if config_path.exists():
        try:
            with open(config_path, "rb") as f:
                config_data = tomllib.load(f)
                config.update(config_data.get("osprebit", {}))
                print(f"已加载配置文件: {config_path}")
        except Exception as e:
            print(f"读取配置文件失败: {e}")
    else:
        print(f"配置文件不存在: {config_path}")
        print("使用默认配置")
    
    return config

CONFIG = load_config()
