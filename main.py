from fastapi import FastAPI
import uvicorn
from fastapi.responses import HTMLResponse
from config.settings import get_settings
from datetime import datetime
from pathlib import Path

# 获取配置
settings = get_settings()

# 创建FastAPI应用
app = FastAPI(
    title="FastAPI Mail Application",
    version="1.0.0",
    description="FastAPI邮件服务应用"
)

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
    print("="*60 + "\n")
    
    uvicorn.run(
        app,
        host=settings.app_host,
        port=settings.app_port,
        log_level=settings.log_level
    )
