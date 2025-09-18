# Entry point for "data_collection api ..." and "python -m backend.services.data_collection.public-api.api_cli"
# API data collection commands

import sys, runpy
from importlib import import_module

COMMANDS = {
    "load": "backend.services.data_collection.public-api.run",
    "public": "backend.services.data_collection.public-api.run",
    "housing": "backend.services.data_collection.public-api.run",
    "fresh": "backend.services.data_collection.public-api.run",
}

HELP = f"""data_collection api <command> [args]

Commands:
  load                Load all API data
  public              Load public infrastructure data only
  housing             Load housing data only
  fresh [--type]      Fresh load (delete existing data first)
  
  --type options: all, public, housing, bus, convenience, hospital, school, sports, subway

Examples:
  data_collection api load
  data_collection api public
  data_collection api housing
  data_collection api fresh --type all
  data_collection api fresh --type public
"""

def main() -> None:
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