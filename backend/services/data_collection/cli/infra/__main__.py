# Entry point for "data-collection-infra ..." and "python -m backend.services.data_collection.cli.infra"
# Infrastructure and API data collection commands

import sys, runpy
from importlib import import_module

COMMANDS = {
    "api": "backend.services.data_collection.cli.infra.api_cli",
    "normalized": "backend.services.data_collection.cli.infra.infra_normalized_cli",
}

HELP = f"""data-collection-infra <command> [args]

Commands:
  api                API data collection, normalization and DB loading commands (see module --help)
  normalized         Infrastructure data normalization commands (see module --help)

Examples:
  data-collection-infra api --help
  data-collection-infra api collect
  data-collection-infra api load
  data-collection-infra api all
  data-collection-infra normalized --help
  data-collection-infra normalized process
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
