#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 Hao Wu <hao.wu@ortzikantu.com>
# SPDX-License-Identifier: GPL-3.0-only

"""
Osprebit 模块

Osprebit是一个Git仓库浏览和管理工具，
提供仓库可视化、提交历史查看、文件浏览等功能。
"""

from .config import CONFIG

__version__ = CONFIG.get("version", "0.1.0-dev")
__author__ = "Hao Wu"
__email__ = "hao.wu@ortzikantu.com"
__license__ = "GPL-3.0-only"
