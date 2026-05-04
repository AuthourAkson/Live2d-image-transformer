"""
Live2D Image Transformer — Web UI
==================================
基于 FastAPI 的 Web 界面，提供图片上传和模型生成功能。

启动:
    python webui/app.py
    或:
    uvicorn webui.app:app --host 0.0.0.0 --port 8000 --reload

访问: http://localhost:8000
"""

import io
import logging
import os
import sys
import uuid
import zipfile
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image

from core.preprocessing import remove_background_pil
from core.segmentation import separate_layers
from core.rigging import auto_rig
from core.export import export_live2d

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webui")

app = FastAPI(
    title="Live2D Image Transformer",
    description="将图片转换为 Live2D 可动模型",
    version="0.1.0",
)

# 静态文件与模板
base_dir = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(base_dir / "static")), name="static")
templates = Jinja2Templates(directory=str(base_dir / "templates"))

# 输出根目录
OUTPUT_ROOT = Path(os.environ.get("L2D_OUTPUT_DIR", base_dir.parent / "output"))
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def run_pipeline_from_image(
    image: Image.Image,
    job_id: str,
    atlas_size: int = 2048,
):
    """从 PIL Image 执行完整管线。"""
    job_dir = OUTPUT_ROOT / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: 背景移除
    logger.info(f"[{job_id}] 正在移除背景...")
    clean = remove_background_pil(image)
    clean_path = job_dir / "input_clean.png"
    clean.save(str(clean_path))

    # Step 2: 图层分离
    logger.info(f"[{job_id}] 正在分离图层...")
    layers, original_size = separate_layers(clean)

    # Step 3: 骨骼绑定
    logger.info(f"[{job_id}] 正在绑定骨骼...")
    rig = auto_rig(layers)

    # Step 4: 导出
    logger.info(f"[{job_id}] 正在导出 Live2D...")
    l2d_output = job_dir / "live2d_model"
    export_live2d(
        layers=layers,
        rig_result=rig,
        output_dir=str(l2d_output),
        model_name="model",
        atlas_size=atlas_size,
    )

    # 打包 zip
    zip_path = job_dir / "live2d_model.zip"
    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        for f in l2d_output.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(l2d_output))

    return {
        "job_id": job_id,
        "layers": [l.to_dict() for l in layers],
        "num_layers": len(layers),
        "num_params": rig.metadata["total_parameters"],
        "zip_path": str(zip_path),
    }


# === 路由 ===

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/upload")
async def upload_image(
    file: UploadFile = File(...),
    atlas_size: int = Form(2048),
):
    """上传图片并执行管线"""
    if not file.content_type or not file.content_type.startswith("image/"):
        return JSONResponse({"error": "请上传图片文件"}, status_code=400)

    job_id = uuid.uuid4().hex[:12]

    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")

        result = run_pipeline_from_image(
            image=image,
            job_id=job_id,
            atlas_size=atlas_size,
        )

        return JSONResponse({
            "success": True,
            "job_id": result["job_id"],
            "num_layers": result["num_layers"],
            "num_params": result["num_params"],
            "layers": result["layers"],
            "download_url": f"/api/download/{job_id}",
        })

    except Exception as e:
        logger.exception(f"处理失败 [{job_id}]: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/download/{job_id}")
async def download_model(job_id: str):
    """下载模型的 ZIP 包"""
    zip_path = OUTPUT_ROOT / job_id / "live2d_model.zip"
    if not zip_path.exists():
        return JSONResponse({"error": "模型不存在或已被清理"}, status_code=404)

    return FileResponse(
        path=str(zip_path),
        filename=f"live2d_model_{job_id}.zip",
        media_type="application/zip",
    )


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


# === 启动入口 ===
if __name__ == "__main__":
    import uvicorn
    logger.info("启动 WebUI: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
