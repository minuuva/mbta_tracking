import logging
import boto3
from config import ROUTE_ID, STOP_ID, TABLE_NAME, AWS_REGION
from mbta_client import fetch_predictions, parse_predictions
from dynamo import get_previous, build_record, write_record
from storage import get_s3_client, update_csv, generate_and_upload_plot

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

def main():
    # defining resources
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(TABLE_NAME)
    s3_client = get_s3_client()

    # step 1: fetch and parse MBTA predictions
    try:
        api_response = fetch_predictions()
        prediction_data = parse_predictions(api_response)
    except Exception as e:
        log.warning("Failed to fetch/parse predictions: %s", e)
        prediction_data = None
    
    # step 2: build record and write to DynamoDB
    record = build_record(prediction_data)
    previous = get_previous(table)
    write_record(table, record)

    # step 3: append to CSV and regenerate plot on S3
    df = update_csv(s3_client, record)
    generate_and_upload_plot(s3_client, df)

    # Step 4: Log summary
    if record["status"] == "NO_SERVICE":
        log.info("%s | stop=%s | NO SERVICE | %s",
                 ROUTE_ID, STOP_ID, record["timestamp"])
    else:
        log.info(
            "%s | stop=%s | delay=%+.2f min | %s | sched=%s | pred=%s | predictions=%d",
            ROUTE_ID, STOP_ID, record["delay_minutes"],
            record["status"], record["scheduled_arrival"],
            record["predicted_arrival"], record["num_predictions"],
        )
if __name__ == "__main__":
    main()
