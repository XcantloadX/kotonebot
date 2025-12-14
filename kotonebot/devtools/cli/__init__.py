def main():
    """Entry point for the kbot command."""
    from .main import main as _main
    return _main()

__all__ = ["main"]
