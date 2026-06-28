import json
import os
import time
import requests
import concurrent.futures
import functools
import boto3
import pika
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv
from engine import generate_integration_plan

load_dotenv(dotenv_path="../.env")

RABBITMQ_URL = os.getenv("QUEUE_URL")
SERVER_URL = os.getenv("SERVER_URL")
PROCESS_TIMEOUT_DURATION = 300  
CONCURRENT_LIMIT = 5  

print(f"Connecting to RabbitMQ")

# shared global ThreadPoolExecutor 
executor = concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_LIMIT)


def safe_ack(ch, delivery_tag):
    
    try:
        ch.basic_ack(delivery_tag=delivery_tag)
    except Exception as e:
        print(f"Failed to acknowledge message thread-safely: {e}")


AWS_REGION = os.getenv("AWS_REGION")
s3 = boto3.client("s3", region_name=AWS_REGION)



executor = concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_LIMIT)


def safe_ack(ch, delivery_tag):
    try:
        ch.basic_ack(delivery_tag=delivery_tag)
    except Exception as e:
        print(f"Failed to acknowledge message thread-safely: {e}")


def delete_s3_object(bucket, key):
    if not bucket or not key:
        return

    try:
        s3.delete_object(Bucket=bucket, Key=key)
        print(f"Deleted S3 object: s3://{bucket}/{key}")
    except Exception as e:
        print(f"Failed to delete S3 object s3://{bucket}/{key}: {e}")


def process_job_async(ch, connection, method, ticket):
    jobId = ticket.get("jobId")
    originalFileName = ticket.get("original_filename")
    userKey = ticket.get("userApiKey")
    s3_bucket = ticket.get("s3Bucket")
    s3_key = ticket.get("s3Key")

    schema_text = ticket.get("schemaText", "")
    index_text = ticket.get("indexText", "")
    log_tail = ticket.get("logTail", "")

    print(f" Processing Job [ JobID: {jobId} - FileName: {originalFileName} ]")

    backend_updated = False

    def report_progress(stage, stage_message):
        try:
            res = requests.put(
                f"{SERVER_URL}/wiki/internal/job/{jobId}",
                json={
                    "status": "processing",
                    "stage": stage,
                    "stage_message": stage_message,
                },
                timeout=10,
            )

            if res.status_code != 200:
                print("Server is busy at the moment. Please try again later.")
                print(f" Progress update rejected by server for job {jobId}: {res.text}")
        except Exception as net_err:
            print("Server is busy at the moment. Please try again later.")
            print(f" Could not send progress update for job {jobId}: {net_err}")

    try:
        report_progress("starting", f"Starting ingest for {originalFileName}")

        plan = generate_integration_plan(
            s3_bucket,
            s3_key,
            userKey,
            originalFileName,
            schema_text,
            index_text,
            log_tail,
            progress_callback=report_progress,
        )

        payload = {
            "status": "completed",
            "plan": plan,
        }

        try:
            res = requests.put(
                f"{SERVER_URL}/wiki/internal/job/{jobId}",
                json=payload,
                timeout=15,
            )

            if res.status_code == 200:
                backend_updated = True
                print(f" Job {jobId} completed successfully for {originalFileName}")
            else:
                print("Server is busy at the moment. Please try again later.")
                print(f" Job {jobId} result rejected by server: {res.text}")

        except Exception as net_err:
            print("Server is busy at the moment. Please try again later.")
            print(f" Could not notify backend server of success for job {jobId}: {net_err}")

    except Exception as e:
        print(f" AI processing failed for job {jobId}: {e}")

        try:
            payload = {
                "status": "failed",
                "stage": "failed",
                "stage_message": f"Job failed for {originalFileName}",
                "error": str(e),
            }

            res = requests.put(
                f"{SERVER_URL}/wiki/internal/job/{jobId}",
                json=payload,
                timeout=15,
            )

            if res.status_code == 200:
                backend_updated = True
            else:
                print("Server is busy at the moment. Please try again later.")
                print(f" Job {jobId} failure update rejected by server: {res.text}")

        except Exception as net_err:
            print("Server is busy at the moment. Please try again later.")
            print(f" Could not notify backend server of failure for job {jobId}: {net_err}")

    finally:
        if backend_updated:
            delete_s3_object(s3_bucket, s3_key)

            connection.add_callback_threadsafe(
                functools.partial(safe_ack, ch, method.delivery_tag)
            )
        else:
            print(f"Leaving job {jobId} unacked so RabbitMQ can redeliver it later.")

def callback(ch, method, properties, body):
    
    connection = ch.connection
    ticket = json.loads(body)
    
    executor.submit(process_job_async, ch, connection, method, ticket)


def start_worker():
    print(f"AI worker starting up with concurrency limit of {CONCURRENT_LIMIT}...")
    parameters = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    channel.queue_declare(queue="pdf_jobs", durable=True)
    
    channel.basic_qos(prefetch_count=CONCURRENT_LIMIT)
    channel.basic_consume(queue="pdf_jobs", on_message_callback=callback)

    print("Worker connected to RabbitMQ and waiting for jobs...")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("Stopping worker...")
        channel.stop_consuming()
    finally:
        connection.close()
        # shut down the pool 
        executor.shutdown(wait=False)


if __name__ == "__main__":
    time.sleep(2)
    start_worker()
