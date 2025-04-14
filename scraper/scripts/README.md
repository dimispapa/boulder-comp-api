# Scraper Command-Line Tools

This directory contains command-line tools for scraping, storing, and managing crag data.

## Overview

The scripts in this directory provide command-line alternatives to the API endpoints for scraping and data management. These scripts allow you to:

1. Scrape crag data from 27crags.com
2. Store scraped data to the database
3. Upload boulder photos to Cloudinary

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
- `store`: Store scraped crag data to the database
- `upload`: Upload boulder photos for a crag to Cloudinary
- `help`: Show help information

## Individual Scripts

### Scrape Crag

Scrapes data from a 27crags.com crag page and saves it to a JSON file.
Data is automatically stored to the database after successful scraping.

```bash
./scripts/scrape_crag.py <crag_name> [--verbose]
```

Options:
- `crag_name`: Name of the crag to scrape (e.g., "inia-droushia")
- `--verbose`, `-v`: Print verbose progress information

### Store Crag Data

Stores previously scraped crag data to the database.

```bash
./scripts/store_crag_data.py [--file FILE] [--crag CRAG] [--verbose]
```

Options:
- `--file`, `-f`: Path to the JSON file to store
- `--crag`, `-c`: Name of the crag to find the most recent file for
- `--verbose`, `-v`: Print verbose information

Note: Either `--file` or `--crag` must be provided.

### Upload Boulder Photos

Uploads boulder photos for a crag to Cloudinary.

```bash
./scripts/upload_boulder_photos.py <crag_name> [--verbose]
```

Options:
- `crag_name`: Name of the crag to upload photos for (e.g., "inia-droushia")
- `--verbose`, `-v`: Print verbose information

## Examples

### Scrape a crag with verbose output

```bash
./scripts/scraper_cli.py scrape inia-droushia --verbose
```

### Store the most recent scraped data for a crag

```bash
./scripts/scraper_cli.py store --crag inia-droushia
```

### Upload boulder photos for a crag

```bash
./scripts/scraper_cli.py upload inia-droushia
```

### Get help for a specific command

```bash
./scripts/scraper_cli.py help scrape
``` 