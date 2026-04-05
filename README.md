# MBTA Orange Line Delay Tracker

A containerized data pipeline that tracks prediction delay on the MBTA Orange Line at Downtown Crossing (Southbound) every 30 minutes. Built for DS5220 Data Project 2.

## Data Source

This project uses the [MBTA V3 API](https://api-v3.mbta.com), the official REST API for the Massachusetts Bay Transportation Authority (Boston's regional transit system). The API provides real-time GTFS predictions and static schedule data in JSON:API format. Specifically, the pipeline queries the `/predictions` endpoint with the associated `/schedule` sideload for the **Orange Line** at **Downtown Crossing** (`place-dwnxg`), **Southbound** (direction 0, toward Forest Hills). The API is free to use with a registered key (1,000 requests/minute) and updates continuously during service hours (~5 AM–1 AM ET).

## Scheduled Process

A Kubernetes CronJob (`mbta-job.yaml`) triggers a containerized Python application every 30 minutes. On each run, the application:

1. **Fetches** upcoming predicted arrivals from the MBTA API, along with their corresponding scheduled arrival times.
2. **Computes delay** as the difference between the predicted and scheduled arrival for the next upcoming train (in minutes). Positive values indicate the train is running late; negative values indicate it is running early.
3. **Classifies** the data point as `ON_TIME` (delay under 5 minutes), `DELAYED` (delay of 5+ minutes), or `NO_SERVICE` (overnight hours when no predictions are available).
4. **Persists** the record to an AWS DynamoDB table (`mbta-tracking`) with `route_id` as the partition key and `timestamp` as the sort key.
5. **Appends** the record to a cumulative `data.csv` file stored in an S3 static website bucket.
6. **Generates** an updated time-series plot (`plot.png`) using seaborn/matplotlib and uploads it to the same S3 bucket.

The pipeline runs on a K3s (lightweight Kubernetes) cluster hosted on an AWS EC2 instance. AWS permissions are provided through an IAM instance profile (no credentials in code), and the MBTA API key is injected via a Kubernetes Secret.

## Output Data and Plot

**`data.csv`** — A cumulative CSV file with one row per pipeline run. Columns include: `timestamp` (UTC), `route_id`, `stop_id`, `direction_id`, `scheduled_arrival`, `predicted_arrival`, `delay_minutes`, `num_predictions` (how many upcoming predictions existed at query time), and `status` (ON_TIME / DELAYED / NO_SERVICE). Over 72 hours at 30-minute intervals, the file contains 144+ rows.

**`plot.png`** — A time-series line chart showing prediction delay (in minutes) over the full collection window. The green dashed line marks on-time (0 minutes), and red dashed lines mark the ±5-minute delay threshold. NO_SERVICE overnight records are filtered out so gaps in the line reflect periods when the MBTA was not operating. The plot reveals daily patterns such as rush-hour delay spikes and overnight service gaps.

- **Plot URL:** `http://mbtav3.s3-website-us-east-1.amazonaws.com/plot.png`
- **Data URL:** `http://mbtav3.s3-website-us-east-1.amazonaws.com/data.csv`

## Repository Structure

```
mbta-delay/          # containerized application
  app.py             # entry point
  config.py          # configuration and environment variables
  mbta_client.py     # MBTA API fetch and parse
  dynamo.py          # DynamoDB read/write
  storage.py         # S3 CSV and plot operations
  Dockerfile
  requirements.txt
mbta-job.yaml        # Kubernetes CronJob manifest
```
