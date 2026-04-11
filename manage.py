"""
ReliOps - CLI entrypoint.
Database init, dev server, and management commands.

Author: Kris R. (UpliftPal)
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, run_server
from app.config import DB_PATH, MOCK_DATA_DIR
from app.models import init_db, seed_from_mock_data


def cmd_init_db():
    db_path = str(DB_PATH)
    init_db(db_path)
    seed_from_mock_data(db_path, str(MOCK_DATA_DIR))
    print(f"Database initialized at {db_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ReliOps CLI')
    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('init-db', help='Initialize database and seed with mock data')

    run_parser = subparsers.add_parser('run', help='Start the development server')
    run_parser.add_argument('--host', default='localhost', help='Bind host (default: localhost)')
    run_parser.add_argument('--port', type=int, default=5000, help='Port (default: 5000)')
    run_parser.add_argument('--cert', default=None, help='SSL certificate .pem file')
    run_parser.add_argument('--key', default=None, help='SSL private key .pem file')
    run_parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

    if args.command == 'init-db':
        cmd_init_db()
    elif args.command == 'run':
        run_server(
            host=args.host,
            port=args.port,
            ssl_cert=args.cert,
            ssl_key=args.key,
            debug=args.debug,
        )
    else:
        parser.print_help()
        sys.exit(1)
