#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 Hao Wu <hao.wu@ortzikantu.com>
# SPDX-License-Identifier: GPL-3.0-only

"""
Git仓库操作模块

本模块提供了Git仓库相关的操作功能，包括仓库列表获取、
分支管理、标签管理等功能。

主要功能：
    - 获取所有仓库列表
    - 获取仓库的分支信息
    - 获取仓库的默认分支
    - 获取仓库的标签列表
    - 获取标签的详细信息
    - 生成快照下载URL

使用示例：
    >>> repos = get_all_repos(git_ops)
    >>> branches = get_branches(git_ops)
    >>> tags = get_tags(git_ops)
"""

import pygit2
import logging
from datetime import datetime, timezone

from .models import RepoInfo

logger = logging.getLogger("osprebit")


def get_all_repos(self):
    """
    获取所有仓库列表
    
    该方法会扫描配置的仓库目录，返回所有Git仓库的详细信息，
    包括仓库名称、路径、默认分支、描述、所有者和最后一次提交信息。
    
    Args:
        self: GitOperations对象
        
    Returns:
        list[dict]: 仓库信息列表，每个元素包含以下键：
            - name (str): 仓库名称
            - path (str): 仓库路径
            - default_branch (str): 默认分支名称
            - description (str): 仓库描述
            - owner (str): 仓库所有者
            - last_commit (dict|None): 最后一次提交信息，包含time、author、message
            
    Examples:
        >>> repos = get_all_repos(git_ops)
        >>> for repo in repos:
        ...     print(f"{repo['name']}: {repo['description']}")
    """
    repos = []
    try:
        for item in self.repo_path.iterdir():
            if item.is_dir():
                if (item / ".git").is_dir() or item.name.endswith(".git"):
                    try:
                        repo = pygit2.Repository(str(item))
                        default_branch = "main"
                        try:
                            head_branch_found = False
                            try:
                                head_ref = repo.head
                                if head_ref and head_ref.name:
                                    if head_ref.name.startswith('refs/heads/'):
                                        branch_name = head_ref.name.split('refs/heads/')[1]
                                        if branch_name in repo.branches.local:
                                            default_branch = branch_name
                                            head_branch_found = True
                            except Exception as e:
                                logger.debug(f"无法获取HEAD引用或HEAD指向的分支不存在: {e}")
                            
                            if not head_branch_found:
                                try:
                                    local_branches = list(repo.branches.local)
                                    if local_branches:
                                        default_branch = local_branches[0]
                                except Exception as e:
                                    logger.debug(f"无法获取本地分支列表: {e}")
                        except Exception as e:
                            logger.debug(f"获取默认分支失败: {e}")
                        
                        description = ""
                        owner = ""
                        config_path = item / "config"
                        if not config_path.exists() and not item.name.endswith(".git"):
                            config_path = item / ".git" / "config"
                        
                        if config_path.exists():
                            try:
                                with open(config_path, "r", encoding="utf-8") as f:
                                    in_repo_section = False
                                    for line in f:
                                        line = line.strip()
                                        if line.startswith("[repo]"):
                                            in_repo_section = True
                                        elif line.startswith("[") and not line.startswith("[repo]"):
                                            in_repo_section = False
                                        elif in_repo_section:
                                            if line.startswith("description = "):
                                                description = line[len("description = "):].strip().strip('"')
                                            elif line.startswith("owner = "):
                                                owner = line[len("owner = "):].strip().strip('"')
                            except:
                                pass
                        
                        if not description:
                            desc_file = item / "description"
                            if not desc_file.exists() and not item.name.endswith(".git"):
                                desc_file = item / ".git" / "description"
                            if desc_file.exists():
                                try:
                                    with open(desc_file, "r", encoding="utf-8") as f:
                                        description = f.read().strip()
                                except:
                                    pass
                        
                        last_commit = None
                        try:
                            if repo.head:
                                commit = repo[repo.head.target]
                                commit_time = datetime.fromtimestamp(commit.commit_time, timezone.utc)
                                last_commit = {
                                    "time": commit_time,
                                    "author": commit.author.name,
                                    "message": commit.message.strip()
                                }
                        except:
                            pass
                        
                        repo_info = RepoInfo(
                            name=item.name.replace(".git", ""),
                            path=str(item),
                            default_branch=default_branch,
                            description=description,
                            owner=owner
                        )
                        repo_dict = repo_info.to_dict()
                        repo_dict["last_commit"] = last_commit
                        
                        repos.append(repo_dict)
                    except Exception as e:
                        logger.error(f"读取仓库 {item.name} 失败: {e}")
    except Exception as e:
        logger.error(f"获取仓库列表失败: {e}")
    return repos


