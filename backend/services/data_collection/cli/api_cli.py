# Entry point for "data-collection api ..." and "python -m backend.services.data_collection.public-api.api_cli"
# API data collection commands

import sys, runpy
from importlib import import_module

COMMANDS = {
    "load": "backend.services.data_collection.public-api.run",
    "public": "backend.services.data_collection.public-api.run",
    "housing": "backend.services.data_collection.public-api.run",
    "fresh": "backend.services.data_collection.public-api.run",
}

HELP = f"""data-collection api <command> [args]

Commands:
  load                Load all API data
  public              Load public infrastructure data only
  housing             Load housing data only
  fresh [--type]      Fresh load (delete existing data first)
  
  --type options: all, public, housing, bus, convenience, hospital, school, sports, subway

Examples:
  data-collection api load
  data-collection api public
  data-collection api housing
  data-collection api fresh --type all
  data-collection api fresh --type public
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

    # Map commands to appropriate arguments
    command_args = {
        "load": ["--source", "seoul", "--service", "all"],
        "public": ["--source", "seoul", "--service", "SearchSTNBySubwayLineInfo"],
        "housing": ["--source", "seoul", "--service", "SearchParkInfoService"],
        "fresh": ["--source", "seoul", "--service", "all"]
    }
    
    args = command_args.get(cmd, ["--source", "seoul", "--service", "all"])
    
    # Forward arguments to the target module as if it was called directly.
    sys.argv = [f"{module_path}"] + args + rest
    runpy.run_module(module_path, run_name="__main__")

if __name__ == "__main__":
    main()