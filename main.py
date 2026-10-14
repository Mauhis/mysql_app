"""Executable entry point for the MySQL database application."""

from cli import run_application
import argparse


def main():
    """Launch the desktop client, or the terminal client with --cli."""
    parser = argparse.ArgumentParser(description='MySQL practice database creator')
    parser.add_argument('--cli', action='store_true', help='Use the terminal interface')
    args = parser.parse_args()
    if args.cli:
        return run_application()
    try:
        from desktop import run_desktop
    except ModuleNotFoundError as error:
        if error.name != 'tkinter':
            raise
        parser.exit(1, 'Tkinter is unavailable. Install your Python Tk package or run with --cli.\n')
    return run_desktop()


if __name__ == "__main__":
    raise SystemExit(main())
