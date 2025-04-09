from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
import cv2
import numpy as np
from pathlib import Path

app = FastAPI()


def cv2_imread(path: str, flags=cv2.IMREAD_COLOR):
    """读取图片，支持中文路径"""
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), flags)


@app.get("/image")
async def get_image(path: str):
    """返回指定路径的图片

    Args:
        path: 图片的文件路径

    Returns:
        图片数据
    """
    try:
        # 检查文件是否存在
        if not Path(path).exists():
            raise HTTPException(status_code=404, detail="Image not found")

        # 读取图片
        img = cv2_imread(path)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image format")

        # 编码为PNG并返回
        _, img_encoded = cv2.imencode('.png', img)
        return Response(content=img_encoded.tobytes(), media_type="image/png")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=6532)