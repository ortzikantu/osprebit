#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 Hao Wu <hao.wu@ortzikantu.com>
# SPDX-License-Identifier: GPL-3.0-only

"""
热力图生成模块

本模块提供了Git仓库提交热力图数据的生成功能，
包括单个仓库和所有仓库的提交数据统计。

主要功能：
    - HeatmapGenerator: 热力图生成器类
    - get_heatmap_data: 获取单个仓库的热力图数据
    - get_all_repos_heatmap_data: 获取所有仓库的热力图数据

使用示例：
    >>> from pathlib import Path
    >>> from osprebit.heatmap import get_heatmap_data
    >>> repo_path = Path("/path/to/repo")
    >>> data = get_heatmap_data(repo_path, 2025)
"""

import datetime
from typing import Dict, List, Optional
from pathlib import Path
import pygit2
import logging

from .cache_manager import cache_manager

logger = logging.getLogger("osprebit")

class HeatmapGenerator:
    """热力图生成器"""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.repo = None
        try:
            self.repo = pygit2.Repository(str(repo_path))
        except Exception as e:
            logger.error(f"初始化热力图生成器失败: {e}")
    
    def get_repo_state(self):
        """获取仓库当前状态
        
        Returns:
            仓库状态字典，包含各分支的HEAD提交ID
        """
        if not self.repo:
            return {}
        
        try:
            state = {}
            # 获取所有本地分支的HEAD提交ID
            for branch_name in self.repo.branches.local:
                try:
                    branch = self.repo.branches[branch_name]
                    commit = branch.peel()
                    state[branch_name] = str(commit.id)
                except Exception as e:
                    logger.debug(f"获取分支 {branch_name} 状态失败: {e}")
            return state
        except Exception as e:
            logger.error(f"获取仓库状态失败: {e}")
            return {}
    
    def check_repo_change(self):
        """检查仓库是否发生变化
        
        Returns:
            如果仓库发生变化返回True，否则返回False
        """
        repo_name = self.repo_path.name
        current_state = self.get_repo_state()
        
        # 检查仓库状态是否发生变化
        if cache_manager.check_repo_change(repo_name, current_state):
            # 仓库发生变化，清空缓存
            cache_manager.clear_repo_cache(repo_name)
            logger.info(f"仓库 {repo_name} 发生变化，已清空缓存")
            return True
        
        return False
    
    def get_commit_data(self, year: int) -> Dict[str, int]:
        """获取指定年份的提交数据"""
        # 检查仓库是否发生变化
        self.check_repo_change()
        
        # 生成缓存键
        cache_key = f"heatmap_commit_data_{self.repo_path.name}_{year}"
        
        # 尝试从缓存获取
        cached_result = cache_manager.get(cache_key, max_age=86400)  # 缓存1天
        if cached_result is not None:
            logger.info(f"从缓存获取热力图数据: {year}")
            return cached_result
        
        commit_data = {}
        
        if not self.repo:
            return commit_data
        
        try:
            # 获取所有分支
            branches = []
            for branch_name in self.repo.branches.local:
                branches.append(branch_name)
            
            # 获取所有提交
            visited = set()
            for branch_name in branches:
                try:
                    branch = self.repo.branches[branch_name]
                    commit = branch.peel()
                    
                    # 遍历提交历史
                    while commit:
                        commit_id = str(commit.id)
                        if commit_id in visited:
                            break
                        
                        visited.add(commit_id)
                        
                        # 计算提交日期
                        commit_date = datetime.datetime.fromtimestamp(commit.commit_time, datetime.timezone.utc)
                        
                        # 格式化为 YYYY-MM-DD
                        date_str = commit_date.strftime("%Y-%m-%d")
                        commit_data[date_str] = commit_data.get(date_str, 0) + 1
                        
                        # 获取父提交
                        if not commit.parents:
                            break
                        commit = commit.parents[0]
                except Exception as e:
                    logger.debug(f"处理分支 {branch_name} 失败: {e}")
            
            # 缓存结果
            cache_manager.set(cache_key, commit_data)
            logger.info(f"获取热力图数据成功: {year}, {len(commit_data)} 天")
        except Exception as e:
            logger.error(f"获取提交数据失败: {e}")
        
        return commit_data
    
    def generate_heatmap_data(self, year: int = None) -> Dict:
        """生成热力图数据"""
        # 如果未指定年份，使用当前年份
        if year is None:
            year = datetime.datetime.now(datetime.timezone.utc).year
        
        commit_data = self.get_commit_data(year)
        
        # 计算日期范围：指定年份的1月1日到12月31日
        start_date = datetime.datetime(year, 1, 1, tzinfo=datetime.timezone.utc)
        end_date = datetime.datetime(year, 12, 31, tzinfo=datetime.timezone.utc)
        
        # 调整开始日期到第一个周日
        # 周日是6，周一到周六是0-5
        while start_date.weekday() != 6:  # 6是周日
            start_date -= datetime.timedelta(days=1)
        
        # 调整结束日期到12月31日所在周的下一个周六，确保完整显示最后一周
        while end_date.weekday() != 5:  # 5是周六
            end_date += datetime.timedelta(days=1)
        
        # 生成日期网格
        weeks = []
        current_date = start_date
        
        while current_date <= end_date:
            week = []
            for _ in range(7):
                if current_date <= end_date:
                    date_str = current_date.strftime("%Y-%m-%d")
                    count = commit_data.get(date_str, 0)
                    week.append({
                        "date": date_str,
                        "count": count,
                        "color": self._get_color(count)
                    })
                else:
                    # 填充空数据
                    week.append({
                        "date": "",
                        "count": 0,
                        "color": "--heatmap-lightest"
                    })
                current_date += datetime.timedelta(days=1)
            weeks.append(week)
        
        # 计算总提交数（只统计指定年份的）
        total_commits = 0
        for date_str, count in commit_data.items():
            if date_str.startswith(str(year)):
                total_commits += count
        
        return {
            "year": year,
            "weeks": weeks,
            "total_commits": total_commits,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d")
        }
    
    def _get_color(self, count: int) -> str:
        """根据提交数量获取颜色"""
        return self._get_color_static(count)
    
    @staticmethod
    def _get_color_static(count: int) -> str:
        """根据提交数量获取颜色（静态方法）"""
        if count == 0:
            return "--heatmap-lightest"  # 背景色，浅灰色
        elif count < 2:
            return "--heatmap-lighter"  # 极浅粉色
        elif count < 4:
            return "--heatmap-light"  # 浅粉色
        elif count < 8:
            return "--heatmap-medium"  # 中粉色
        elif count < 16:
            return "--heatmap-dark"  # 深粉色
        else:
            return "--heatmap-darkest"  # 主色调，深红色

