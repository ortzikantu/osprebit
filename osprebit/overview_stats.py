#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 Hao Wu <hao.wu@ortzikantu.com>
# SPDX-License-Identifier: GPL-3.0-only

"""
Overview统计模块
提供整个服务和仓库的统计功能

主要功能：
    - OverviewStats: 服务和仓库统计类
    - get_service_stats: 获取服务级别统计信息
    - get_repo_stats: 获取单个仓库的统计信息
    - get_repo_rankings: 获取仓库排名

使用示例：
    >>> from osprebit.overview_stats import OverviewStats
    >>> stats = OverviewStats()
    >>> service_stats = stats.get_service_stats()
"""

import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import pygit2

from .config import CONFIG

logger = logging.getLogger("osprebit")


class OverviewStats:
    """Overview统计类"""
    
    def __init__(self):
        self.repos_path = Path(CONFIG["repo_path"])
    
    def get_service_stats(self) -> Dict[str, Any]:
        """获取服务级别统计信息
        
        Returns:
            包含服务统计信息的字典
        """
        try:
            stats = {
                "total_repos": 0,
                "total_commits": 0,
                "total_files": 0,
                "total_size": 0,
                "total_authors": set(),
                "active_repos": 0,
                "largest_repo": None,
                "most_active_repo": None,
                "recent_activity": []
            }
            
            repo_stats = []
            
            # 遍历所有仓库
            for repo_dir in self.repos_path.iterdir():
                if not repo_dir.is_dir():
                    continue
                
                # 检查是否是git仓库
                is_git_repo = (repo_dir / ".git").is_dir() or repo_dir.name.endswith('.git')
                if not is_git_repo:
                    continue
                
                stats["total_repos"] += 1
                
                try:
                    repo = pygit2.Repository(str(repo_dir))
                    repo_name = repo_dir.name
                    if repo_name.endswith('.git'):
                        repo_name = repo_name[:-4]
                    
                    # 获取仓库统计信息
                    repo_stat = self._get_repo_stats(repo, repo_name, repo_dir)
                    repo_stats.append(repo_stat)
                    
                    # 累加统计
                    stats["total_commits"] += repo_stat["total_commits"]
                    stats["total_files"] += repo_stat["total_files"]
                    stats["total_size"] += repo_stat["total_size"]
                    stats["total_authors"].update(repo_stat["authors"])
                    
                    if repo_stat["total_commits"] > 0:
                        stats["active_repos"] += 1
                    
                    # 记录最近活动
                    if repo_stat["latest_commit"]:
                        stats["recent_activity"].append({
                            "repo_name": repo_name,
                            "commit_time": repo_stat["latest_commit"],
                            "commit_message": repo_stat["latest_message"]
                        })
                    
                except Exception as e:
                    logger.error(f"获取仓库 {repo_dir.name} 统计信息失败: {e}")
                    continue
            
            # 转换authors为列表
            stats["total_authors"] = len(stats["total_authors"])
            
            # 找出最大的仓库
            if repo_stats:
                stats["largest_repo"] = max(repo_stats, key=lambda x: x["total_size"])
                stats["most_active_repo"] = max(repo_stats, key=lambda x: x["total_commits"])
            
            # 按时间排序最近活动
            stats["recent_activity"].sort(key=lambda x: x["commit_time"], reverse=True)
            stats["recent_activity"] = stats["recent_activity"][:10]
            
            # 格式化大小
            stats["total_size_formatted"] = self._format_size(stats["total_size"])
            
            return stats
            
        except Exception as e:
            logger.error(f"获取服务统计信息失败: {e}")
            return {}
    
    def _get_repo_stats(self, repo: pygit2.Repository, repo_name: str, repo_dir: Path) -> Dict[str, Any]:
        """获取单个仓库的统计信息
        
        Args:
            repo: pygit2仓库对象
            repo_name: 仓库名称
            repo_dir: 仓库目录路径
            
        Returns:
            包含仓库统计信息的字典
        """
        try:
            stats = {
                "repo_name": repo_name,
                "total_commits": 0,
                "total_files": 0,
                "total_size": 0,
                "authors": set(),
                "latest_commit": None,
                "latest_message": ""
            }
            
            # 计算仓库大小
            stats["total_size"] = self._calculate_repo_size(repo_dir)
            
            # 获取所有提交（统计所有分支的提交）
            try:
                # 遍历所有本地分支
                for branch_name in repo.branches.local:
                    try:
                        branch = repo.branches[branch_name]
                        commit = branch.peel(pygit2.Commit)
                        if commit:
                            # 使用repo.walk遍历该分支的所有提交
                            branch_commit_count = 0
                            for commit in repo.walk(commit.id):
                                branch_commit_count += 1
                                stats["authors"].add(commit.author.name)
                                
                                # 记录最新提交
                                if stats["latest_commit"] is None or datetime.fromtimestamp(commit.commit_time) > stats["latest_commit"]:
                                    stats["latest_commit"] = datetime.fromtimestamp(commit.commit_time)
                                    stats["latest_message"] = commit.message.strip().split('\n')[0]
                            
                            stats["total_commits"] += branch_commit_count
                            logger.debug(f"仓库 {repo_name} 分支 {branch_name} 提交数: {branch_commit_count}")
                    except Exception as e:
                        logger.debug(f"分支 {branch_name} 处理失败: {e}")
                        continue
            except Exception as e:
                logger.error(f"获取仓库 {repo_name} 提交历史失败: {e}")
                import traceback
                logger.debug(traceback.format_exc())
            
            logger.debug(f"仓库 {repo_name} 总提交数: {stats['total_commits']}")
            
            # 计算文件数量（统计所有分支的文件数）
            try:
                if not repo.is_empty:
                    # 遍历所有本地分支
                    all_files = set()
                    for branch_name in repo.branches.local:
                        try:
                            branch = repo.branches[branch_name]
                            commit = branch.peel(pygit2.Commit)
                            if commit and commit.type == 1:  # GIT_OBJ_COMMIT
                                tree = commit.tree
                                branch_files = self._get_all_files_in_tree(tree)
                                all_files.update(branch_files)
                                logger.debug(f"仓库 {repo_name} 分支 {branch_name} 文件数: {len(branch_files)}")
                        except Exception as e:
                            logger.debug(f"分支 {branch_name} 文件统计失败: {e}")
                            continue
                    
                    stats["total_files"] = len(all_files)
                    logger.info(f"仓库 {repo_name} 总文件数: {stats['total_files']}")
                else:
                    logger.warning(f"仓库 {repo_name} 为空仓库")
            except Exception as e:
                logger.error(f"获取仓库 {repo_name} 文件数量失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            # 格式化仓库大小
            stats["total_size_formatted"] = self._format_size(stats["total_size"])
            
            return stats
            
        except Exception as e:
            logger.error(f"获取仓库 {repo_name} 统计信息失败: {e}")
            return {
                "repo_name": repo_name,
                "total_commits": 0,
                "total_files": 0,
                "total_size": 0,
                "authors": set(),
                "latest_commit": None,
                "latest_message": ""
            }
    
    def _count_files_in_tree(self, tree: pygit2.Tree) -> int:
        """递归计算树中的文件数量
        
        Args:
            tree: pygit2树对象
            
        Returns:
            文件数量
        """
        count = 0
        for entry in tree:
            if entry.type == 3:  # GIT_OBJ_BLOB
                count += 1
            elif entry.type == 2:  # GIT_OBJ_TREE
                try:
                    subtree = tree[entry.name]
                    count += self._count_files_in_tree(subtree)
                except Exception as e:
                    logger.debug(f"无法访问子树 {entry.name}: {e}")
        return count
    
    def _get_all_files_in_tree(self, tree: pygit2.Tree, prefix: str = "") -> set:
        """递归获取树中所有文件的路径
        
        Args:
            tree: pygit2树对象
            prefix: 路径前缀
            
        Returns:
            文件路径集合
        """
        files = set()
        for entry in tree:
            path = f"{prefix}/{entry.name}" if prefix else entry.name
            if entry.type == 3:  # GIT_OBJ_BLOB
                files.add(path)
            elif entry.type == 2:  # GIT_OBJ_TREE
                try:
                    subtree = tree[entry.name]
                    files.update(self._get_all_files_in_tree(subtree, path))
                except Exception as e:
                    logger.debug(f"无法访问子树 {entry.name}: {e}")
        return files
    
    def _calculate_repo_size(self, repo_dir: Path) -> int:
        """计算仓库大小
        
        Args:
            repo_dir: 仓库目录路径
            
        Returns:
            仓库大小（字节）
        """
        try:
            total_size = 0
            repo_path_str = str(repo_dir)
            is_bare_repo = repo_dir.name.endswith('.git')
            
            if is_bare_repo:
                # 裸仓库：计算整个目录的大小
                for root, dirs, files in os.walk(repo_path_str):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            total_size += os.path.getsize(file_path)
                        except:
                            pass
            else:
                # 非裸仓库：计算.git目录和工作目录的大小
                git_dir = os.path.join(repo_path_str, ".git")
                if os.path.exists(git_dir):
                    for root, dirs, files in os.walk(git_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                total_size += os.path.getsize(file_path)
                            except:
                                pass
                
                # 计算工作目录大小（排除.git目录）
                for root, dirs, files in os.walk(repo_path_str):
                    if '.git' in dirs:
                        dirs.remove('.git')
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            total_size += os.path.getsize(file_path)
                        except:
                            pass
            
            return total_size
            
        except Exception as e:
            logger.error(f"计算仓库大小失败: {e}")
            return 0
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化大小
        
        Args:
            size_bytes: 大小（字节）
            
        Returns:
            格式化后的大小字符串
        """
        if size_bytes == 0:
            return "0 B"
        elif size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    def get_repo_rankings(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取仓库排名
        
        Returns:
            包含各种排名的字典
        """
        try:
            repo_stats = []
            
            # 遍历所有仓库
            for repo_dir in self.repos_path.iterdir():
                if not repo_dir.is_dir():
                    continue
                
                # 检查是否是git仓库
                is_git_repo = (repo_dir / ".git").is_dir() or repo_dir.name.endswith('.git')
                if not is_git_repo:
                    continue
                
                try:
                    repo = pygit2.Repository(str(repo_dir))
                    repo_name = repo_dir.name
                    if repo_name.endswith('.git'):
                        repo_name = repo_name[:-4]
                    
                    # 获取仓库统计信息
                    repo_stat = self._get_repo_stats(repo, repo_name, repo_dir)
                    repo_stats.append(repo_stat)
                    
                except Exception as e:
                    logger.error(f"获取仓库 {repo_dir.name} 统计信息失败: {e}")
                    continue
            
            # 排序
            rankings = {
                "by_commits": sorted(repo_stats, key=lambda x: x["total_commits"], reverse=True),
                "by_files": sorted(repo_stats, key=lambda x: x["total_files"], reverse=True),
                "by_size": sorted(repo_stats, key=lambda x: x["total_size"], reverse=True),
                "by_authors": sorted(repo_stats, key=lambda x: len(x["authors"]), reverse=True)
            }
            
            return rankings
            
        except Exception as e:
            logger.error(f"获取仓库排名失败: {e}")
            return {"by_commits": [], "by_files": [], "by_size": [], "by_authors": []}