"""
Standard OpenEnv server entry for tooling (`uv run server`, `openenv validate`).
"""
from __future__ import annotations


def main() -> None:
    from app.server import main as app_main

    app_main()


if __name__ == "__main__":
    main()
