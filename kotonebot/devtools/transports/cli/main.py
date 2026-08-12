"""CLI 入口：启动传输层组合。"""

import sys
import argparse

from kotonebot.devtools.services.context import DevtoolsContext
from kotonebot.devtools.transports.http.app import (
    start_http,
    start_http_background,
    stop_http_background,
)


def main():
    """KotoneBot CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="kbot",
        description="KotoneBot command-line interface"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    devtools_parser = subparsers.add_parser(
        "devtools",
        help="Start the KotoneBot DevTools web server"
    )
    devtools_parser.add_argument(
        "--port", type=int, default=1178, help="Port to listen on (default: 1178)"
    )
    devtools_parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="Host to listen on (default: 127.0.0.1)"
    )
    devtools_parser.add_argument(
        "--no-browser", action="store_true", help="Do not automatically open browser"
    )
    devtools_parser.add_argument(
        "--workspace", type=str, default=None,
        help="Workspace directory containing pyproject.toml (default: current working directory)",
    )

    host_parser = subparsers.add_parser(
        "devtools-host",
        help="Start single-process host with LSP(stdio) and DevTools HTTP server",
    )
    host_parser.add_argument(
        "--workspace", type=str, default=None,
        help="Workspace directory containing pyproject.toml (default: current working directory)",
    )
    host_parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="HTTP host to bind (default: 127.0.0.1)",
    )
    host_parser.add_argument(
        "--port", type=int, default=1178, help="HTTP port to bind (default: 1178)",
    )
    host_parser.add_argument(
        "--stdio", action="store_true", help="Use stdio transport for LSP (default behavior).",
    )

    args = parser.parse_args()

    ctx = DevtoolsContext.from_workspace(args.workspace)

    if args.command == "devtools":
        start_http(ctx, host=args.host, port=args.port, open_browser=not args.no_browser)
    elif args.command == "devtools-host":
        # LSP 栈（pygls/lsprotocol）仅在 devtools-host 模式下需要，
        # 放在分支内懒加载，避免拖慢纯 HTTP 的 devtools 冷启动
        from kotonebot.devtools.transports.lsp.server import run_lsp
        handle = start_http_background(ctx, host=args.host, port=args.port)
        try:
            run_lsp(ctx)
        finally:
            stop_http_background(handle)
    else:
        parser.print_help()
        sys.exit(0)
