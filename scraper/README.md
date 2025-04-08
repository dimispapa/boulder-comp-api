# 27crags Data Scraper

## Overview

The scraper module provides functionality to extract bouldering data from 27crags.com, transforming it into structured data for the Boulder Competition API. The scraper handles authentication, rate limiting, and extraction of complex data including route information, boulder photos, and route line data (SVG paths that show the climbing route on a boulder image).

## Architecture

The scraper is built with a modular architecture designed to handle JavaScript-rendered pages, authentication, and proper data extraction:

### Core Components

1. **CragScraper Class** (`core.py`): Main class orchestrating the scraping process with methods to:
   - Navigate through crags, sectors, boulders, and routes
   - Handle authentication and session management
   - Extract structured data from HTML
   - Process route lines and photo data

2. **Data Models** (`models.py`): Defines the data structures for:
   - Crags (collection of boulders at a location)
   - Boulders (individual climbing features)
   - Routes (specific climbing paths on boulders)
   - Boulder Photos and Route Line Data

3. **Data Storage** (`data_storage.py`): Handles persisting scraped data to the database:
   - Maps scraped objects to database models
   - Creates/updates records while maintaining relationships
   - Handles Boulder-Sector mappings for proper organization

4. **Authentication** (`auth_utils.py`): Manages authentication with 27crags:
   - Standard HTTP-based login
   - Playwright-based login for JavaScript-heavy pages
   - Detection of authentication requirements

5. **Playwright Utilities** (`playwright_utils.py`): Provides browser automation for:
   - Rendering JavaScript-heavy pages
   - Extracting data from dynamic content
   - Handling authentication in browser context
   - Managing browser sessions efficiently

## Scraping Process Flow

1. **Initialization**:
   - Create a CragScraper instance
   - Initialize HTTP session with appropriate headers
   - Set up rate limiting
   - Initialize Playwright if needed for JavaScript rendering

2. **Authentication**:
   - Attempt standard HTTP-based login
   - Fall back to Playwright-based login if necessary
   - Maintain authenticated session throughout scraping

3. **Crag Scraping**:
   - Start with a crag URL
   - Extract all boulder URLs from the crag page
   - Process boulders in batches with rate limiting

4. **Boulder Processing**:
   - Extract boulder details (name, GPS coordinates)
   - Get boulder photos
   - Extract route information
   - Process route lines data from photos

5. **Route Line Data Extraction**:
   - Identify SVG path data in the HTML
   - Extract route lines coordinates
   - Associate route lines with specific photos
   - Parse and normalize coordinate data

6. **Data Storage**:
   - Map scraped objects to database models
   - Look up sector mappings for proper organization
   - Create or update records in database
   - Maintain relationships between entities (boulders → routes → lines)

## Implementation Details

### Rate Limiting and Batch Processing

The scraper implements sophisticated rate limiting to avoid overloading the target website:
- Configurable request intervals with randomized delays
- Batch processing of boulders
- Automatic retry logic for failed requests

```python
# Example of rate limiting implementation
async def _rate_limit(self) -> None:
    """Async version of rate limiting with randomization."""
    async with self._rate_limit_lock:
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        base_delay = self.min_request_interval

        # Add randomness to the delay (±30%)
        jitter = base_delay * 0.3 * (2 * random.random() - 1)
        delay = max(0, base_delay + jitter - time_since_last_request)

        if delay > 0:
            await asyncio.sleep(delay)
        self.last_request_time = time.time()
```

### JavaScript Rendering

For pages with JavaScript-rendered content (like route lines on photos), the scraper uses Playwright:

```python
# Example of Playwright-based content extraction
async def get_content(self, url: str, wait_for_selector: str = None, wait_timeout: int = 10000) -> str:
    """Get page content using Playwright for JavaScript rendering."""
    if not self.is_initialized:
        await self.initialize()
    
    try:
        await self.page.goto(url)
        if wait_for_selector:
            await self.page.wait_for_selector(wait_for_selector, timeout=wait_timeout)
        return await self.page.content()
    except Exception as e:
        logger.error(f"Error getting content for {url}: {str(e)}")
        raise
```

### Route Line Extraction

The scraper can extract route line data from SVG paths embedded in the HTML:

```python
# Example of route line extraction
def _extract_lines_data(self, img_div, photo_id):
    """Extract route line data from SVG paths."""
    line_data = {}
    
    # Find SVG paths within the image container
    svg_paths = img_div.select('path')
    for path in svg_paths:
        route_id = path.get('id')
        if not route_id or not route_id.startswith('route-'):
            continue
            
        # Extract route ID from path ID
        route_id = route_id.replace('route-', '')
        
        # Get path data
        path_data = path.get('d')
        if not path_data:
            continue
            
        # Parse path data into coordinates
        coordinates = parse_svg_path(path_data)
        
        # Store in dictionary
        line_data[route_id] = {
            'photo_id': photo_id,
            'coordinates': coordinates
        }
    
    return line_data
```

## Usage

The scraper is designed to be used within the API's background tasks:

