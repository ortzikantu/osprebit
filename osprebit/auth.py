#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 Hao Wu <hao.wu@ortzikantu.com>
# SPDX-License-Identifier: GPL-3.0-only

"""
认证管理模块

本模块提供了Git推送操作的认证功能，包括令牌生成、验证、
撤销和管理等功能。使用SHA-256哈希存储令牌，确保安全性。

主要功能：
    - 生成安全的认证令牌
    - 验证令牌有效性
    - 撤销令牌
    - 清理过期令牌
    - 令牌持久化存储

使用示例：
    >>> from osprebit.auth import auth_manager
    >>> token = auth_manager.generate_token("myuser")
    >>> is_valid = auth_manager.validate_token(token)
    >>> auth_manager.revoke_token(token)
"""

import secrets
import time
import logging
import hashlib
import json
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger("osprebit")

class Authenticator:
    """
    认证管理器
    
    该类负责令牌的生成、验证和管理，支持令牌的持久化存储
    和过期管理。令牌使用SHA-256哈希存储，确保安全性。
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        初始化认证管理器
        
        该方法初始化认证管理器，创建存储目录并加载已有令牌。
        
        Args:
            storage_dir (Optional[Path]): 令牌存储目录，默认为~/.config/osprebit/tokens
        """
        self.active_tokens: Dict[str, Dict] = {}
        self.token_expiry = 259200
        
        if storage_dir is None:
            storage_dir = Path.home() / ".config" / "osprebit" / "tokens"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.tokens_file = self.storage_dir / "tokens.json"
        
        self._load_tokens()
    
    def _hash_token(self, token: str) -> str:
        """
        对令牌进行哈希处理
        
        该方法使用SHA-256算法对令牌进行哈希处理，
        用于安全存储和验证。
        
        Args:
            token (str): 原始令牌
            
        Returns:
            str: 哈希后的令牌
        """
        return hashlib.sha256(token.encode()).hexdigest()
    
    def _save_tokens(self):
        """
        保存令牌到文件
        
        该方法将当前活跃的令牌信息保存到JSON文件中。
        只保存元数据，不保存原始令牌。
        """
        try:
            tokens_data = {}
            for token_hash, info in self.active_tokens.items():
                tokens_data[token_hash] = {
                    "username": info["username"],
                    "created_at": info["created_at"].isoformat(),
                    "expires_at": info["expires_at"].isoformat()
                }
            
            with open(self.tokens_file, "w") as f:
                json.dump(tokens_data, f, indent=2)
            
            logger.info(f"Tokens saved to {self.tokens_file}")
        except Exception as e:
            logger.error(f"Failed to save tokens: {e}")
    
    def _load_tokens(self):
        """
        从文件加载令牌
        
        该方法从JSON文件中加载令牌信息，过滤掉已过期的令牌。
        只加载元数据，原始令牌需要用户提供。
        """
        try:
            if not self.tokens_file.exists():
                logger.info("No existing tokens file found")
                return
            
            with open(self.tokens_file, "r") as f:
                tokens_data = json.load(f)
            
            self.active_tokens.clear()
            
            for token_hash, info in tokens_data.items():
                expires_at = datetime.fromisoformat(info["expires_at"])
                if datetime.now() > expires_at:
                    continue
                
                self.active_tokens[token_hash] = {
                    "username": info["username"],
                    "created_at": datetime.fromisoformat(info["created_at"]),
                    "expires_at": expires_at
                }
            
            logger.info(f"Loaded {len(self.active_tokens)} tokens from {self.tokens_file}")
        except Exception as e:
            logger.error(f"Failed to load tokens: {e}")
            self.active_tokens.clear()
    
    def generate_token(self, username: str = "git") -> str:
        """
        生成新的认证令牌
        
        该方法生成一个安全的URL编码令牌，计算其哈希值并存储。
        令牌默认有效期为3天。
        
        Args:
            username (str): 用户名，默认为"git"
            
        Returns:
            str: 生成的令牌字符串
        """
        token = secrets.token_urlsafe(32)
        
        token_hash = self._hash_token(token)
        
        expiry_time = datetime.now() + timedelta(seconds=self.token_expiry)
        
        self.active_tokens[token_hash] = {
            "username": username,
            "created_at": datetime.now(),
            "expires_at": expiry_time
        }
        
        self._save_tokens()
        
        logger.info(f"Generated new token for user {username}")
        return token
    
    def validate_token(self, token: str) -> bool:
        """
        验证令牌是否有效
        
        该方法验证令牌是否存在且未过期。
        
        Args:
            token (str): 要验证的令牌
            
        Returns:
            bool: 如果令牌有效返回True，否则返回False
        """
        token_hash = self._hash_token(token)
        
        if token_hash not in self.active_tokens:
            logger.warning(f"Token not found")
            return False
        
        token_info = self.active_tokens[token_hash]
        if datetime.now() > token_info["expires_at"]:
            del self.active_tokens[token_hash]
            self._save_tokens()
            logger.warning(f"Token expired")
            return False
        
        logger.info(f"Token validated successfully")
        return True
    
    def get_token_info(self, token: str) -> Optional[Dict]:
        """
        获取令牌信息
        
        该方法返回令牌的元数据信息。
        
        Args:
            token (str): 令牌
            
        Returns:
            Optional[Dict]: 令牌信息字典，如果令牌不存在或过期返回None
        """
        token_hash = self._hash_token(token)
        
        if not self.validate_token(token):
            return None
        
        return self.active_tokens.get(token_hash)
    
    def revoke_token(self, token: str) -> bool:
        """
        撤销令牌
        
        该方法从活跃令牌列表中移除指定令牌。
        
        Args:
            token (str): 要撤销的令牌
            
        Returns:
            bool: 如果令牌成功撤销返回True，否则返回False
        """
        token_hash = self._hash_token(token)
        
        if token_hash in self.active_tokens:
            del self.active_tokens[token_hash]
            self._save_tokens()
            logger.info(f"Token revoked")
            return True
        
        logger.warning(f"Attempted to revoke non-existent token")
        return False
    
    def clear_expired_tokens(self) -> int:
        """
        清理过期令牌
        
        该方法移除所有已过期的令牌。
        
        Returns:
            int: 清理的过期令牌数量
        """
        expired_tokens = []
        current_time = datetime.now()
        
        for token_hash, info in self.active_tokens.items():
            if current_time > info["expires_at"]:
                expired_tokens.append(token_hash)
        
        for token_hash in expired_tokens:
            del self.active_tokens[token_hash]
        
        if expired_tokens:
            self._save_tokens()
            logger.info(f"Cleared {len(expired_tokens)} expired tokens")
        
        return len(expired_tokens)
    
    def get_latest_token(self, username: str = "git") -> str:
        """
        获取最新的令牌
        
        该方法清理过期令牌并生成新令牌。
        由于令牌使用哈希存储，无法从哈希反推出原始令牌，
        所以每次调用都会生成新令牌。
        
        Args:
            username (str): 用户名，默认为"git"
            
        Returns:
            str: 新生成的有效令牌
        """
        self.clear_expired_tokens()
        
        return self.generate_token(username)

auth_manager = Authenticator()

def get_authenticator() -> Authenticator:
    """
    获取认证管理器实例
    
    该方法返回全局认证管理器实例。
    
    Returns:
        Authenticator: 认证管理器实例
    """
    return auth_manager

def authenticate_with_token(auth_header: str) -> bool:
    """
    使用令牌进行认证
    
    该方法解析认证头并验证令牌。支持Token和Basic两种认证方式。
    
    Args:
        auth_header (str): 认证头信息
        
    Returns:
        bool: 如果认证成功返回True，否则返回False
    """
    try:
        auth_type, auth_value = auth_header.split(" ", 1)
        auth_type_lower = auth_type.lower()
        
        if auth_type_lower == "token":
            return auth_manager.validate_token(auth_value)
        
        elif auth_type_lower == "basic":
            import base64
            decoded = base64.b64decode(auth_value).decode('utf-8')
            if ':' in decoded:
                _, password = decoded.split(':', 1)
                return auth_manager.validate_token(password)
            return False
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
    
    return False
