"""FastAPI 依赖注入。"""

from fastapi import Request

from kotonebot.devtools.services.context import DevtoolsContext


def get_context(request: Request) -> DevtoolsContext:
    """从 app.state 获取共享上下文。"""
    return request.app.state.ctx
