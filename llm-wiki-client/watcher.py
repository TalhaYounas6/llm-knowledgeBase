import os
import time
import json
import requests
import getpass
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- CONFIGURATION ---
SERVER_URL = "http://localhost:3000"
CONFIG_FILE = "config.json"
INPUT_FOLDER = "./Raw_Sources"
OUTPUT_FOLDER = "./Wiki_Notes"

# Ensure both directories exist
os.makedirs(INPUT_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- HELPER FUNCTIONS ---
def save_local_key(api_key):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"api_key": api_key}, f)

def get_local_key():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            return data.get("api_key")
    return None

def verify_token(api_key):
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        res = requests.get(f"{SERVER_URL}/user/status", headers=headers)
        if res.status_code == 200:
            print(f"Authenticated! Daily Quota: {res.json().get('usage')}")
            return True
        return False
    except requests.exceptions.ConnectionError:
        print("Check your internet connection.")
        exit(1)

# --- POLLING LOGIC ---
def poll_for_result(job_id, api_key, original_filename):
    print(f"Waiting for AI to process '{original_filename}'...")
    
    headers = {'Authorization': f'Bearer {api_key}'}
    
    while True:
        try:
            # Tap the server on the shoulder
            res = requests.get(f"{SERVER_URL}/wiki/job/{job_id}", headers=headers)
            
            if res.status_code == 200:
                job_data = res.json()
                status = job_data.get('status')
                
                if status == 'completed':
                    print(f" AI finished processing '{original_filename}'!")
                    
                    # 1. Grab the markdown text
                    markdown_text = job_data.get('markdown_content', '')
                    
                    # 2. Create the new filename (change .pdf to .md)
                    base_name = os.path.splitext(original_filename)[0]
                    new_filepath = os.path.join(OUTPUT_FOLDER, f"{base_name}.md")
                    
                    # 3. Save it into the Wiki Notes folder
                    with open(new_filepath, "w", encoding="utf-8") as f:
                        f.write(markdown_text)
                        
                    print(f"Saved to {new_filepath}\n")
                    break 
                    
                elif status == 'failed':
                    print(f" AI failed to process '{original_filename}'.")
                    break
                
                # If status is 'pending' or 'processing', ijust wait silently
                
        except requests.exceptions.ConnectionError:
            print("Lost connection to server while waiting...")
            
        # Wait 5 seconds before asking the server again
        time.sleep(5) 

# --- MENU ACTIONS ---
def action_login():
    print("\n--- LOGIN ---")
    
    # 1. Try Auto-Login first
    local_key = get_local_key()
    if local_key:
        print("Found saved session. Verifying...")
        if verify_token(local_key):
            return local_key
        else:
            print("Saved session expired or invalid. Please log in manually.")

    # 2. Manual Login Fallback
    email = input("Email: ")
    password = getpass.getpass("Password: ") 

    try:
        response = requests.post(f"{SERVER_URL}/auth/login", json={"email": email, "password": password})
        if response.status_code == 200:
            api_key = response.json().get("apiKey")
            save_local_key(api_key)
            print("Login successful! Credentials saved.")
            return api_key
        else:
            print(f"Login failed: {response.json().get('message')}")
            return None
    except requests.exceptions.ConnectionError:
        print("Could not connect to the server.")
        return None

def action_register():
    print("\n--- REGISTER ---")
    username = input("Username: ")
    email = input("Email: ")
    password = getpass.getpass("Password: ")
    
    custom_key = getpass.getpass("Enter API Key (It is recommended to get your own free Gemini api key from google studio): ")
    
    payload = {"username": username, "email": email, "password": password}
    if custom_key.strip():
        payload["customLLMKey"] = custom_key.strip()

    try:
        response = requests.post(f"{SERVER_URL}/auth/register", json=payload)
        if response.status_code == 201:
            api_key = response.json().get("apiKey")
            save_local_key(api_key)
            print("Account created successfully! Credentials saved.")
            return api_key
        else:
            print(f"Registration failed: {response.json().get('message')}")
            return None
    except requests.exceptions.ConnectionError:
        print("Could not connect to the server.")
        return None

def action_change_key():
    print("\n--- CHANGE CUSTOM LLM KEY ---")
    print("Please verify your account first.")
    email = input("Email: ")
    password = getpass.getpass("Password: ")

    try:
        # 1. Login to get the API Key 
        login_res = requests.post(f"{SERVER_URL}/auth/login", json={"email": email, "password": password})
        
        if login_res.status_code != 200:
            print("Invalid email or password.")
            return None
            
        api_key = login_res.json().get("apiKey")
        save_local_key(api_key) # Refresh 
        
        # 2. Prompt for the new custom key
        new_custom_key = input("Enter your new custom Key: ")
        
        # 3. Hit the update route
        headers = {"Authorization": f"Bearer {api_key}"}
        update_res = requests.put(f"{SERVER_URL}/user/key", json={"customKey": new_custom_key.strip()}, headers=headers)
        
        if update_res.status_code == 200:
            print(f"{update_res.json().get('message')}")
            return api_key
        else:
            print(f"Failed to update key: {update_res.json().get('message')}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("Cannot reach the server.")
        return None

# --- FILE WATCHER LOGIC ---
class FileDropHandler(FileSystemEventHandler):
    def __init__(self, api_key):
        self.api_key = api_key

    def on_created(self, event):
        if event.is_directory or os.path.basename(event.src_path).startswith('.'):
            return

        time.sleep(1) # buffer
        file_path = event.src_path
        filename = os.path.basename(file_path)
        print(f"\n Detected new file: {filename}")
        
        try:
            with open(file_path, 'rb') as f:
                files = {'document': f}
                headers = {'Authorization': f'Bearer {self.api_key}'}
                
                print(" Uploading to Cloud Server...")
                response = requests.post(f"{SERVER_URL}/wiki/ingest", files=files, headers=headers)
                
                if response.status_code == 202:
                    print("Server accepted the file! Processing in background...")
                    job_id = response.json().get("jobId")
                    
                    if job_id:
                        # Call the polling function right here!
                        poll_for_result(job_id, self.api_key, filename)
                    else:
                        print("Server did not return a Job ID.")
                else:
                    try:
                        err_msg = response.json().get('message')
                    except:
                        err_msg = response.text
                    print(f" Server Error: {err_msg}")
        except Exception as e:
            print(f" Upload failed: {e}")

def startWatching(api_key):
    event_handler = FileDropHandler(api_key)
    observer = Observer()
    observer.schedule(event_handler, INPUT_FOLDER, recursive=True)
    observer.start()

    print("\n Watcher Started")
    print(f" Monitoring '{INPUT_FOLDER}' for changes.")
    print("Press CTRL+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n Watcher stopped.")
    observer.join()        

# --- MAIN BOOT SEQUENCE ---
if __name__ == "__main__":
    print("\n===============================")
    print("    Welcome to WikiSync CLI    ")
    print("===============================")
    
    API_KEY = None
    
    while not API_KEY:
        print("\n Please select an option:")
        print("1) Login & Start")
        print("2) Register & Start")
        print("3) Change Custom LLM Key & Start")
        print("4) Exit")
        
        choice = input("> ")
        
        if choice == '1':
            API_KEY = action_login()
        elif choice == '2':
            API_KEY = action_register()
        elif choice == '3':
            API_KEY = action_change_key()
        elif choice == '4':
            print("Goodbye!")
            exit(0)
        else:
            print("Invalid choice. Please press 1, 2, 3, or 4.")
            
    # If successfully complete any flow, start the engine
    startWatching(API_KEY)