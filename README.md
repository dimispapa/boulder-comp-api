# Boulder Competition API

API service for the Bouldering Festival Competition app, providing score calculation and 27crags data scraping capabilities.

## Features

- **Score Calculation**: Calculate competition scores based on team ascents.
- **Leaderboard Generation**: Create and update real-time leaderboards.
- **27crags Scraping**: Scrape boulder data from 27crags to update competition data.
- **Background Task Processing**: Using Celery for asynchronous task execution.
- **Supabase Integration**: Connect to the main app's Supabase database.

## Tech Stack

- **FastAPI**: Modern, high-performance web framework for building APIs
- **Celery**: Asynchronous task queue for background processing
- **Redis**: Message broker for Celery
- **Supabase**: Database integration with the main app
- **Python 3.12+**: Core programming language
- **Docker**: Container platform for consistent development and deployment

## Project Structure

```
boulder-comp-api/
├── api/                  # FastAPI endpoints
│   └── routes/           # Route handlers (scraper, scoring)
├── scraper/              # 27crags scraping logic
├── scoring/              # Score calculation logic
├── tasks/                # Celery background tasks
├── utils/                # Common utilities/helpers
├── tests/                # Unit/integration tests
├── main.py               # FastAPI app entry point
├── .env                  # Environment variables (not committed)
├── docker-compose.yml    # Docker Compose configuration
├── Dockerfile            # Docker configuration for FastAPI app
├── Dockerfile.celery     # Docker configuration for Celery worker
├── requirements.txt      # Dependencies
├── heroku.yml            # Heroku container deployment configuration
├── Procfile              # Heroku process definitions (alternative to heroku.yml)
├── app.json              # Heroku app configuration
└── .dockerignore         # Files to exclude from Docker builds
```

## Setup and Installation

### Option 1: Using Docker (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/boulder-comp-api.git
   cd boulder-comp-api
   ```

2. Copy the example environment file and configure:
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials
   ```

3. Build and start the Docker containers:
   ```bash
   docker-compose up -d
   ```

   This will start:
   - FastAPI application (accessible at http://localhost:8000)
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

4. Copy the example environment file and configure:
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials
   ```

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

## API Endpoints

### Scraper API

- `POST /api/scraper/scrape` - Start a scraping task for 27crags data
- `GET /api/scraper/task/{task_id}` - Check status of a scraping task

### Scoring API

- `POST /api/scoring/calculate` - Calculate scores for a competition
- `GET /api/scoring/task/{task_id}` - Check status of a calculation task
- `GET /api/scoring/leaderboard/{competition_id}` - Get competition leaderboard

## Development

- Follow PEP8 style guidelines
- Write tests for new features
- Add documentation for API endpoints

## Deployment

This API is designed to be deployed using Docker:

### Heroku

1. Install the Heroku CLI and login:
   ```bash
   brew install heroku
   heroku login
   ```

2. Create a new Heroku app:
   ```bash
   heroku create your-app-name
   ```

3. Add Redis add-on:
   ```bash
   heroku addons:create heroku-redis:hobby-dev -a your-app-name
   ```

4. Set environment variables:
   ```bash
   heroku config:set SUPABASE_URL=your_url
   heroku config:set SUPABASE_KEY=your_key
   # Add other environment variables
   ```

5. Enable the container stack:
   ```bash
   heroku stack:set container -a your-app-name
   ```

6. Login to Heroku Container Registry:
   ```bash
   heroku container:login
   ```

7. Deploy the app:
   ```bash
   git push heroku main
   ```

8. Scale dynos:
   ```bash
   heroku ps:scale web=1 worker=1
   ```

9. View logs:
   ```bash
   heroku logs --tail
   ```

#### Custom Domain and SSL

1. Add your custom domain to Heroku:
   ```bash
   heroku domains:add www.yourdomain.com -a your-app-name
   ```

2. Verify domain ownership and configure DNS:
   - Add the provided DNS target as a CNAME record for your domain
   - For apex domains, use DNS provider's ALIAS/ANAME record or Heroku's DNS service

3. Enable Automatic Certificate Management (ACM) for SSL:
   ```bash
   heroku certs:auto:enable -a your-app-name
   ```

4. Check certificate status:
   ```bash
   heroku certs:auto -a your-app-name
   ```

#### Troubleshooting

- Restart dynos:
  ```bash
  heroku dyno:restart -a your-app-name
  ```

- Check running dynos:
  ```bash
  heroku ps -a your-app-name
  ```

- View detailed logs:
  ```bash
  heroku logs --tail --source app -a your-app-name
  ```

#### Monitoring and Logging

1. Set up application monitoring with Heroku add-ons:
   ```bash
   # New Relic for application performance monitoring
   heroku addons:create newrelic:wayne -a your-app-name
   
   # Papertrail for log management
   heroku addons:create papertrail:choklad -a your-app-name
   ```

2. Configure custom metrics with Heroku metrics:
   ```bash
   # Enable Heroku metrics
   heroku labs:enable runtime-metrics -a your-app-name
   
   # View metrics
   heroku metrics -a your-app-name
   ```

3. Set up alerts for important events:
   ```bash
   # Using Librato for metric alerts
   heroku addons:create librato:development -a your-app-name
   ```

4. Access application metrics dashboards:
   ```bash
   # Open metrics dashboard
   heroku addons:open librato -a your-app-name
   
   # Open logs dashboard
   heroku addons:open papertrail -a your-app-name
   ```

### Docker and Container Best Practices

- **Environment Variables**: Always use environment variables for configuration (credentials, URLs, etc.) instead of hardcoding values
- **Container Images**: Use specific version tags for base images (e.g., `python:3.12-slim` instead of `python:latest`)
- **Image Cleanup**: Periodically clean up unused images to save disk space:
  ```bash
  docker image prune -a
  ```
- **Health Checks**: Consider adding health checks to your containers to ensure they're running correctly
- **Volumes for Persistent Data**: Use Docker volumes for any data that needs to persist between container restarts
- **Network Security**: Configure container networks to only expose necessary ports
- **Resource Limits**: Set memory and CPU limits for containers in production environments

## License

This project is licensed under the MIT License - see the LICENSE file for details.
