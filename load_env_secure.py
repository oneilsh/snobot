"""
Environment loader that checks for secure deployment environment first,
then falls back to local .env file for development.
"""

import os
import dotenv

# Check if we're in a deployment environment (secure config exists)
SECURE_ENV_PATH = '/etc/snobot/.env'
LOCAL_ENV_PATH = '.env'

if os.path.exists(SECURE_ENV_PATH):
    # Production/deployment environment
    dotenv.load_dotenv(SECURE_ENV_PATH, override=True)
elif os.path.exists(LOCAL_ENV_PATH):
    # Development environment
    dotenv.load_dotenv(LOCAL_ENV_PATH, override=True)
else:
    # No .env file found - this is okay, environment variables might be set another way
    pass
