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

## Canvas Quiz

**1. Which data source you chose and why.**

I chose the MBTA V3 API, which provides real-time predictions and schedules for Boston's transit system. I selected it because it directly relates to transportation engineering, which is an interest of mine. Specifically, I'm tracking prediction delay (the difference between predicted and scheduled arrival times) on the Orange Line at Downtown Crossing. The API is well-documented, returns JSON, offers a free API key with generous rate limits (1,000 requests/minute), and updates continuously during service hours, making it ideal for a scheduled data pipeline collecting every 30 minutes.

**2. What you observe in the data — any patterns, spikes, or surprises over the 72-hour window.**

Over the 72-hour window, a few clear patterns emerged. On 04/03, delays were mostly positive (trains arriving 1–4 minutes late), which aligns with typical weekday service under normal load. However, starting around 04/04 midday, the delay values shifted sharply negative, reaching as low as -11 minutes, meaning trains were predicted to arrive significantly earlier than scheduled. This is surprising and likely indicates schedule adjustments, short-turns, or trains running ahead of timetable during lighter ridership periods. The overnight gaps (roughly 1–5 AM ET each night) are visible as breaks in the line where no service was running. One notable spike occurred on the evening of 04/05 with a drop to nearly -12 minutes, suggesting an unusual service deviation. Overall, the data reveals that the Orange Line does not simply run "late"; it oscillates between early and late, with the magnitude of early arrivals being larger than expected.

**3. How Kubernetes Secrets differ from plain environment variables and why that distinction matters.**

Plain environment variables are defined in cleartext directly in the CronJob YAML file. This means anyone with access to the manifest can read them. Kubernetes Secrets are stored separately and are base64-encoded at rest. They are injected into the pod at runtime and referenced by name in the YAML, so the actual sensitive value never appears in any file on disk, in version control, or in the container image. This matters because API keys, passwords, and tokens should never be exposed in source code or configuration files where they could be leaked or accidentally committed.

**4. How your CronJob pods gain permission to read/write to AWS services without credentials appearing in any file.**

The EC2 instance has an IAM role (dp2-mbta-ec2-role) attached to it as an instance profile. When a pod runs on that instance, the AWS SDK (boto3) automatically discovers temporary credentials from the EC2 instance metadata service (IMDS) via the attached role. These credentials are short-lived, automatically rotated, and never written to any file: no access keys or secret keys appear in the YAML, Docker image, or Python code. The pod logs confirm this with the line Found credentials from IAM Role: dp2-mbta-ec2-role.

**5. One thing you would do differently if you were building this pipeline for a real production system.**

I would add monitoring and alerting. For example, I would integrate with CloudWatch to notify the team when a CronJob pod fails, when DynamoDB writes an error out, or when no data has been collected for an unexpected period. The current pipeline fails silently; in production, you need to know immediately when the pipeline breaks so you can respond before data gaps grow too large. I would also set up a CI/CD pipeline to automatically build and push the container image on each commit, rather than building and pushing manually.
