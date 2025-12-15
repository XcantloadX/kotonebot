import logging
from typing import Any, Callable, Coroutine, Dict, Optional

from socketio import AsyncServer

logger = logging.getLogger(__name__)


class RPCManager:
    def __init__(self, sio: AsyncServer):
        self.sio = sio
        self.methods: Dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}
        self.sio.on("rpc", self.on_rpc)

    def on(self, name: Optional[str] = None) -> Callable:
        def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
            method_name = name or func.__name__
            if method_name in self.methods:
                raise ValueError(f"Method {method_name} already registered")
            self.methods[method_name] = func
            logger.info(f"RPC method '{method_name}' registered")
            return func

        return decorator

    async def on_rpc(self, sid: str, data: Dict[str, Any]):
        method_name = data.get("method")
        request_id = data.get("id")
        params = data.get("params", {})

        if not method_name or not request_id:
            logger.warning(f"Invalid RPC call from {sid}: {data}")
            return

        logger.debug(f"RPC call from {sid}: {method_name}({params})")

        if method_name not in self.methods:
            logger.error(f"RPC method '{method_name}' not found")
            await self.sio.emit(
                "rpc_error",
                {"id": request_id, "error": f"Method '{method_name}' not found"},
                to=sid,
            )
            return

        try:
            result = await self.methods[method_name](**params)
            await self.sio.emit("rpc_response", {"id": request_id, "result": result}, to=sid)
        except Exception as e:
            logger.exception(f"Error executing RPC method '{method_name}'")
            await self.sio.emit(
                "rpc_error",
                {"id": request_id, "error": str(e)},
                to=sid,
            )
