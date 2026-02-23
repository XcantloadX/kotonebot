import sys
import argparse

from ..lsp.server import run_lsp_server
from ..web.server.server import start_devtools, start_devtools_background, stop_devtools_background


def main():
    """KotoneBot CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="kbot",
        description="KotoneBot command-line interface"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # devtools subcommand
    devtools_parser = subparsers.add_parser(
        "devtools",
        help="Start the KotoneBot DevTools web server"
    )
    devtools_parser.add_argument(
        "--port",
        type=int,
        default=1178,
        help="Port to listen on (default: 1178)"
    )
    devtools_parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to listen on (default: 127.0.0.1)"
    )
    devtools_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically open browser"
    )
    devtools_parser.add_argument(
        "--workspace",
        type=str,
        default=None,
        help="Workspace directory containing pyproject.toml (default: current working directory)",
    )

    host_parser = subparsers.add_parser(
        "devtools-host",
        help="Start single-process host with LSP(stdio) and DevTools HTTP server",
    )
    host_parser.add_argument(
        "--workspace",
        type=str,
        default=None,
        help="Workspace directory containing pyproject.toml (default: current working directory)",
    )
    host_parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="HTTP host to bind (default: 127.0.0.1)",
    )
    host_parser.add_argument(
        "--port",
        type=int,
        default=1178,
        help="HTTP port to bind (default: 1178)",
    )
    host_parser.add_argument(
        "--stdio",
        action="store_true",
        help="Use stdio transport for LSP (default behavior).",
    )
    
    args = parser.parse_args()
    
    if args.command == "devtools":
        start_devtools(
            host=args.host,
            port=args.port,
            open_browser=not args.no_browser,
            workspace=args.workspace,
        )
    elif args.command == "devtools-host":
        handle = start_devtools_background(host=args.host, port=args.port, workspace=args.workspace)
        try:
            run_lsp_server(workspace=args.workspace)
        finally:
            stop_devtools_background(handle)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
