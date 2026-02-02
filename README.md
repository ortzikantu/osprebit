# Osprebit

<div align="center">

<img src="https://ortzikantu.com/assets/pics/works-icon/works-osprebit.png" alt="Osprebit" width="120" height="120">

![Osprebit](https://img.shields.io/badge/Osprebit-v0.1.0--dev-pink)
![License](https://img.shields.io/badge/License-GPL--3.0--only-blue)
![Python](https://img.shields.io/badge/Python-3.14+-green)
![Litestar](https://img.shields.io/badge/Litestar-2.19.0+-purple)

**轻量级自托管 Git Web 界面**

</div>

## 简介

Osprebit 是一个轻量级的自托管 Git Web 界面，基于现代 Python 技术栈构建。它提供了一个简洁、高效的 Web 界面来浏览和管理 Git 仓库。

## 功能特性

- 🌳 **仓库浏览** - 浏览仓库文件树和文件内容
- 📝 **提交历史** - 查看完整的提交历史和提交详情
- 🔥 **贡献热力图** - 可视化展示贡献活动
- 📊 **统计信息** - 仓库统计和概览信息
- 🔄 **Git 协议支持** - 完整支持 Git push/pull 操作
- 📦 **快照下载** - 支持下载仓库快照
- 🎨 **现代化界面** - 响应式设计，支持移动端
- ⚡ **高性能** - 基于 ASGI，支持高并发
- 🔧 **易于配置** - 简单的 TOML 配置文件

## 技术栈

- **Web 框架**: Litestar 2.19+
- **模板引擎**: Jinja2 3.1+
- **Git 操作**: pygit2 1.19+
- **ASGI 服务器**: Uvicorn
- **Python 版本**: 3.14+

## 截图

![Osprebit 截图](screenshot/Screenshot.png)

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://codeberg.org/ortzikantu/osprebit.git
cd osprebit

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 配置

创建配置文件 `~/.config/osprebit/config.toml`：

```toml
[osprebit]
site_name = "Osprebit"
port = 6789
repo_path = "/path/to/your/repos"
base_url = "https://your-domain.com"
```

配置文件示例可参考 [config.toml.example](config.toml.example)。

### 运行

```bash
# 开发模式
python -m uvicorn osprebit.app:app --host 0.0.0.0 --port 6789 --reload

# 生产模式
python -m uvicorn osprebit.app:app --host 0.0.0.0 --port 6789 --workers 4
```

访问 `http://localhost:6789` 即可查看界面。

### 创建裸仓库

Osprebit 需要使用 Git 裸仓库（bare repository）。创建裸仓库的步骤：

```bash
# 创建裸仓库目录
mkdir -p /path/to/your/repos/myproject.git
cd /path/to/your/repos/myproject.git

# 初始化为裸仓库
git init --bare

# 设置仓库描述（可选）
echo "我的项目描述" > description
git config --local repo.description "我的项目描述"

# 设置仓库所有者（可选）
git config --local repo.owner "Your Name"
```

## 许可证

本项目采用 [GPL-3.0-only](LICENSE) 许可证。

## 致谢

- [Litestar](https://litestar.dev/) - 现代化的 Python Web 框架
- [pygit2](https://www.pygit2.org/) - Python Git 绑定
- [Jinja2](https://jinja.palletsprojects.com/) - 模板引擎

## 联系方式

- 作者: Hao Wu
- 邮箱: hao.wu@ortzikantu.com
- 项目主页: https://codeberg.org/ortzikantu/osprebit
- 问题反馈: https://codeberg.org/ortzikantu/osprebit/issues

---

<div align="center">

**如果这个项目对你有帮助，请给个 ⭐️**

Made with ❤️ by Ortzikantu

</div>
