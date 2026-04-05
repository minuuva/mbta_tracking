import os

# MBTA API
MBTA_API_URL = "https://api-v3.mbta.com"
API_KEY      = os.environ.get("API_KEY", "")

# Target: Orange Line, Downtown Crossing, Southbound (toward Forest Hills)
ROUTE_ID = "Orange"
STOP_ID  = "place-dwnxg"
DIRECTION_ID = 0

# AWS Configuration
AWS_REGION = "us-east-1"
TABLE_NAME   = os.environ["DYNAMODB_TABLE"]
S3_BUCKET    = os.environ["S3_BUCKET"]

# Thresholds
# ---------------------------------------------------------------------------
# Predictions with abs(delay) >= this value (minutes) are flagged as DELAYED.
# Typical MBTA on-time performance standard is within 5 minutes of schedule.
DELAY_THRESHOLD_MIN = 5.0