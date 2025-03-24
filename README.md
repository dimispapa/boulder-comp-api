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
- **Python 3.9+**: Core programming language

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
└── requirements.txt      # Dependencies
```

## Setup and Installation

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

## Running the API

1. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```

2. Start the Celery worker:
   ```bash
   celery -A tasks worker --loglevel=info
   ```

3. Access the API documentation:
   - Open `http://localhost:8000/docs` in your browser

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

This API is designed to be deployed on Heroku.

1. Create a Heroku app
2. Set up the Redis add-on
3. Configure environment variables
4. Deploy from GitHub

## License

This project is licensed under the MIT License - see the LICENSE file for details.
