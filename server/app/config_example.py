"""
Example usage of the Settings configuration.

This file demonstrates how to properly use settings throughout the application.
"""

from app.config import get_settings, get_test_settings

# Get settings instance (cached)
settings = get_settings()

# Access non-sensitive values directly
print(f"Environment: {settings.environment}")
print(f"Log Level: {settings.log_level}")
print(f"API Prefix: {settings.api_v1_prefix}")

# Access sensitive values using get_secret_value()
db_url = settings.database_url.get_secret_value()
redis_url = settings.redis_url.get_secret_value()
secret_key = settings.secret_key.get_secret_value()
jina_key = settings.jina_api_key.get_secret_value()

# Use helper properties
if settings.is_production:
    print("Running in production mode")
elif settings.is_local:
    print("Running in local development mode")

# For testing, use get_test_settings()
test_settings = get_test_settings()
test_db_url = test_settings.database_url.get_secret_value()
print(f"Test database: {test_db_url}")
