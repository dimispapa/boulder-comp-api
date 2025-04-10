import sys
import logging
import os
from logging.handlers import TimedRotatingFileHandler

# Only enable debug logging if DEBUG environment variable is set to true
DEBUG_MODE = os.environ.get('DEBUG', 'false').lower() == 'true'

# Define the log level based on DEBUG mode
LOG_LEVEL = logging.DEBUG if DEBUG_MODE else logging.INFO


# Configure the root logger only once
def setup_logging():
    # Get the root logger
    root_logger = logging.getLogger()

    # Clear any existing handlers to prevent duplication
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

    # Configure a single handler for the root logger
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(LOG_LEVEL)

    # Configure a rotating file handler that creates a new log file each day
    os.makedirs('logs', exist_ok=True)
    log_file_path = 'logs/app.log'

    # Use TimedRotatingFileHandler instead of FileHandler
    file_handler = TimedRotatingFileHandler(
        log_file_path,
        when='midnight',     # Rotate at midnight each day
        interval=1,          # One day per file
        backupCount=7,       # Keep logs for last 7 days
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)  # Set to DEBUG to capture everything
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Set higher log levels for third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('google').setLevel(logging.WARNING)
    logging.getLogger('celery').setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # Prevent propagation for the celery logger to avoid duplication
    celery_logger = logging.getLogger('celery')
    celery_logger.propagate = False

    # Create our application logger
    app_logger = logging.getLogger('boulder-comp-api')
    app_logger.setLevel(LOG_LEVEL)
    # Allow propagation to root since we're using root handlers
    app_logger.propagate = True

    return app_logger


# Create a single logger instance for the application
logger = setup_logging()


# Function to get module-specific logger that inherits from main logger
def get_logger(module_name):
    """
    Get a logger for a specific module that inherits settings
    from the main logger.

    Args:
        module_name (str): Name of the module (typically __name__)

    Returns:
        logging.Logger: A logger configured with the main logger's settings
    """
    module_logger = logging.getLogger(f'boulder-comp-api.{module_name}')
    # Set level directly to ensure it's respected
    module_logger.setLevel(LOG_LEVEL)
    return module_logger
