import sys
import logging
import os

# Only enable debug logging if DEBUG environment variable is set to true
DEBUG_MODE = os.environ.get('DEBUG', 'false').lower() == 'true'

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout if DEBUG_MODE else open(os.devnull, 'w'))

# Set higher log levels for third-party libraries
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('google').setLevel(logging.WARNING)

# Create logger
logger = logging.getLogger('boulder-comp-api')

# Add filter to console output
console_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(console_handler)


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
    child_logger = logger.getChild(module_name)
    return child_logger


# Optional: Add filter to exclude logs from showing in the terminal
class ExcludeConsoleFilter(logging.Filter):

    def filter(self, record):
        return False


# Add filter to console output but allow Heroku to capture it
console_handler = logging.StreamHandler(sys.stdout)
# console_handler.addFilter(ExcludeConsoleFilter())
logger.addHandler(console_handler)

# Prevent the logger from propagating to the root logger
# This ensures logs don't show up in the console
# logger.propagate = False
