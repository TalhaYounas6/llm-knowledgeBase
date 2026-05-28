import pika
import json
import requests
import os
import time
from dotenv import load_dotenv
from engine import generate_integration_plan
import concurrent.futures

load_dotenv(dotenv_path="../.env")

RABBITMQ_URL           = os.getenv("QUEUE_URL")
SERVER_URL             = os.getenv("SERVER_URL")
PROCESS_TIMEOUT_DURATION = 300  

print(f"Connecting to RabbitMQ: {RABBITMQ_URL}")


def callback(ch, method, properties, body):
    ticket           = json.loads(body)
    jobId            = ticket.get("jobId")
    originalFileName = ticket.get("original_filename")
    userKey          = ticket.get("userApiKey")
    relative_path    = ticket.get("filePath")
    file_path        = os.path.abspath(os.path.join("..", relative_path))

    # Context forwarded from watcher.py 
    schema_text = ticket.get("schemaText", "")
    index_text  = ticket.get("indexText",  "")
    log_tail    = ticket.get("logTail",    "")
   

    print(f"Pulled Job from QUEUE [ JobID: {jobId} - FileName: {originalFileName} ]")

    res = None
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                generate_integration_plan,
                file_path,
                userKey,
                originalFileName,
                schema_text,
                index_text,
                log_tail
            )
            plan = future.result(PROCESS_TIMEOUT_DURATION)

        # Send the structured plan back to the server
        # The server stores it. Watcher.py polls and executes it locally
        payload = {
            "status": "completed",
            "plan":   plan          # dict: note_filename, note_content, index_entry, cross_links
        }
        res = requests.put(f"{SERVER_URL}/wiki/internal/job/{jobId}", json=payload)

        if res.status_code == 200:
            print(f"Job completed successfully , plan sent to server for {originalFileName}")
         
        else:
            print(f"Job result rejected by server: {res.text}")

    except concurrent.futures.TimeoutError:
        print(f"Timeout: AI took too long for job {jobId}")
        requests.put(f"{SERVER_URL}/wiki/internal/job/{jobId}", json={"status": "failed"})

    except Exception as e:
        print(f"AI processing failed for job {jobId}: {e}")
        requests.put(f"{SERVER_URL}/wiki/internal/job/{jobId}", json={"status": "failed"})

    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)
        if os.path.exists(file_path):
            os.remove(file_path)
            print("Cleaned up temporary file")


def start_worker():
    print("AI worker starting up...")
    parameters = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(parameters)
    channel    = connection.channel()

    channel.queue_declare(queue="pdf_jobs", durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="pdf_jobs", on_message_callback=callback)

    print("Worker connected to RabbitMQ and waiting for jobs...")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("Stopping worker...")
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == "__main__":
    time.sleep(2)
    start_worker()