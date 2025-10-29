from fastapi import FastAPI
import uvicorn
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from config.settings import get_settings
from datetime import datetime
from pathlib import Path
from api.websocket.mail import router as mail_router
from api.imap.email import router as imap_router
from api.imap.email_search_api import router as search_router
from api.rei.rei_api import router as rei_router
from api.user.login_api import router as login_router
from api.user.register_api import router as register_router
from api.user.verification_api import router as verification_router
from contextlib import asynccontextmanager
import asyncio

# 获取配置
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    from services.monitor.monitor_service import MonitorService
    from services.rei.task_manager import get_task_manager
    
    # 启动任务管理器
    print("🔧 启动任务管理器...")
    task_manager = get_task_manager()
    await task_manager.start()
    
    # 在后台启动监控服务
    print("🌐 启动邮件监控服务...")
    monitor_task = asyncio.create_task(MonitorService.start())
    
    yield  # 应用运行中
    
    # 关闭时执行
    print("⏹️ 停止邮件监控服务...")
    await MonitorService.stop()
    
    print("⏹️ 停止任务管理器...")
    await task_manager.stop()
    
    # 等待监控任务结束（最多等待5秒）
    try:
        await asyncio.wait_for(monitor_task, timeout=5.0)
    except asyncio.TimeoutError:
        monitor_task.cancel()
        print("⏹️ 监控任务已强制取消")
    except asyncio.CancelledError:
        print("⏹️ 监控任务已取消")


# 创建FastAPI应用
app = FastAPI(
    title="FastAPI Mail Application",
    version="1.0.0",
    description="FastAPI邮件服务应用",
    lifespan=lifespan
)

# 配置CORS - 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://192.168.1.4:5500",
        "http://localhost:3000",
        "http://192.168.1.4:3000",
        ],  # 允许的前端地址
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
)

# 注册路由
# 用户相关路由
app.include_router(login_router)
app.include_router(register_router)
app.include_router(verification_router)
# 邮件相关路由
app.include_router(mail_router)
app.include_router(imap_router)
app.include_router(search_router)
# REI相关路由
app.include_router(rei_router)

@app.get("/", response_class=HTMLResponse)
def read_root():
    """根路径 - 欢迎页面"""
    template_path = Path(__file__).parent / "templates" / "welcome.html"
    html_content = template_path.read_text(encoding="utf-8")
    
    # 替换模板变量
    html_content = html_content.replace("{{VERSION}}", "1.0.0")
    html_content = html_content.replace("{{ENVIRONMENT}}", settings.app_env)
    html_content = html_content.replace("{{PORT}}", str(settings.app_port))
    
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    # 打印启动信息
    print("\n" + "="*60)
    print(f"🚀 FastAPI 服务启动成功！")
    print(f"📅 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 访问地址: http://localhost:{settings.app_port}")
    print(f"📚 API文档: http://localhost:{settings.app_port}/docs")
    print(f"🌐 WebSocket: ws://localhost:{settings.app_port}")
    print("="*60 + "\n")
    
    uvicorn.run(
        app,
        host=settings.app_host,
        port=settings.app_port,
        log_level=settings.log_level
    )
