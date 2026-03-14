#!/usr/bin/env python3
"""
EOC Roster Generator - Main Entry Point

A terminal application that generates optimized monthly shift rosters
for an 18-member EOC team working 24/7 operations with 8-hour rotational shifts.

Usage:
    python eoc_roster_generator.py

Author: EOC Team
Version: 1.0
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from roster.cli import RosterCLI


def main():
    """Main entry point for the application."""
    cli = RosterCLI()
    cli.run()


if __name__ == "__main__":
    main()
