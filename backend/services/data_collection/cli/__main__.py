# Entry point for "data_collection ..." and "python -m backend.services.data_collection.cli"
# Safe delegator: keeps existing scripts intact and forwards args.

import sys, runpy
from importlib import import_module

COMMANDS = {
    "crawl": "backend.services.data_collection.cli.crawl_platforms_raw",
    "migrate-pg": "backend.services.data_collection.cli.migrate_to_postgresql",
    "migrate-db": "backend.services.data_collection.cli.migrate_database",
    "load-csv-mysql": "backend.services.data_collection.cli.load_csv_to_mysql",
    "load-mysql": "backend.services.data_collection.cli.load_to_mysql",
    "db-create-load": "backend.services.data_collection.cli.db_create_and_load",
    # add more commands here as you modularize
}

HELP = f"""data-collection <command> [args]

Commands:
  crawl              Run platform crawlers (see module --help)
  migrate-pg         Migrate data to PostgreSQL
  migrate-db         Generic migration script
  load-csv-mysql     Load CSV into MySQL
  load-mysql         Load into MySQL
  db-create-load     Create DB and load

Examples:
  data-collection crawl --help
  data-collection crawl --target sohouse --since 2025-01-01
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
