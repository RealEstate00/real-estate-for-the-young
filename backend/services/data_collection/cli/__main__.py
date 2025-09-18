# Entry point for "data_collection ..." and "python -m backend.services.data_collection.cli"
# Safe delegator: keeps existing scripts intact and forwards args.

import sys, runpy
from importlib import import_module

COMMANDS = {
    "crawl": "backend.services.data_collection.cli.crawl_platforms_raw",
    "api": "backend.services.data_collection.cli.api_cli",
    "normalized": "backend.services.data_collection.cli.normalized_cli",
    # add more commands here as you modularize
}

HELP = f"""data_collection <command> [args]

Commands:
  crawl              Run platform crawlers (see module --help)
  api                API data collection commands (see module --help)
  normalized         Data normalization commands (see module --help)

Examples:
  data_collection crawl --help
  data_collection crawl --target sohouse --since 2025-01-01
  data_collection api --help
  data_collection api load
  data_collection api housing
  data_collection normalized --help
  data_collection normalized process
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

    # Forward arguments to the target module as if it was called directly.
    sys.argv = [f"{module_path}"] + rest
    runpy.run_module(module_path, run_name="__main__")

if __name__ == "__main__":
    main()
