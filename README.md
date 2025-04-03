# Boulder Competition API

API service for the Bouldering Festival Competition app, providing score calculation and 27crags data scraping capabilities.

## Features

- **FastAPI Backend**: High-performance, easy-to-use API framework.
- **Celery Integration**: Background task processing for resource-intensive operations.
- **PostgreSQL Database**: Using SQLModel ORM for a type-safe, Pydantic-compatible database interface.
- **NeonDB Integration**: Connect to a PostgreSQL-compatible serverless database.
- **Docker Support**: Containerized setup for easy deployment and development.
- **Asynchronous Processing**: Handle concurrent requests efficiently.
- **Cloudinary Integration**: For media storage and processing.
- **Redis**: For task queueing and caching.

## Technology Stack

- **FastAPI**: Modern, fast API framework
- **Celery**: Distributed task queue
- **Redis**: Message broker for Celery
- **SQLModel**: ORM for PostgreSQL database
- **NeonDB**: Serverless PostgreSQL database
- **Docker & Docker Compose**: Containerization
- **Cloudinary**: Cloud-based image management
- **Playwright**: For web scraping automation

## Project Structure

```file
boulder-comp-api/
├── api/                  # FastAPI endpoints and route handlers
├── scraper/              # 27crags scraping logic
├── scoring/              # Score calculation logic
│   ├── scoring.md        # Scoring system documentation and calculation details
├── tasks/                # Celery background tasks
├── utils/                # Common utilities and helpers
├── tests/                # Unit and integration tests
│   └── testing.md        # Testing documentation and guidelines
├── supabase/             # Supabase configuration and migrations
├── docs/                 # Documentation and diagrams
│   └── media_storage.md  # Media storage implementation details
├── main.py               # FastAPI app entry point
├── .env                  # Environment variables (not committed)
├── docker-compose.yml    # Docker Compose configuration
├── Dockerfile            # Docker configuration for FastAPI app
├── Dockerfile.celery     # Docker configuration for Celery worker
├── requirements.txt      # Python dependencies
├── heroku.yml            # Heroku container deployment configuration
├── Procfile              # Heroku process definitions
├── app.json              # Heroku app configuration
└── .dockerignore         # Files to exclude from Docker builds
```

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Database Configuration
DATABASE_URL=postgresql://user:password@hostname:port/database

# Redis Configuration (for Celery)
REDIS_URL=redis://localhost:6379/0

# Development Environment
DEBUG=True
ENVIRONMENT=development

# API Configuration
API_PREFIX=/api
API_HOST=0.0.0.0
API_PORT=8000

# Cloudinary Configuration (for media uploads)
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

For Heroku deployment, these variables should be set using the Heroku CLI or dashboard.

## Setup and Installation

### Option 1: Using Docker (Recommended)

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/boulder-comp-api.git
   cd boulder-comp-api
   ```

2. Create the `.env` file as described in the Environment Variables section above

3. Build and start the Docker containers:

   ```bash
   docker compose up -d
   ```

   This will start:
   - FastAPI application (accessible at <http://localhost:8000>)
   - Celery worker for background tasks
   - Redis for message brokering

4. Access the API documentation:
   - Open `http://localhost:8000/docs` in your browser

### Option 2: Local Development

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/boulder-comp-api.git
   cd boulder-comp-api
   ```

2. Set up a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create the `.env` file as described in the Environment Variables section above

5. Start Redis (required for Celery):

   ```bash
   # Using Docker
   docker run -d -p 6379:6379 redis
   # Or install Redis locally
   ```

6. Start the FastAPI server:

   ```bash
   uvicorn main:app --reload
   ```

7. Start the Celery worker:

   ```bash
   celery -A tasks worker --loglevel=info
   ```

## Docker Commands

- Start all services:

  ```bash
  docker-compose up -d
  ```

- View logs:

  ```bash
  docker-compose logs -f
  ```

- Rebuild services after making changes:

  ```bash
  docker-compose up -d --build
  ```

- Stop all services:

  ```bash
  docker-compose down
  ```

- Access a container's shell:

  ```bash
  docker-compose exec api bash
  docker-compose exec celery-worker bash
  ```

- View running containers:

  ```bash
  docker-compose ps
  ```

- Check container resource usage:

  ```bash
  docker stats
  ```

## Docker Development Tips

### Essential Docker Commands
```bash
# Start all services (use --build after changing dependencies)
docker compose up -d --build

# View logs for all services or specific ones
docker compose logs -f
docker compose logs -f api          # FastAPI logs
docker compose logs -f celery-worker # Celery logs

# Stop all services
docker compose down

# Access container shell
docker compose exec api bash
docker compose exec celery-worker bash
```

### Understanding the `--build` Flag

The `--build` flag is critical to understand:

```bash
# Without --build: Uses cached images, might miss dependency updates
docker compose up -d

