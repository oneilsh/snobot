"""
Pre-compute and cache the SQL and Vector databases for evaluation
This script initializes the databases and saves them to disk for faster loading
"""

import sys
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import database classes directly to avoid Streamlit warnings
from resources.sql_db import SqlDB
from resources.vec_db import VecDB

# Initialize database instances directly (bypassing Streamlit cache)
sql_db = SqlDB()
vec_db = VecDB()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def precompute_databases():
    """Pre-compute and cache both SQL and Vector databases"""
    
    logger.info("Starting database pre-computation...")
    
    try:
        # Initialize SQL database
        logger.info("Initializing SQL database...")
        sql_db_instance = sql_db
        logger.info("SQL database initialized and cached")
        
        # Initialize Vector database  
        logger.info("Initializing Vector database...")
        vec_db_instance = vec_db
        logger.info("✓ Vector database initialized and cached")
        
        # Test that they work
        logger.info("Testing databases...")
        
        # Test SQL database
        test_query = "SELECT COUNT(*) FROM concept LIMIT 1"
        result = sql_db_instance.run_query(test_query)
        logger.info(f"SQL database test query returned: {result[0][0]} concepts")
        
        # Test Vector database
        test_hits = vec_db_instance.query("diabetes", top_k=3)
        logger.info(f"Vector database test query returned {len(test_hits)} hits for 'diabetes'")
        
        logger.info("Database pre-computation completed successfully")
        logger.info("Databases are now cached and ready for evaluation")
        
    except Exception as e:
        logger.error(f"Database pre-computation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    precompute_databases()
