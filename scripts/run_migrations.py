#!/usr/bin/env python3
"""
Script to run Alembic migrations against Docker database.

Usage:
    python scripts/run_migrations.py upgrade head
    python scripts/run_migrations.py downgrade base
    python scripts/run_migrations.py current
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic import command
from alembic.config import Config

def main():
    """Run Alembic command with Docker database URL."""
    # Use Docker database URL (db host instead of localhost)
    os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/bank_statements_test"
    
    # Create Alembic config
    config = Config("alembic.ini")
    
    # Get command from arguments
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_migrations.py [command] [args...]")
        print("Commands: upgrade, downgrade, current, history")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "upgrade":
        target = sys.argv[2] if len(sys.argv) > 2 else "head"
        print(f"Running: alembic upgrade {target}")
        command.upgrade(config, target)
        print("✓ Migration complete")
        
    elif cmd == "downgrade":
        target = sys.argv[2] if len(sys.argv) > 2 else "base"
        print(f"Running: alembic downgrade {target}")
        command.downgrade(config, target)
        print("✓ Downgrade complete")
        
    elif cmd == "current":
        print("Current revision:")
        command.current(config)
        
    elif cmd == "history":
        print("Migration history:")
        command.history(config)
        
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