# 工厂函数
def get_heatmap_data(repo_path: Path, year: int = None) -> Dict:
    """获取热力图数据"""
    generator = HeatmapGenerator(repo_path)
    return generator.generate_heatmap_data(year)

# 获取所有仓库的热力图数据
def get_all_repos_heatmap_data(repos_path: Path, year: int = None) -> Dict:
    """获取所有仓库的热力图数据"""
    if year is None:
        year = datetime.datetime.now(datetime.timezone.utc).year
    
    # 初始化提交数据字典
    commit_data = {}
    total_commits = 0
    
    # 遍历所有仓库
    try:
        for repo_dir in repos_path.iterdir():
            if repo_dir.is_dir() and repo_dir.name.endswith('.git'):
                try:
                    generator = HeatmapGenerator(repo_dir)
                    repo_commit_data = generator.get_commit_data(year)
                    
                    # 合并提交数据
                    for date_str, count in repo_commit_data.items():
                        commit_data[date_str] = commit_data.get(date_str, 0) + count
                    
                    # 累加总提交数（只统计指定年份的）
                    for date_str, count in repo_commit_data.items():
                        if date_str.startswith(str(year)):
                            total_commits += count
                except Exception as e:
                    logger.debug(f"处理仓库 {repo_dir.name} 失败: {e}")
    except Exception as e:
        logger.error(f"获取所有仓库热力图数据失败: {e}")
    
    # 计算日期范围：指定年份的1月1日到12月31日
    start_date = datetime.datetime(year, 1, 1, tzinfo=datetime.timezone.utc)
    end_date = datetime.datetime(year, 12, 31, tzinfo=datetime.timezone.utc)
    
    # 调整开始日期到第一个周日
    # 周日是6，周一到周六是0-5
    while start_date.weekday() != 6:  # 6是周日
        start_date -= datetime.timedelta(days=1)
    
    # 调整结束日期到12月31日所在周的下一个周六，确保完整显示最后一周
    while end_date.weekday() != 5:  # 5是周六
        end_date += datetime.timedelta(days=1)
    
    # 生成日期网格
    weeks = []
    current_date = start_date
    
    while current_date <= end_date:
        week = []
        for _ in range(7):
            if current_date <= end_date:
                date_str = current_date.strftime("%Y-%m-%d")
                count = commit_data.get(date_str, 0)
                week.append({
                    "date": date_str,
                    "count": count,
                    "color": HeatmapGenerator._get_color_static(count)
                })
            else:
                    # 填充空数据
                    week.append({
                        "date": "",
                        "count": 0,
                        "color": "--heatmap-lightest"
                    })
            current_date += datetime.timedelta(days=1)
        weeks.append(week)
    
    return {
        "year": year,
        "weeks": weeks,
        "total_commits": total_commits,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d")
    }
