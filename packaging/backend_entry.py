"""Frozen entry point for the Director-bot backend (PyInstaller target).

Delegates to the Typer CLI so the frozen binary behaves like
`director-bot <command>` (serve, demo, short, ...).
"""
import multiprocessing

from director_bot.cli import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
