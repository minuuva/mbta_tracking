import io
import logging
import boto3
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import seaborn as sns
from botocore.exceptions import ClientError
from config import S3_BUCKET, AWS_REGION, DELAY_THRESHOLD_MIN

log = logging.getLogger(__name__)

def get_s3_client():
    return boto3.client("s3", region_name=AWS_REGION)

def update_csv(s3_client, record: dict) -> pd.DataFrame:
    """
    Download existing data.csv from S3, append the new record, and upload back.
    On the first run, it starts a fresh DataFrame with the new record.
    It returns the full updated DataFrame for use in plot generation.
    """
    try:
        obj = s3_client.get_object(Bucket=S3_BUCKET, Key="data.csv")
        df = pd.read_csv(io.BytesIO(obj["Body"].read()))
        log.info("Downloaded existing data.csv (%d rows)", len(df))
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            log.info("No existing data.csv, starting fresh")
            df = pd.DataFrame()
        else:
            log.error("S3 GetObject failed: %s", e)
            raise
    
    new_row = {
        "timestamp":         record["timestamp"],
        "route_id":          record["route_id"],
        "stop_id":           record["stop_id"],
        "direction_id":      record["direction_id"],
        "scheduled_arrival": record["scheduled_arrival"],
        "predicted_arrival": record["predicted_arrival"],
        "delay_minutes":     float(record["delay_minutes"]),
        "num_predictions":   record["num_predictions"],
        "status":            record["status"],
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    s3_client.put_object(
        Bucket=S3_BUCKET, Key="data.csv",
        Body=csv_buffer.getvalue(), ContentType="text/csv",
    )
    log.info("Uploaded data.csv to S3 (%d rows)", len(df))
    return df

def generate_and_upload_plot(s3_client, df: pd.DataFrame) -> None:
    """
    Generates a time-series delay plot and upload as plot.png to S3.
    Filters out NO_SERVICE records so overnight gaps appear as breaks
    in the line rather than misleading zero-delay points.
    """
    plot_df = df[df["status"] != "NO_SERVICE"].copy()

    if plot_df.empty:
        log.info("No service data points yet - skipping plot generation")
        return
    
    plot_df["timestamp"] = pd.to_datetime(plot_df["timestamp"])
    plot_df = plot_df.sort_values("timestamp")

    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(14, 6))
    sns.lineplot(
        data=plot_df, x="timestamp", y="delay_minutes",
        ax=ax, marker="o", markersize=4, linewidth=1.5,
    )
    ax.axhline(y=0, color="green", linestyle="--", alpha=0.7,
               label="On Time")
    ax.axhline(y=DELAY_THRESHOLD_MIN, color="red", linestyle="--",
               alpha=0.5, label=f"Delay Threshold ({DELAY_THRESHOLD_MIN} min)")
    ax.axhline(y=-DELAY_THRESHOLD_MIN, color="red", linestyle="--",
               alpha=0.5)
    ax.set_title(
        "MBTA Orange Line — Prediction Delay at Downtown Crossing (Southbound)",
        fontsize=14,
    )
    ax.set_xlabel("Time (UTC)", fontsize=12)
    ax.set_ylabel("Delay (minutes)", fontsize=12)
    ax.legend(loc="upper left")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    fig.autofmt_xdate(rotation=45)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    buf.seek(0)
    plt.close(fig)
    s3_client.put_object(
        Bucket=S3_BUCKET, Key="plot.png",
        Body=buf.getvalue(), ContentType="image/png",
    )
    log.info("Uploaded plot.png to S3")