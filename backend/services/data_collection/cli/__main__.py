# Entry point for "data-collection ..." and "python -m backend.services.data_collection.cli"
# Safe delegator: keeps existing scripts intact and forwards args.

import sys, runpy
from importlib import import_module

COMMANDS = {
    "crawl": "backend.services.data_collection.cli.housing.crawl_platforms_raw",
    "api": "backend.services.data_collection.cli.api_cli",
    "normalized": "backend.services.data_collection.cli.housing.normalized_cli",
    # add more commands here as you modularize
}

HELP = f"""data-collection <command> [args]

Commands:
  crawl              Run platform crawlers (see module --help)
  api                API data collection commands (see module --help)
  normalized         Data normalization commands (see module --help)

Examples:
  data-collection crawl --help
  data-collection crawl --target sohouse --since 2025-01-01
  data-collection api --help
  data-collection api load
  data-collection api housing
  data-collection normalized --help
  data-collection normalized process
"""

def main() -> None:
    # 환경 변수 설정 (기본값)
    import os
    os.environ.setdefault("PG_USER", "postgres")
    os.environ.setdefault("PG_PASSWORD", "post1234")
    os.environ.setdefault("PG_DB", "rey")
    os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://postgres:post1234@localhost:5432/rey")
    
    # If no subcommand, print help.
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help"}:
        print(HELP)
        sys.exit(0)

    cmd, rest = sys.argv[1], sys.argv[2:]
    module_path = COMMANDS.get(cmd)
    if not module_path:
        print(f"Unknown command: {cmd}\n")
        print(HELP)
        sys.exit(2)

    # Forward arguments to the target module as if it was called directly.
    sys.argv = [f"{module_path}"] + rest
    runpy.run_module(module_path, run_name="__main__")

if __name__ == "__main__":
    main()
