# MBTA Orange Line Delay Tracker

A containerized data pipeline that tracks prediction delay on the MBTA Orange Line at Downtown Crossing (Southbound) every 30 minutes. Built for DS5220 Data Project 2.

## Architecture

- **Data Source:** [MBTA V3 API](https://api-v3.mbta.com) — real-time predictions vs scheduled arrivals
- **Persistence:** AWS DynamoDB (`mbta-tracking` table)
- **Visualization:** Evolving time-series plot published to S3 static website
- **Scheduling:** Kubernetes CronJob running on K3s (EC2)

## Pipeline

Each run:
1. Fetches predictions from the MBTA API
2. Computes delay (predicted arrival − scheduled arrival)
3. Writes the record to DynamoDB
4. Appends to `data.csv` on S3
5. Regenerates `plot.png` on S3

## Structure

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

## Plot URL

`http://mbtav3.s3-website-us-east-1.amazonaws.com/plot.png`
