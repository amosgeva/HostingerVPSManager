"""Application-wide constants.

Centralised here so timing/limits/URLs can be changed in one place.
"""

# Refresh interval (UI auto-refresh of server data)
DEFAULT_REFRESH_SECONDS = 30
MIN_REFRESH_SECONDS = 10
MAX_REFRESH_SECONDS = 300

# HTTP client
API_BASE_URL = "https://developers.hostinger.com"
API_TIMEOUT_SECONDS = 30
API_MAX_RETRIES = 3
API_BACKOFF_FACTOR = 0.5  # exponential backoff base (0.5, 1.0, 2.0, 4.0...)
API_RETRY_STATUSES = (429, 500, 502, 503, 504)

# Metrics
METRIC_AVERAGING_HOURS = 24
