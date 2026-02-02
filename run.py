import uvicorn
from osprebit.config import CONFIG

if __name__ == "__main__":
    print("🚀 启动 Osprebit Git Server...")
    print(f"🔌 服务端口：{CONFIG['port']}")
    print(f"📂 仓库路径：{CONFIG['repo_path']}")
    
    uvicorn.run(
        "osprebit.app:app",
        host="0.0.0.0",
        port=CONFIG["port"],
        reload=True,
    )