```python
# Example of how to use the scraper
async def scrape_crag(crag_name: str, db_session: Session):
    """
    Scrape a crag and store the data in the database.
    """
    headers = {"User-Agent": "Mozilla/5.0 ..."}
    
    scraper = CragScraper(
        headers=headers,
        session=db_session,
        crag_name=crag_name
    )
    
    # Authenticate and scrape
    async with aiohttp.ClientSession() as http_session:
        await scraper.login(http_session)
        crag_data = await scraper.scrape_crag()
        
    # Store the data
    status = store_crag_data(crag_data, db_session)
    
    return status
```

## Integration with API and Celery

The scraper integrates deeply with the FastAPI backend and Celery task queue to provide scalable, asynchronous data collection. This architecture enables efficient scraping of large datasets without blocking API responses.

### API to Celery Workflow

1. **API Endpoints**:
   - The API exposes endpoints for initiating scraping operations:
     - `/api/scraper/crags/{crag_name}` - Trigger scraping for a specific crag
     - `/api/scraper/status/{task_id}` - Check status of a running scrape task
     - `/api/admin/scraper/schedule` - Schedule periodic scraping tasks

2. **Task Delegation**:
   ```python
   # Example API endpoint
   @router.post("/scraper/crags/{crag_name}", response_model=ScrapeTaskResponse)
   async def trigger_crag_scrape(
       crag_name: str,
       background_tasks: BackgroundTasks,
       current_user: User = Depends(get_current_user)
   ):
       # Verify permissions
       if current_user.role not in [UserRole.ADMIN, UserRole.MODERATOR]:
           raise HTTPException(status_code=403, detail="Not authorized to trigger scraping")
       
       # Delegate to Celery task
       task = scrape_crag_task.delay(crag_name)
       
       # Store task reference
       background_tasks.add_task(update_task_status, task.id, "PENDING")
       
       return {
           "task_id": task.id,
           "status": "PENDING",
           "crag_name": crag_name
       }
   ```

3. **Celery Task Definition**:
   ```python
   # tasks/scraper_tasks.py
   @celery_app.task(bind=True, name="scrape_crag")
   def scrape_crag_task(self, crag_name: str):
       """Celery task that runs a crag scraper."""
       task_id = self.request.id
       update_task_status(task_id, "PROCESSING")
       
       try:
           # Set up database session
           db = get_db_session()
           
           # Run scraper in async event loop
           loop = asyncio.get_event_loop()
           result = loop.run_until_complete(
               run_scraper(crag_name, db)
           )
           
           # Mark as completed
           update_task_status(task_id, "COMPLETED", result=result)
           return result
           
       except Exception as e:
           # Handle errors
           logger.error(f"Error scraping crag {crag_name}: {str(e)}")
           update_task_status(task_id, "FAILED", error=str(e))
           raise
       finally:
           if db:
               db.close()
   ```

4. **Async Scraper Execution**:
   ```python
   # tasks/scraper_utils.py
   async def run_scraper(crag_name: str, db_session: Session):
       """Run the scraper with proper initialization and cleanup."""
       # Initialize scraper
       headers = get_random_user_agent()
       scraper = CragScraper(
           headers=headers,
           session=db_session,
           crag_name=crag_name
       )
       
       # Create HTTP session
       async with aiohttp.ClientSession() as http_session:
           # Handle authentication
           await scraper.login(http_session)
           
           # Run the scraper
           crag_data = await scraper.scrape_crag()
           
           # Store the results
           storage_result = store_crag_data(crag_data, db_session)
           
           # Clean up resources
           await scraper.cleanup()
           
       return {
           "crag": crag_name,
           "boulders_count": len(crag_data.boulders),
           "routes_count": sum(len(b.routes) for b in crag_data.boulders),
           "status": "success",
           "storage_result": storage_result
       }
   ```

### Task Status Tracking

The system keeps track of all scraping tasks for monitoring and debugging:

1. **Task Status Database Model**:
   ```python
   class ScraperTask(SQLModel, table=True):
       __tablename__ = "scraper_tasks"
       
       id: str = Field(primary_key=True)  # Celery task ID
       crag_name: str
       status: str  # "PENDING", "PROCESSING", "COMPLETED", "FAILED"
       result: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
       error: Optional[str] = None
       created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
       updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
   ```

2. **Status Updating Utility**:
   ```python
   def update_task_status(task_id: str, status: str, result: Dict = None, error: str = None):
       """Update the status of a scraper task in the database."""
       with get_db_session() as db:
           task = db.query(ScraperTask).filter(ScraperTask.id == task_id).first()
           if not task:
               # Create new task record
               task = ScraperTask(id=task_id, status=status)
               db.add(task)
           else:
               # Update existing task
               task.status = status
               
           if result:
               task.result = result
           if error:
               task.error = error
               
           task.updated_at = datetime.now(UTC)
           db.commit()
   ```

### Scheduled and Batch Operations

For maintaining up-to-date data, the system supports scheduled and batch operations:

