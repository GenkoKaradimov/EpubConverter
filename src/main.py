"""
Entry point: create Application and run it (GUI main loop).
All code and comments in English.
"""

from __future__ import annotations


def main() -> None:
    from app.application import Application

    app = Application()
    app.run()


if __name__ == "__main__":
    main()
