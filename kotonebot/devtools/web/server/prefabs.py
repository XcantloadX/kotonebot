from kotonebot.devtools.web.server.rpc import RPCManager
from kotonebot.devtools.project.project import Project
from kotonebot.devtools.project.scanner import scan_prefabs

_prefabs_cache = None


def init(rpc: RPCManager, project: Project):
    @rpc.on("request_prefabs")
    async def request_prefabs():
        global _prefabs_cache
        if _prefabs_cache is None:
            editor = project.conf.editor
            if not editor or not editor.prefabs_module:
                return {}
            _prefabs_cache = scan_prefabs(editor.prefabs_module)
        return _prefabs_cache