def get_branches(self):
    """
    获取仓库的所有分支
    
    该方法返回仓库中所有本地分支的列表，包括分支名称和
    最后一次提交的时间。
    
    Args:
        self: GitOperations对象
        
    Returns:
        list[dict]: 分支信息列表，每个元素包含以下键：
            - name (str): 分支名称
            - commit_time (datetime|None): 最后一次提交时间，如果获取失败则为None
            
    Examples:
        >>> branches = get_branches(git_ops)
        >>> for branch in branches:
        ...     print(f"{branch['name']}: {branch['commit_time']}")
    """
    try:
        repo = pygit2.Repository(str(self.repo_path))
        branches = []
        for branch in repo.branches.local:
            try:
                branch_obj = repo.branches[branch]
                commit = branch_obj.peel()
                if commit:
                    commit_time = datetime.fromtimestamp(commit.commit_time, timezone.utc)
                    branches.append({
                        "name": branch,
                        "commit_time": commit_time
                    })
            except:
                branches.append({
                    "name": branch,
                    "commit_time": None
                })
        return branches
    except Exception as e:
        logger.error(f"获取分支失败: {e}")
        return []


def get_default_branch(self):
    """
    获取仓库的默认分支
    
    该方法会尝试获取HEAD引用指向的分支，如果失败则返回
    第一个本地分支，最后返回"main"作为默认值。
    
    Args:
        self: GitOperations对象
        
    Returns:
        str: 默认分支名称
        
    Examples:
        >>> default_branch = get_default_branch(git_ops)
        >>> print(f"默认分支: {default_branch}")
    """
    try:
        repo = pygit2.Repository(str(self.repo_path))
        
        try:
            head_ref = repo.head
            if head_ref and head_ref.name:
                if head_ref.name.startswith('refs/heads/'):
                    branch_name = head_ref.name.split('refs/heads/')[1]
                    if branch_name in repo.branches.local:
                        return branch_name
        except Exception as e:
            logger.debug(f"无法获取HEAD引用或HEAD指向的分支不存在: {e}")
        
        try:
            local_branches = list(repo.branches.local)
            if local_branches:
                return local_branches[0]
        except Exception as e:
            logger.debug(f"无法获取本地分支列表: {e}")
        
        return "main"
    except Exception as e:
        logger.error(f"获取默认分支失败: {e}")
        return "main"


def get_tags(self):
    """
    获取仓库的所有标签
    
    该方法返回仓库中所有标签的列表。
    
    Args:
        self: GitOperations对象
        
    Returns:
        list[str]: 标签名称列表
        
    Examples:
        >>> tags = get_tags(git_ops)
        >>> for tag in tags:
        ...     print(f"标签: {tag}")
    """
    try:
        repo = pygit2.Repository(str(self.repo_path))
        tags = []
        for ref_name in repo.references:
            if ref_name.startswith('refs/tags/'):
                tag_name = ref_name.split('refs/tags/')[1]
                tags.append(tag_name)
        return tags
    except Exception as e:
        logger.error(f"获取标签失败: {e}")
        return []


def get_tag_info(self, tag_name):
    """
    获取指定标签的详细信息
    
    该方法返回指定标签的详细信息，包括标签指向的提交ID、
    提交时间、作者和提交信息。支持带注释的标签和轻量级标签。
    
    Args:
        self: GitOperations对象
        tag_name (str): 标签名称
        
    Returns:
        dict|None: 标签信息字典，包含以下键：
            - name (str): 标签名称
            - message (str|None): 标签消息（仅带注释的标签）
            - tagger (str|None): 标签创建者名称（仅带注释的标签）
            - tagger_email (str|None): 标签创建者邮箱（仅带注释的标签）
            - tag_time (datetime|None): 标签创建时间（仅带注释的标签）
            - object_id (str): 标签指向的对象ID
            如果标签不存在则返回None
            
    Examples:
        >>> tag_info = get_tag_info(git_ops, "v1.0.0")
        >>> if tag_info:
        ...     print(f"标签 {tag_info['name']} 由 {tag_info['tagger']} 创建")
    """
    try:
        repo = pygit2.Repository(str(self.repo_path))
        try:
            tag_obj = repo.revparse_single(f"refs/tags/{tag_name}")
        except Exception:
            return None
        
        if tag_obj.type == 4:
            return {
                "name": tag_name,
                "message": tag_obj.message.strip(),
                "tagger": tag_obj.tagger.name,
                "tagger_email": tag_obj.tagger.email,
                "tag_time": datetime.fromtimestamp(tag_obj.tagger.time, timezone.utc),
                "object_id": str(tag_obj.target)
            }
        else:
            return {
                "name": tag_name,
                "message": None,
                "tagger": None,
                "tagger_email": None,
                "tag_time": None,
                "object_id": str(tag_obj.id)
            }
    except Exception as e:
        logger.error(f"获取标签信息失败: {e}")
        return None


def get_snapshot_url(self, tag_name, format='tar.gz'):
    """
    获取指定标签的快照下载URL
    
    该方法生成指定标签的快照下载URL，支持tar.gz格式。
    
    Args:
        self: GitOperations对象
        tag_name (str): 标签名称
        format (str, optional): 快照格式，默认为'tar.gz'
        
    Returns:
        str|None: 快照下载URL，如果获取失败则返回None
        
    Examples:
        >>> url = get_snapshot_url(git_ops, "v1.0.0")
        >>> print(f"下载URL: {url}")
    """
    try:
        repo_name = self.repo_path.name
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        return f"/{repo_name}/snapshot/{tag_name}/{format}"
    except Exception as e:
        logger.error(f"获取snapshot链接失败: {e}")
        return None