# With --build: Forces rebuild with fresh dependencies
docker compose up -d --build
```

When to use `--build`:
- After modifying `requirements.txt`
- After changing Dockerfile or Dockerfile.celery
- If you encounter module import errors (e.g., "ModuleNotFoundError")
- When switching branches with different dependencies

Common errors without `--build`:
- Missing module errors
- Outdated dependencies
- Changes to Docker configuration not applied

### Troubleshooting Tips

1. **Container Won't Start**:
   - Check logs: `docker compose logs <service_name>`
   - Verify environment variables in `.env`

2. **Redis Connection Issues**:
   ```bash
   # Check Redis is running
   docker compose ps redis
   # Verify connection
   docker compose exec redis redis-cli ping
   ```

3. **Celery Worker Issues**:
   ```bash
   # Check detailed logs
   docker compose logs celery-worker
   # Restart worker
   docker compose restart celery-worker
   ```

4. **Cleanup and Maintenance**:
   ```bash
   # Clean up unused resources
   docker system prune
   
   # Remove all stopped containers, unused networks, dangling images, and build cache
   docker system prune -a
   ```

## Database Design

## 🗄️ Database Schema

### 🧗 Bouldering Data Tables

#### `crags`

| Field         | Type         | Notes                                |
|---------------|--------------|--------------------------------------|
| `id`          | UUID / PK    | Unique crag ID                       |
| `name`        | text         | Unique crag name                     |
| `display_name`| text         | Formatted display name               |
| `description` | text / null  | Optional crag description            |
| `created_at`  | timestamp    | When added                           |
| `updated_at`  | timestamp    | Last updated                         |

#### `sectors`

| Field         | Type         | Notes                                |
|---------------|--------------|--------------------------------------|
| `id`          | UUID / PK    | Unique sector ID                     |
| `name`        | text         | Unique sector name                   |
| `display_name`| text         | Formatted display name               |
| `crag_id`     | FK → crags.id| Reference to parent crag             |
| `description` | text / null  | Optional sector description          |
| `created_at`  | timestamp    | When added                           |
| `updated_at`  | timestamp    | Last updated                         |

#### `boulders`

| Field         | Type           | Notes                                |
|---------------|----------------|--------------------------------------|
| `id`          | UUID / PK      | Unique boulder ID                    |
| `name`        | text           | Boulder name                         |
| `display_name`| text           | Formatted display name               |
| `url`         | text           | 27crags URL                          |
| `sector_id`   | FK → sectors.id| Reference to sector                  |
| `gps_postgis`  | GEOGRAPHY(POINT)| PostGIS formatted coordinates (POINT(lon lat))|
| `gps_string`  | text           | Raw coordinates string (lat, lon)    |
| `created_at`  | timestamp      | When added                           |
| `updated_at`  | timestamp      | Last updated                         |

#### `boulder_photos`

| Field        | Type         | Notes                                      |
|--------------|--------------|--------------------------------------------|
| `id`         | UUID / PK    | Unique photo ID                            |
| `boulder_id` | FK → boulders.id | Linked boulder                        |
| `url`        | text         | Original photo URL                         |
| `photo_id`   | text         | Photo identifier                           |
| `storage_url`| text / null  | URL in Supabase Storage after upload       |
| `lines_data` | JSONB / null | Optional route line data                   |
| `created_at` | timestamp    | When added                                 |
| `updated_at` | timestamp    | Last updated                               |

#### `routes`

| Field        | Type         | Notes                                    |
|--------------|--------------|------------------------------------------|
| `id`         | UUID / PK    | Unique route ID                          |
| `boulder_id` | FK → boulders.id | Linked boulder                      |
| `name`       | text         | Route name                               |
| `display_name`| text        | Formatted display name                   |
| `url`        | text         | Route URL on 27crags                     |
| `grade`      | text         | e.g. '6A+', '7B'                         |
| `rating`     | float / null | Route rating                             |
| `description`| text / null  | Route description                        |
| `line_data`  | JSONB / null | Route line data                          |
| `created_at` | timestamp    | When added                               |
| `updated_at` | timestamp    | Last updated                             |

#### `boulder_sector_mappings`

| Field         | Type           | Notes                               |
|---------------|----------------|-------------------------------------|
| `id`          | UUID / PK      | Unique mapping ID                   |
| `boulder_url` | text           | URL of boulder on 27crags           |
| `sector_name` | text           | Name of the sector                  |
| `sector_id`   | FK → sectors.id| Reference to sector                 |
| `created_at`  | timestamp      | When added                          |
| `updated_at`  | timestamp      | Last updated                        |

---

### 🧑‍🤝‍🧑 Competition Tables

#### `competitions`

| Field         | Type           | Notes                                                       |
|---------------|----------------|-------------------------------------------------------------|
| `id`          | UUID / PK      | Unique competition ID                                       |
| `name`        | text           | Name of the competition (e.g. "May 2025 Club Comp")         |
| `crag_id`     | FK → crags.id  | Crag where the competition takes place                      |
| `display_name`| text           | Formatted display name                                      |
| `category`    | text[]         | Categories hosted (e.g. "marathon,boulder beasts")          |
| `start_date`  | date           | Competition start date                                      |
| `end_date`    | date           | Competition end date                                        |
| `status`      | enum           | "ongoing" or "completed"                                    |
| `description` | text / null    | Details about the competition                               |
| `venue`       | text / null    | Location/venue of the event                                 |
| `created_at`  | timestamp      | When added                                                  |
| `updated_at`  | timestamp      | Last updated                                                |

#### `teams`

| Field           | Type         | Notes                                                |
|-----------------|--------------|------------------------------------------------------|
| `id`            | UUID / PK    | Unique team ID                                       |
| `competition_id`| FK → competitions.id | Competition this team is registered for      |
| `name`          | text         | Team name                                            |
| `captain_id`    | FK → participants.id | Optional (ID of the team captain)           |
| `category`      | text         | Always `'marathon'` for team entries                 |
| `paid`          | boolean      | Whether the team has been marked as paid             |
| `created_at`    | timestamp    | Signup time                                          |

#### `