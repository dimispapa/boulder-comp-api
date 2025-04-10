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
├── api/                            # FastAPI endpoints and route handlers
├── scraper/                        # 27crags scraping logic
│   └── README.md                   # Scraper documentation and implementation details
├── scoring/                        # Score calculation logic
│   └── README.md                   # Scoring system documentation and calculation details
├── tasks/                          # Celery background tasks
├── utils/                          # Common utilities and helpers
├── tests/                          # Unit and integration tests
│   └── testing.md                  # Testing documentation and guidelines
├── supabase/                       # Supabase configuration and migrations
├── docs/                           # Documentation and diagrams
│   ├── media/                      # Media storage documentation and diagrams
│   │   ├── README.md               # Media storage implementation details
│   │   └── media_storage_flow.png  # Media storage flow diagram
│   ├── scoring/                    # Scoring system diagrams
│   │   └── scoring_flow.png        # Scoring process flow diagram
│   ├── scraper/                    # Scraper diagrams
│   │   └── scraper_flow.png        # Scraper process flow diagram
│   └── database/                   # Database diagrams
│       └── erd.png                 # Entity relationship diagram
├── main.py                         # FastAPI app entry point
├── .env                            # Environment variables (not committed)
├── docker-compose.yml              # Docker Compose configuration
├── Dockerfile                      # Docker configuration for FastAPI app
├── Dockerfile.celery               # Docker configuration for Celery worker
├── requirements.txt                # Python dependencies
├── heroku.yml                      # Heroku container deployment configuration
├── Procfile                        # Heroku process definitions
├── app.json                        # Heroku app configuration
└── .dockerignore                   # Files to exclude from Docker builds
```

## Key Documentation

- [**Scoring System**](scoring/README.md): Detailed documentation of the competition scoring algorithm and implementation
- [**Media Storage**](docs/media/README.md): Complete overview of the photo storage system, workflows, and security model
- [**Scraper Architecture**](scraper/README.md): Comprehensive guide to the web scraping system for boulder data

## Scoring Calculator

The Boulder Competition API includes a sophisticated scoring calculator that computes rankings for both team-based (Marathon) and individual (Boulder Beasts) competition categories.

### Key Features

- **Team-Based Scoring**: Complex scoring algorithm for the Marathon category that includes:
  - Base points for route difficulty
  - Volume bonuses based on number of ascents
  - Team ascent bonuses for routes completed by all team members
  - Unique ascent bonuses for routes climbed only by one team
  - Master grade bonuses for teams with most ascents at specific grades
  - Score normalization based on team size

- **Individual Scoring**: Simplified scoring for individual competitors (Boulder Beasts) that:
  - Counts only the top 5 highest-scoring routes
  - Applies base points based on route grades
  - Generates rankings based on total points

- **Interactive Results**: Detailed breakdowns of score components for transparency

For complete details on the scoring system, including the mathematical formulas and implementation specifics, see the [Scoring System Documentation](scoring/README.md).

## API and Task Integration

The API is designed as a set of interconnected services that utilize Celery for handling resource-intensive operations asynchronously.

### Core API Routes

1. **Scraper Endpoints** (`/api/scraper`):
   - `/start`: Start scraping a crag (default: "inia-droushia")
   - `/store`: Store previously scraped data to the database
   - `/list-files`: List all scraped data files, optionally filtered by crag name
   - `/task/{task_id}`: Check status of a scraping or storage task
   - `/crags`: List all available crags
   - `/sectors/{crag_id}`: List all sectors for a specific crag

2. **Scoring Endpoints** (`/api/scoring`):
   - `/calculate`: Start calculating scores for a competition
   - `/status/{task_id}`: Get the status of a score calculation task
   - `/rankings/{comp_id}`: Get the latest rankings for a competition

3. **Media Management** (`/api/media`):
   - `/upload-boulder-photos/{crag_name}`: Upload boulder photos for a crag
   - `/upload-competition-photos/{competition_id}`: Handle direct photo uploads from competition participants
   - `/competition-photos/{competition_id}`: Get competition photos
   - `/competition-photos/{photo_id}/approve`: Approve or reject a competition photo
   - `/competition-photos/{photo_id}/feature`: Feature or unfeature a competition photo

### Celery Integration

API endpoints are designed to delegate resource-intensive tasks to Celery workers for asynchronous processing:

1. **Task Delegation Pattern**:
   ```python
   @router.post("/start")
   async def start_scraping(background_tasks: BackgroundTasks,
                           crag_name: str = "inia-droushia") -> Dict[str, Any]:
       # Use the registered task
       task = scrape_crag_task.delay(crag_name)
       return {
           "status": "success",
           "message": "Scraping task started",
           "task_id": task.id,
           "task_type": "scrape"
       }
   ```

2. **Task Monitoring**:
   - Status tracking endpoints (`/api/scraper/task/{task_id}`, `/api/scoring/status/{task_id}`)
   - Detailed progress reporting and error handling

3. **Common Celery Tasks**:
   - **Scraping**: Asynchronous extraction of boulder data from 27crags
   - **Data Storage**: Storing scraped data to the database
   - **Scoring Calculation**: Computing competition rankings for Marathon and Boulder Beasts categories
   - **Media Processing**: Uploading and processing photos to Cloudinary

This architecture allows the API to remain responsive while handling computationally intensive operations efficiently in the background. Tasks can scale horizontally by adding more Celery workers as needed.

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

### 🗄️ Database Schema

#### 🧗 Bouldering Data Tables

#### `crags`

| Field         | Type         | Notes                                |
|---------------|--------------|--------------------------------------|
| `id`          | UUID / PK    | Unique crag ID                       |
| `name`        | text         | Unique crag name                     |
| `display_name`| text         | Formatted display name               |
| `description` | text / null  | Optional crag description            |
| `inserted_at`  | timestamp    | When added                           |
| `updated_at`  | timestamp    | Last updated                         |

#### `sectors`

| Field         | Type         | Notes                                |
|---------------|--------------|--------------------------------------|
| `id`          | UUID / PK    | Unique sector ID                     |
| `name`        | text         | Unique sector name                   |
| `display_name`| text         | Formatted display name               |
| `crag_id`     | FK → crags.id| Reference to parent crag             |
| `description` | text / null  | Optional sector description          |
| `inserted_at`  | timestamp    | When added                           |
| `updated_at`  | timestamp    | Last updated                         |

#### `boulders`

| Field         | Type           | Notes                                |
|---------------|----------------|--------------------------------------|
| `id`          | UUID / PK      | Unique boulder ID                    |
| `name`        | text           | Boulder name                         |
| `display_name`| text           | Formatted display name               |
| `url`         | text           | 27crags URL                          |
| `sector_id`   | FK → sectors.id| Reference to sector                  |
| `gps_postgis` | text / null    | PostGIS formatted coordinates        |
| `gps_string`  | text / null    | Raw coordinates string               |
| `inserted_at`  | timestamp      | When added                           |
| `updated_at`  | timestamp      | Last updated                         |

#### `boulder_photos`

| Field        | Type         | Notes                                      |
|--------------|--------------|--------------------------------------------|
| `id`         | UUID / PK    | Unique photo ID                            |
| `boulder_id` | FK → boulders.id | Linked boulder                        |
| `source_url` | text         | Original source URL (where photo was scraped from) |
| `order`      | int          | Order/position of the photo                |
| `photo_id`   | text         | Photo identifier                           |
| `storage_url`| text / null  | URL in Cloudinary after upload             |
| `lines_data` | JSONB / null | Optional route line data                   |
| `inserted_at` | timestamp    | When added                                 |
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
| `inserted_at` | timestamp    | When added                               |
| `updated_at` | timestamp    | Last updated                             |

#### `boulder_sector_mappings`

| Field         | Type           | Notes                               |
|---------------|----------------|-------------------------------------|
| `id`          | UUID / PK      | Unique mapping ID                   |
| `boulder_url` | text           | URL of boulder on 27crags           |
| `sector_name` | text           | Name of the sector                  |
| `sector_id`   | FK → sectors.id| Reference to sector                 |
| `inserted_at`  | timestamp      | When added                          |
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
| `start_date`  | datetime       | Competition start date                                      |
| `end_date`    | datetime       | Competition end date                                        |
| `status`      | enum           | Competition status: "upcoming", "ongoing", or "completed"   |
| `description` | text / null    | Details about the competition                               |
| `venue`       | text / null    | Location/venue of the event                                 |
| `inserted_at`  | timestamp      | When added                                                  |
| `updated_at`  | timestamp      | Last updated                                                |

#### `competition_categories`

| Field           | Type                | Notes                                        |
|-----------------|---------------------|----------------------------------------------|
| `id`            | UUID / PK           | Unique category ID                           |
| `competition_id`| FK → competitions.id| Competition this category belongs to         |
| `category_type` | enum                | "marathon" or "boulder_beasts"               |
| `name`          | text                | Category name                                |
| `description`   | text / null         | Category description                         |
| `display_order` | int                 | Order for display in UI                      |
| `inserted_at`    | timestamp           | When added                                   |
| `updated_at`    | timestamp           | Last updated                                 |

#### `teams`

| Field           | Type                | Notes                                        |
|-----------------|---------------------|----------------------------------------------|
| `id`            | UUID / PK           | Unique team ID                               |
| `competition_id`| FK → competitions.id| Competition this team is registered for      |
| `name`          | text                | Team name                                    |
| `captain_id`    | FK → participants.id| Team captain (uses named FK constraint)      |
| `category`      | text                | Competition category ("marathon")            |
| `inserted_at`    | timestamp           | When added                                   |
| `updated_at`    | timestamp           | Last updated                                 |

#### `participants`

| Field           | Type             | Notes                                        |
|-----------------|------------------|----------------------------------------------|
| `id`            | UUID / PK        | Unique participant ID                         |
| `competition_id`| FK → competitions.id | Competition this participant is registered for |
| `user_id`       | FK → users.id    | User account for the participant             |
| `first_name`    | text             | Participant's first name                     |
| `last_name`     | text             | Participant's last name                      |
| `email`         | text             | Participant's email                          |
| `team_id`       | FK → teams.id / null | Team the participant belongs to (null for solo) |
| `is_solo`    | boolean          | Whether this is a solo participant          |
| `inserted_at`    | timestamp        | When added                                   |

#### `ascents`

| Field           | Type                | Notes                                     |
|-----------------|---------------------|-------------------------------------------|
| `id`            | UUID / PK           | Unique ascent ID                         |
| `competition_id`| FK → competitions.id| Competition where the ascent was recorded|
| `participant_id`| FK → participants.id| Participant who completed the ascent     |
| `route_id`      | FK → routes.id      | Route that was climbed                   |
| `team_id`       | FK → teams.id / null| Team of the participant (if applicable)  |
| `inserted_at`    | timestamp           | When the ascent was recorded             |

#### `users`

| Field            | Type             | Notes                                     |
|------------------|------------------|-------------------------------------------|
| `id`             | UUID / PK        | Unique user ID                            |
| `first_name`     | text             | User's first name                         |
| `last_name`      | text             | User's last name                          |
| `email`          | text             | User's email address                      |
| `hashed_password`| text             | Encrypted password                        |
| `confirmed_at`   | timestamp / null | When email was confirmed                  |
| `role`           | enum             | "user", "admin", or "moderator"           |
| `inserted_at`     | timestamp        | When added                                |
| `updated_at`     | timestamp        | Last updated                              |

#### `comp_vouchers`

| Field           | Type                | Notes                                     |
|-----------------|---------------------|-------------------------------------------|
| `id`            | UUID / PK           | Unique voucher ID                         |
| `email`         | text                | Email associated with the voucher         |
| `code`          | int                 | Voucher code                              |
| `code_used_at`  | timestamp / null    | When the voucher was used                 |
| `competition_id`| FK → competitions.id| Competition this voucher is for           |
| `participant_id`| FK → participants.id / null | Participant who used the voucher   |
| `inserted_at`    | timestamp           | When added                                |
| `updated_at`    | timestamp           | Last updated                              |

### 📊 Scoring Tables

#### `base_points`

| Field              | Type                | Notes                                     |
|--------------------|---------------------|-------------------------------------------|
| `id`               | UUID / PK           | Unique config ID                          |
| `competition_id`   | FK → competitions.id / null | Competition (null for global config) |
| `grade`            | text                | Climbing grade (e.g., "6A", "7B+")        |
| `points`           | int                 | Base points for the grade                 |
| `increment_factor` | float / null        | Optional increment factor                 |

#### `volume_bonus`

| Field               | Type                | Notes                                     |
|---------------------|---------------------|-------------------------------------------|
| `id`                | UUID / PK           | Unique config ID                          |
| `competition_id`    | FK → competitions.id / null | Competition (null for global config) |
| `bonus_increment`   | int                 | Number of ascents to trigger bonus        |
| `points_per_increment` | int              | Points awarded per increment              |

#### `unique_ascent_bonus`

| Field           | Type                | Notes                                       |
|-----------------|---------------------|---------------------------------------------|
| `id`            | UUID / PK           | Unique config ID                            |
| `competition_id`| FK → competitions.id / null | Competition (null for global config)|
| `bonus_factor`  | float               | Multiplier for unique ascents               |

#### `team_ascent_bonus`

| Field           | Type                | Notes                                       |
|-----------------|---------------------|---------------------------------------------|
| `id`            | UUID / PK           | Unique config ID                            |
| `competition_id`| FK → competitions.id / null | Competition (null for global config)|
| `team_size`     | int                 | Size of the team                            |
| `bonus_factor`  | float               | Bonus multiplier (e.g., 0.18 for 18%)       |

#### `master_grade_bonus`

| Field           | Type                | Notes                                       |
|-----------------|---------------------|---------------------------------------------|
| `id`            | UUID / PK           | Unique config ID                            |
| `competition_id`| FK → competitions.id / null | Competition (null for global config)|
| `bonus_factor`  | float               | Bonus factor for team with most ascents     |

#### `marathon_rankings`

| Field               | Type                | Notes                                   |
|---------------------|---------------------|----------------------------------------|
| `id`                | UUID / PK           | Unique ranking ID                      |
| `competition_id`    | FK → competitions.id| Competition for this ranking           |
| `team_id`           | FK → teams.id       | Team being ranked                      |
| `team_size`         | int                 | Number of members in team              |
| `base_score`        | float               | Base score from ascents                |
| `volume_bonus`      | float               | Bonus points for volume                |
| `unique_ascent_bonus` | float            | Bonus for unique routes                 |
| `team_ascent_bonus` | float               | Bonus based on team size               |
| `master_grade_bonus`| float               | Bonus for mastering grades             |
| `total_score`       | float               | Total unadjusted score                 |
| `normalized_score`  | float               | Score normalized for team size         |
| `rank`              | int                 | Final ranking position                 |
| `inserted_at`        | timestamp           | When calculated                        |
| `updated_at`        | timestamp           | Last updated                           |

#### `marathon_detailed_results`

| Field                | Type                | Notes                                  |
|----------------------|---------------------|----------------------------------------|
| `id`                 | UUID / PK           | Unique result ID                       |
| `competition_id`     | FK → competitions.id| Competition for this result            |
| `team_id`            | FK → teams.id       | Team being scored                      |
| `team_name`          | text                | Name of the team                       |
| `team_size`          | int                 | Number of members in team              |
| `routes`             | JSONB               | Detailed routes information            |
| `total_ascents`      | int                 | Total number of ascents by team        |
| `volume_bonus`       | float               | Bonus points for volume                |
| `team_completed_routes` | int             | Number of routes completed by team     |
| `team_unique_routes` | int                 | Number of unique routes climbed        |
| `master_grades`      | JSONB               | Master grades information              |
| `master_grade_bonus` | float               | Bonus for mastering grades             |
| `base_score`         | float               | Base score from ascents                |
| `team_ascent_bonus`  | float               | Bonus based on team size               |
| `unique_ascent_bonus`| float               | Bonus for unique routes                |
| `total_score`        | float               | Total unadjusted score                 |
| `normalized_score`   | float               | Score normalized for team size         |
| `inserted_at`         | timestamp           | When calculated                        |
| `updated_at`         | timestamp           | Last updated                           |

#### `boulder_beasts_rankings`

| Field           | Type                   | Notes                                   |
|-----------------|------------------------|----------------------------------------|
| `id`            | UUID / PK              | Unique ranking ID                      |
| `competition_id`| FK → competitions.id   | Competition for this ranking           |
| `participant_id`| FK → participants.id   | Participant being ranked               |
| `total_score`   | float                  | Total score                            |
| `top_5_routes`  | text[] / null          | Array of top 5 route names             |
| `top_5_routes_score` | float            | Score from top 5 routes                |
| `rank`          | int                    | Final ranking position                 |
| `inserted_at`    | timestamp              | When calculated                        |
| `updated_at`    | timestamp              | Last updated                           |

#### `competition_photos`

| Field          | Type                 | Notes                                   |
|----------------|----------------------|----------------------------------------|
| `id`           | UUID / PK            | Unique photo ID                        |
| `competition_id` | FK → competitions.id | Competition the photo belongs to      |
| `uploader_id`  | FK → participants.id | Participant who uploaded the photo     |
| `cloudinary_url` | text / null        | URL to the photo in Cloudinary         |
| `description`  | text / null          | Optional photo description             |
| `approved`     | boolean              | Whether the photo is approved          |
| `featured`     | boolean              | Whether the photo is featured          |
| `inserted_at`   | timestamp            | When uploaded                          |
| `updated_at`   | timestamp            | Last updated                           |

### 🔄 Entity Relationship Diagram

The following diagram illustrates the relationships between all database entities in the system, grouped by domain:

![Database Entity Relationship Diagram](docs/database/erd.png)

The diagram is organized into four main domains:
- **Bouldering Data** (blue): Crags, sectors, boulders, routes, and related data
- **Accounts** (orange): User management and authentication
- **Competition Management** (yellow): Competitions, teams, participants, and ascents
- **Scoring System** (green): Scoring configuration and competition results

Note the special relationship between Teams and Participants (marked in red), which represents the circular dependency handled by the named foreign key constraint for team captains.


## Database Implementation & Management

The project includes a collection of command-line scripts for database management located in the 
`database/management` directory. These scripts provide administrators with powerful tools to manage the 
database outside of the API endpoints.

### Core Database Scripts

1. **Database Initialization** (`init_db_all.py`):
   - Creates all database tables based on the SQLModel definitions
   - Optionally initializes mock competition data
   ```bash
   python -m database.management.init_db_all [--mock-comp]
   ```

2. **Database Reset** (`reset_db.py`):
   - Completely resets the database (drops and recreates all tables)
   - Provides options for reimporting boulder data and creating mock competitions
   ```bash
   python -m database.management.reset_db [--force] [--mock-comp] [--skip-boulder-import]
   ```

3. **Crag Data Management**:
   - `init_crag_core.py`: Imports boulder and route data from scraped JSON files
   - `init_crag_config.py`: Sets up configuration for crag-specific settings
   - `init_boulder_photos.py`: Re-uploads boulder photos to Cloudinary
   ```bash
   python -m database.management.init_crag_core [--file PATH] [--crag NAME]
   python -m database.management.init_boulder_photos [--crag NAME] [--skip-reset]
   ```

4. **Mock Competition Setup** (`init_mock_comp.py`):
   - Creates sample competition data for testing and development
   - Includes mock users, teams, participants, and ascents
   - Configures scoring parameters for realistic competition testing

### Database Management Workflow

These CLI tools complement the API endpoints by providing direct database management capabilities:

1. **Development Setup**:
   ```bash
   # Initialize database with test data
   python -m database.management.init_db_all --mock-comp
   ```

2. **Data Reset/Refresh**:
   ```bash
   # Force reset database and recreate with fresh mock data
   python -m database.management.reset_db --force --mock-comp
   ```

3. **Updating Boulder Data**:
   ```bash
   # Import latest boulder data after scraping
   python -m database.management.init_crag_core
   
   # Re-upload boulder photos to Cloudinary
   python -m database.management.init_boulder_photos
   ```

These tools are particularly useful for:
- Initial setup and deployment of the application
- Development and testing with controlled data
- Recovering from database inconsistencies
- Batch operations that would be cumbersome through the API

## 🕸️ Data Collection and Scraping

The Boulder Competition API includes a sophisticated web scraping system to collect climbing data from 27crags.com. This data collection pipeline forms the foundation of the competition platform by providing detailed information about crags, boulders, routes, and photos.

For detailed documentation of the scraping architecture and implementation, refer to [Scraper Documentation](scraper/README.md).