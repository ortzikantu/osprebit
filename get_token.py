#!/usr/bin/env python3
"""获取认证令牌的命令行工具"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from osprebit.auth import get_authenticator


def main():
    """主函数"""
    print("=" * 50)
    print("Git 仓库认证令牌获取工具")
    print("=" * 50)
    
    # 获取认证管理器
    auth_manager = get_authenticator()
    
    # 获取最新令牌
    token = auth_manager.get_latest_token()
    
    # 获取令牌信息
    token_info = auth_manager.get_token_info(token)
    
    print(f"\n✅ 令牌已生成")
    print(f"\n令牌: {token}")
    print(f"\n令牌信息:")
    print(f"  用户名: {token_info['username']}")
    print(f"  创建时间: {token_info['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  过期时间: {token_info['expires_at'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  有效期: 3 天")
    
    print("\n" + "=" * 50)
    print("使用方法:")
    print("=" * 50)
    
    # 获取配置信息
    from osprebit.config import CONFIG
    base_url = CONFIG.get("base_url", "http://localhost")
    port = CONFIG.get("port", "6789")
    
    # 构建完整的URL
    full_url = f"{base_url}:{port}"
    
    print(f"\n1. 使用令牌进行 Git Push:")
    print(f"   git push https://{token}@{full_url}/<仓库名>")
    
    print(f"\n2. 设置 Git 凭据:")
    print(f"   git remote set-url origin https://{token}@{full_url}/<仓库名>")
    
    print(f"\n3. 临时使用令牌:")
    print(f"   git push https://{token}@{full_url}/<仓库名>")
    
    print("\n" + "=" * 50)
    print("注意事项:")
    print("=" * 50)
    print("• 令牌有效期为 3 天")
    print("• 请妥善保管令牌，不要泄露给他人")
    print("• 令牌过期后需要重新获取")
    print("• 系统仅支持令牌认证，不再支持密码认证")
    print("• 如果遇到问题，请联系管理员")
    print("=" * 50)


if __name__ == "__main__":
    main()
