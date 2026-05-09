import pika
import json
import requests
import os
import time
from dotenv import load_dotenv
from engine import processDocument
import concurrent.futures
load_dotenv(dotenv_path="../.env")

RABBITMQ_URL= os.getenv("QUEUE_URL")
SERVER_URL= os.getenv("SERVER_URL")

print(f"Connecting to RABBIT MQ URL :{RABBITMQ_URL}")

PROCESS_TIMEOUT_DURATION = 90 
# 90 seconds

def callback(ch,method,properties,body):
    ticket = json.loads(body)
    jobId = ticket.get("jobId")
    originalFileName = ticket.get("original_filename")
    userKey = ticket.get("userApiKey")
    

    relative_file_path = ticket.get("filePath")
    file_path = os.path.abspath(os.path.join("..", relative_file_path))

    print(f"Pulled Job from QUEUE [ JobID: {jobId} - FileName: {originalFileName}]")

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(processDocument,file_path,userKey)

            markdown_result = future.result(PROCESS_TIMEOUT_DURATION)

            payload = {
                "status" : "completed",
                "markdown_result" : markdown_result
            }

            res = requests.put(f"{SERVER_URL}/wiki/internal/job/{jobId}", json=payload)
            if res.status_code == 200:
                print(f"Job completed Successfully")
            else:
                print(f"Job was not successful : {res.text}")
    except concurrent.futures.TimeoutError:
        print(f"AI took too long to generate an output for job: {jobId}")
        requests.put(f"{SERVER_URL}/wiki/internal/job/{jobId}", json = {
            "status" : "failed"
        })
    except Exception as e:
        print(f"AI processing failed for job {jobId} : {e}")
        requests.put(f"{SERVER_URL}/wiki/internal/job/{jobId}",json={
            "status" : "failed"
        })

        print(f"Server Response Code: {res.status_code}")
        print(f"Server Response Text: {res.text}")
    finally:
        ch.basic_ack(delivery_tag = method.delivery_tag);
        if(os.path.exists(file_path)):
            os.remove(file_path)        
            # Remove file after processing from server
            print("Cleaned up temporary file")

def start_worker():
        print("AI worker starting up...")

        parameters = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        channel.queue_declare(queue="pdf_jobs",durable= True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue="pdf_jobs",on_message_callback=callback)

        print("Worker connected to RabbitMQ and waiting for jobs...")

        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            print("Stopping Worker")
            channel.stop_consuming()      

        finally:
            connection.close()

if __name__ == "__main__":
        time.sleep(2) 
        start_worker()           

