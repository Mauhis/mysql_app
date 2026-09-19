"""Executable entry point for the MySQL database application."""

from cli import run_application


def main():
    """Run the command-line application and return its exit status."""
    return run_application()


if __name__ == "__main__":
    raise SystemExit(main())
