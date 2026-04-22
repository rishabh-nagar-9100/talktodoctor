"""
Supabase Database Client
Handles connection to the Supabase PostgreSQL database.
"""
import os
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

from typing import Optional

logger = logging.getLogger(__name__)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # Use Service Role Key for backend

# Initialize the client (lazy-loaded if keys are missing to prevent crash during development)
supabase: Optional[Client] = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("✅ Supabase client initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase client: {e}")
else:
    logger.warning("⚠️ SUPABASE_URL or SUPABASE_KEY not found in environment. Database operations will fail.")

def get_db() -> Client:
    """Get the active Supabase client instance."""
    if not supabase:
        raise ConnectionError("Supabase client is not initialized. Check your .env file.")
    return supabase