1. **Scheduled Scraping**:
   ```python
   @celery_app.task(name="scheduled_crag_refresh")
   def scheduled_crag_refresh():
       """Refresh data for crags that haven't been updated recently."""
       # Find crags to update
       with get_db_session() as db:
           stale_crags = db.query(Crag).filter(
               Crag.updated_at < datetime.now(UTC) - timedelta(days=7)
           ).all()
           
           # Create tasks for each crag
           for crag in stale_crags:
               # Stagger task execution to avoid overloading Celery
               scrape_crag_task.apply_async(
                   args=[crag.name],
                   countdown=random.randint(60, 600)  # Random delay between 1-10 minutes
               )
   ```

2. **Batch Processing Controls**:
   ```python
   # Configuration options (typically in environment variables)
   BATCH_SIZE = int(os.getenv("SCRAPER_BATCH_SIZE", "10"))  # Process 10 boulders at a time
   BATCH_DELAY = float(os.getenv("SCRAPER_BATCH_DELAY", "5"))  # 5 second delay between batches
   MAX_CONCURRENT_TASKS = int(os.getenv("SCRAPER_MAX_CONCURRENT_TASKS", "3"))
   ```

### Error Recovery and Resilience

The integration includes robust error handling and recovery mechanisms:

1. **Automatic Retry Logic**:
   ```python
   @celery_app.task(
       bind=True,
       name="scrape_crag",
       max_retries=3,
       default_retry_delay=300  # 5 minutes
   )
   def scrape_crag_task(self, crag_name: str):
       """Celery task with automatic retry logic."""
       try:
           # Task implementation
           # ...
       except (ConnectionError, TimeoutError) as e:
           # Network-related errors should be retried
           logger.warning(f"Network error while scraping {crag_name}, retrying: {str(e)}")
           update_task_status(self.request.id, "RETRY", error=str(e))
           raise self.retry(exc=e)
       except Exception as e:
           # Other errors, don't retry
           logger.error(f"Error scraping crag {crag_name}: {str(e)}")
           update_task_status(self.request.id, "FAILED", error=str(e))
           raise
   ```

2. **Partial Results Handling**:
   ```python
   async def run_scraper(crag_name: str, db_session: Session):
       # ... initialization code ...
       
       results = {
           "crag": crag_name,
           "success": True,
           "partial_success": False,
           "boulders_processed": 0,
           "boulders_failed": 0,
           "routes_processed": 0
       }
       
       try:
           # ... scraper execution ...
           
           # Process boulders with partial result tracking
           for i, boulder in enumerate(crag_data.boulders):
               try:
                   # Process boulder
                   # ...
                   results["boulders_processed"] += 1
                   results["routes_processed"] += len(boulder.routes)
               except Exception as e:
                   logger.error(f"Error processing boulder {boulder.name}: {str(e)}")
                   results["boulders_failed"] += 1
                   results["partial_success"] = True
                   continue  # Try next boulder
                   
           return results
       except Exception as e:
           results["success"] = False
           results["error"] = str(e)
           return results
   ```

### Performance Monitoring

The integration includes performance monitoring to track system health:

```python
# Example of performance metrics tracking
def track_scraper_metrics(task_id, crag_name, start_time, end_time, result):
    duration = end_time - start_time
    
    # Record metrics in database
    with get_db_session() as db:
        metrics = ScraperMetrics(
            task_id=task_id,
            crag_name=crag_name,
            duration_seconds=duration.total_seconds(),
            boulders_processed=result.get("boulders_processed", 0),
            routes_processed=result.get("routes_processed", 0),
            success=result.get("success", False),
            partial_success=result.get("partial_success", False),
            memory_usage_mb=get_current_memory_usage(),
            timestamp=datetime.now(UTC)
        )
        db.add(metrics)
        db.commit()

# Utility to get memory usage
def get_current_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # Convert to MB
```

## Configuration

The scraper behavior can be configured through environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_PLAYWRIGHT` | Whether to use Playwright for JavaScript rendering | `true` |
| `MIN_REQUEST_INTERVAL` | Minimum time between requests in seconds | `1.7` |
| `MAX_RETRIES` | Maximum number of retry attempts for failed requests | `3` |
| `RETRY_DELAY` | Delay between retry attempts in seconds | `5` |
| `CRAGS_USERNAME` | Username for 27crags.com | - |
| `CRAGS_PASSWORD` | Password for 27crags.com | - |
| `CRAGS_DOMAIN` | Base domain for 27crags.com | - |
| `USER_AGENT_1` through `USER_AGENT_5` | Rotating user agents | - |

## Error Handling

The scraper implements comprehensive error handling:
- Retries for transient network errors
- Detailed logging
- Graceful recovery from authentication failures
- Fallback mechanisms for different extraction methods

## Challenges and Solutions

### Challenge: JavaScript-Rendered Content
**Solution**: Implemented Playwright integration to handle JavaScript rendering, with fallback to standard HTTP requests for simpler content.

### Challenge: Rate Limiting
**Solution**: Developed adaptive rate limiting with randomized delays and batch processing to avoid detection.

### Challenge: Authentication
**Solution**: Dual authentication approach with both standard HTTP and browser-based authentication options.

### Challenge: Complex Route Line Data
**Solution**: Custom SVG path parsing and coordinate normalization to accurately represent climbing routes. 