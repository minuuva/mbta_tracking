import logging
from datetime import datetime
import requests
from config import MBTA_API_URL, API_KEY, ROUTE_ID, STOP_ID, DIRECTION_ID

log = logging.getLogger(__name__)

def fetch_predictions() -> dict:
    """
    We call the MBTA V3 predictions endpoint with the associated schedule included
    and return the raw JSON:API response dict. This function raises requests.HTTPError
    on non-2xx status codes.
    """
    params = {
        "filter[stop]": STOP_ID,
        "filter[route]": ROUTE_ID,
        "filter[direction_id]": DIRECTION_ID,
        "include": "schedule",
        "sort": "arrival_time",
    }
    headers = {"x-api-key": API_KEY} if API_KEY else {}

    resp = requests.get(f"{MBTA_API_URL}/predictions", params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()

def parse_predictions(api_response: dict) -> dict | None:
    """
    Extracts delay info from the first prediction that has a matching schedule.
    Walks the predictions list in arrivial time order and finds the first one
    with both a predicted arrival_time and a linked schedule arrival_time.
    Returns a dict with delay info, or None if no usable prediction exists like
    when it is overnight and no train runs.
    """
    predictions = api_response.get("data", [])
    included    = api_response.get("included", [])

    # lookup of schedule id -> schedule attributes from the JSON:API "included" sideload
    # so we can match each prediction to its scheduled time
    schedule_map = {}
    for item in included:
        if item["type"] == "schedule":
            schedule_map[item["id"]] = item["attributes"]
    
    for pred in predictions:
        pred_arrival = pred["attributes"].get("arrival_time")
        if not pred_arrival:
            continue

        # follow the prediction -> schedule relationship
        schedule_rel = (pred.get('relationships', {})
                            .get('schedule', {})
                            .get('data', {}))
        
        if not schedule_rel:
            continue

        sched_attrs = schedule_map.get(schedule_rel["id"])
        if not sched_attrs or not sched_attrs.get("arrival_time"):
            continue
        
        sched_arrival = sched_attrs['arrival_time']

        pred_dt = datetime.fromisoformat(pred_arrival)
        sched_dt = datetime.fromisoformat(sched_arrival)
        delay_minutes = round((pred_dt - sched_dt).total_seconds() / 60.0, 2)
        
        log.debug("Matched prediction %s -> schedule %s | delay=%.2f min",
                  pred["id"], schedule_rel["id"], delay_minutes)
        return {
            "predicted_arrival": pred_arrival,
            "scheduled_arrival": sched_arrival,
            "delay_minutes": delay_minutes,
            "num_predictions": len(predictions),
        }
    log.info("No predictions with matching schedules found (likely no service)")
    return None