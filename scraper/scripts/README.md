# Scraper Command-Line Tools

This directory contains command-line tools for scraping crag data and uploading boulder photos.

## Overview

The scripts in this directory provide command-line tools for scraping data from 27crags.com and uploading boulder photos to Cloudinary. These scripts allow you to:

1. Scrape crag data from 27crags.com and save to JSON files
2. Upload boulder photos to Cloudinary

**Note:** Database storage operations have been removed from these scripts. For database operations, please use the scripts in the `database/management` directory.

## Main Entry Point

The main entry point for all commands is `scraper_cli.py`. This script provides a unified interface to all scraper-related operations.

```bash
python scripts/scraper_cli.py <command> [options]
```

or if you made the scripts executable:

```bash
./scripts/scraper_cli.py <command> [options]
```

Available commands:
- `scrape`: Scrape a crag from 27crags.com
- `upload`: Upload boulder photos for a crag to Cloudinary
- `help`: Show help information

## Individual Scripts

### Scrape Crag

Scrapes data from a 27crags.com crag page and saves it to a JSON file.
Can optionally upload boulder photos directly after scraping.

```bash
./scripts/scrape_crag.py <crag_name> [--verbose] [--upload-photos]
```

Options:
- `crag_name`: Name of the crag to scrape (e.g., "inia-droushia")
- `--verbose`, `-v`: Print verbose progress information
- `--upload-photos`, `-u`: Upload boulder photos after scraping

### Upload Boulder Photos

Uploads boulder photos for a crag to Cloudinary.

```bash
./scripts/upload_boulder_photos.py <crag_name> [--verbose]
```

Options:
- `crag_name`: Name of the crag to upload photos for (e.g., "inia-droushia")
- `--verbose`, `-v`: Print verbose information

## Database Integration

To integrate the scraped data with your database, use the management scripts in `database/management`:

1. `init_db_all.py`: Initialize the database schema
2. `init_crag_core.py`: Import boulder and route data from the JSON files created by the scraper

This separation allows for more control over your database operations while still leveraging the scraped data.

## Examples

### Scrape a crag with verbose output

```bash
./scripts/scraper_cli.py scrape inia-droushia --verbose
```

### Scrape a crag and upload photos in one command

```bash
./scripts/scraper_cli.py scrape inia-droushia --upload-photos
```

### Upload boulder photos for a crag

```bash
./scripts/scraper_cli.py upload inia-droushia
```

### Get help for a specific command

```bash
./scripts/scraper_cli.py help scrape
``` 