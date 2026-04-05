import logging
from datetime import datetime, timezone
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from config import ROUTE_ID, STOP_ID, DIRECTION_ID, DELAY_THRESHOLD_MIN

log = logging.getLogger(__name__)

def get_previous(table) -> dict | None:
    """
    We return the most recent stored record for this route, or None on first run.
    The function uses ScanIndexForward=False to sort by timestamp descending, so
    Limit=1 gives us the latest entry without scanning the full partition.
    """
    try:
        resp = table.query(
            KeyConditionExpression=Key("route_id").eq(ROUTE_ID),
            ScanIndexForward=False,
            Limit=1,
        )
        items = resp.get("Items", [])
        return items[0] if items else None
    except Exception as e:
        log.error("DynamoDB query failed: %s", e)
        raise

def build_record(prediction_data: dict | None) -> dict:
    """Build a DynamoDB-ready record from parsed prediction data.
    If prediction_data is None (no service / API failure), the record
    is stored with status NO_SERVICE so overnight gaps are visible in the data.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if prediction_data is None:
        return {
            "route_id": ROUTE_ID,
            "timestamp": now,
            "stop_id": STOP_ID,
            "direction_id": DIRECTION_ID,
            "scheduled_arrival": "N/A",
            "predicted_arrival": "N/A",
            "delay_minutes": Decimal("0"),
            "num_predictions": 0,
            "status": "NO_SERVICE",
        }

    delay = prediction_data["delay_minutes"]
    status = "DELAYED" if abs(delay) >= DELAY_THRESHOLD_MIN else "ON_TIME"

    return {
        "route_id": ROUTE_ID,
        "timestamp": now,
        "stop_id": STOP_ID,
        "direction_id": DIRECTION_ID,
        "scheduled_arrival": prediction_data["scheduled_arrival"],
        "predicted_arrival": prediction_data["predicted_arrival"],
        "delay_minutes": Decimal(str(delay)),
        "num_predictions": prediction_data["num_predictions"],
        "status": status,
    }

def write_record(table, record: dict) -> None:
    """ Write a record to DynamoDB. Raise on failure."""
    try:
        table.put_item(Item=record)
        log.info("Wrote record to DynamoDB: %s | %s", record["route_id"], record["timestamp"])
    except Exception as e:
        log.error("DynamoDB put_item failed: %s", e)
        raise