import os
from supabase import create_client, Client
from dotenv import load_dotenv
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get Supabase credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Verify credentials exist
if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("Supabase credentials not found in environment variables. "
                   "Using placeholder values for development.")
    # Use placeholder values for development
    SUPABASE_URL = "https://your-project.supabase.co"
    SUPABASE_KEY = "your-api-key"


def get_supabase_client() -> Client:
    """
    Get a Supabase client instance with the configured credentials.
    
    Returns:
        Client: A Supabase client instance.
    """
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return client
    except Exception as e:
        logger.error(f"Error creating Supabase client: {str(e)}")
        raise


# Initialize a global client for reuse
supabase_client = get_supabase_client()
