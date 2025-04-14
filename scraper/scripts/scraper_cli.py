#!/usr/bin/env python3
"""
Main CLI entry point for scraper commands.
This script provides a unified interface to all scraper-related operations.
"""
import sys
import argparse
import subprocess
from pathlib import Path

# Get absolute paths for key directories
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SCRAPER_DIR = SCRIPT_DIR.parent

# Add project root to Python path
sys.path.append(str(PROJECT_ROOT))


def print_command_help(command_name, description, usage=None):
    """Print help information for a command."""
    print(f"\n{command_name}:")
    print(f"  {description}")
    if usage:
        print(f"  Usage: {usage}")


def execute_command(script_name, args):
    """
    Execute a script with the given arguments.

    Args:
        script_name (str): Name of the script file to execute
        args (list): Command-line arguments to pass to the script

    Returns:
        int: Exit code from the script
    """
    script_path = SCRIPT_DIR / script_name

    if not script_path.exists():
        print(f"Error: Script not found: {script_path}")
        return 1

    # Create the command with arguments
    cmd = [sys.executable, str(script_path)] + args

    # Execute the command
    result = subprocess.run(cmd)
    return result.returncode


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description='Climbing Crag Data CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
    Available commands:
    scrape     Scrape a crag from 27crags.com
    store      Store scraped crag data to the database
    upload     Upload boulder photos for a crag to Cloudinary
    help       Show this help message
    For help on a specific command, use: scraper_cli.py <command> --help
""")

    parser.add_argument('command',
                        choices=['scrape', 'store', 'upload', 'help'],
                        help='Command to execute')

    # Parse just the command argument
    args, remaining = parser.parse_known_args()

    # If help command is requested
    if args.command == 'help':
        if not remaining:
            # Show general help
            parser.print_help()
            print("\nDetailed command help:")
            print_command_help(
                "scrape", "Scrape a crag from 27crags.com",
                "scraper_cli.py scrape <crag_name> [--verbose]")
            print_command_help(
                "store", "Store scraped crag data to the database",
                "scraper_cli.py store [--file FILE] [--crag CRAG] [--verbose]")
            print_command_help(
                "upload", "Upload boulder photos for a crag to Cloudinary",
                "scraper_cli.py upload <crag_name> [--verbose]")
        else:
            # Show help for a specific command
            cmd = remaining[0]
            if cmd == 'scrape':
                execute_command('scrape_crag.py', ['--help'])
            elif cmd == 'store':
                execute_command('store_crag_data.py', ['--help'])
            elif cmd == 'upload':
                execute_command('upload_boulder_photos.py', ['--help'])
            else:
                print(f"Unknown command: {cmd}")
                sys.exit(1)
    else:
        # Execute the selected command
        if args.command == 'scrape':
            sys.exit(execute_command('scrape_crag.py', remaining))
        elif args.command == 'store':
            sys.exit(execute_command('store_crag_data.py', remaining))
        elif args.command == 'upload':
            sys.exit(execute_command('upload_boulder_photos.py', remaining))


if __name__ == "__main__":
    main()
