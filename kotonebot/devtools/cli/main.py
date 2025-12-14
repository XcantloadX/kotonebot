import argparse
import sys
from .server import start_devtools


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
    
    args = parser.parse_args()
    
    if args.command == "devtools":
        start_devtools(
            host=args.host,
            port=args.port,
            open_browser=not args.no_browser
        )
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
