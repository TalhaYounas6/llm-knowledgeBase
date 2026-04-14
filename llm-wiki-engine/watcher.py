import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from brain import processDocument

INPUT_FOLDER = "./Raw_Sources"

os.makedirs(INPUT_FOLDER,exist_ok=True)

class FileDropHandler(FileSystemEventHandler):
    def on_created(self,event):
        if event.is_directory or os.path.basename(event.src_path).startswith('.'):
            return True
        
        time.sleep(1) # buffer
        print(f"Detected new file {os.path.basename(event.src_path)}")


        processDocument(event.src_path)



def startWatching():
        event_handler = FileDropHandler()
        observer = Observer()
        observer.schedule(event_handler,INPUT_FOLDER,recursive = True)
        observer.start()

        print("Watcher Started")
        print(f"Monitoring {INPUT_FOLDER} for changes.")
        print("Press CTRL+C to stop.")



        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()        

        

if __name__ == "__main__":
    startWatching()
    

