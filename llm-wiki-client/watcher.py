import os
import time
import json
import requests
import pwinput
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# CONFIGURATION
SERVER_URL = "http://localhost:3000"
CONFIG_FILE = "config.json"
INPUT_FOLDER = "./Raw_Sources"
OUTPUT_FOLDER = "./Wiki_Notes"
ALLOW_DEFAULT_LLM = False  

os.makedirs(INPUT_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# HELPER FUNCTIONS
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
        res = requests.get(f"{SERVER_URL}/user/get-status", headers=headers)
        if res.status_code == 200:
            print(f"Authenticated! Daily Quota: {res.json().get('usage')}")
            return True
        return False
    except requests.exceptions.ConnectionError:
        print("Check your internet connection.")
        return False

# Input Wrapper
def ask_user(prompt_text, is_password=False):
    """Wraps inputs to always allow 'back' or 'cancel'."""
    display_prompt = f"{prompt_text} (or type 'back'): "
    
    while True:
        if is_password:
            val = pwinput.pwinput(prompt=display_prompt, mask="*")
        else:
            val = input(display_prompt)
            
        val = val.strip()

        if val.lower() in ['back', 'cancel', 'exit']:
            print("\nAction cancelled. Returning to menu...")
            return None
            

        if not val:
            print("Input cannot be empty. Please try again.")
            continue
            
        return val

# POLLING LOGIC
def poll_for_result(job_id, api_key, original_filename):
    print(f"Waiting for AI to process '{original_filename}'...")
    headers = {'Authorization': f'Bearer {api_key}'}
    
    while True:
        try:
            res = requests.get(f"{SERVER_URL}/wiki/job/{job_id}", headers=headers)
            if res.status_code == 200:
                job_data = res.json()
                status = job_data.get('status')
                
                if status == 'completed':
                    print(f"AI finished processing '{original_filename}'!")
                    markdown_text = job_data.get('markdown_result', '')
                    base_name = os.path.splitext(original_filename)[0]
                    new_filepath = os.path.join(OUTPUT_FOLDER, f"{base_name}.md")
                    
                    with open(new_filepath, "w", encoding="utf-8") as f:
                        f.write(markdown_text)
                        
                    print(f"Saved to {new_filepath}\n")
                    break 
                elif status == 'failed':
                    print(f"AI failed to process '{original_filename}'.")
                    break
        except requests.exceptions.ConnectionError:
            print("Lost connection to server while waiting...")
            
        time.sleep(5) 

# MENU ACTIONS
def action_login():
    print("\n--- LOGIN ---")
    local_key = get_local_key()
    if local_key:
        print("Found saved session. Verifying...")
        if verify_token(local_key):
            return local_key
        else:
            print("Saved session expired. Please log in manually.")

    email = ask_user("Email")
    if not email: return None 
    
    password = ask_user("Password", is_password=True)
    if not password: return None

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
    username = ask_user("Username")
    if not username: return None
    
    email = ask_user("Email")
    if not email: return None
    
    password = ask_user("Password", is_password=True)
    if not password: return None

    if ALLOW_DEFAULT_LLM:
        print("\n(Optional) Bring your own Gemini API key for unlimited use.")
        custom_key = ask_user("Custom LLM Key (or type 'skip' to use default)", is_password=True)
    else:
        print("\nRequired: You must provide your own Gemini API key to use this tool.")
        custom_key = ask_user("Custom LLM Key", is_password=True)
        
    if not custom_key: return None 
    
    payload = {"username": username, "email": email, "password": password}
    
    if ALLOW_DEFAULT_LLM:
        if custom_key.lower() != 'skip':
            payload["customLLMKey"] = custom_key
    else:
        payload["customLLMKey"] = custom_key

    try:
        response = requests.post(f"{SERVER_URL}/auth/register", json=payload)
        if response.status_code == 201:
            api_key = response.json().get("apiKey")
            save_local_key(api_key)
            print("Account created successfully!")
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
    email = ask_user("Email")
    if not email: return None
    
    password = ask_user("Password", is_password=True)
    if not password: return None

    try:
        login_res = requests.post(f"{SERVER_URL}/auth/login", json={"email": email, "password": password})
        if login_res.status_code != 200:
            print("Invalid email or password.")
            return None
            
        api_key = login_res.json().get("apiKey")
        save_local_key(api_key) 
        
        new_custom_key = ask_user("Enter your NEW Gemini API Key", is_password=True)
        if not new_custom_key: return None
        
        headers = {"Authorization": f"Bearer {api_key}"}
        update_res = requests.put(f"{SERVER_URL}/user/key", json={"customKey": new_custom_key}, headers=headers)
        
        if update_res.status_code == 200:
            print(f"{update_res.json().get('message')}")
            return api_key
        else:
            print(f"Failed to update key: {update_res.json().get('message')}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("Cannot reach the server.")
        return None

# FILE WATCHER LOGIC
class FileDropHandler(FileSystemEventHandler):
    def __init__(self, api_key):
        self.api_key = api_key

    def on_created(self, event):
        if event.is_directory or os.path.basename(event.src_path).startswith('.'):
            return

        time.sleep(1) 
        file_path = event.src_path
        filename = os.path.basename(file_path)
        print(f"\nDetected new file: {filename}")
        
        try:
            with open(file_path, 'rb') as f:
                files = {'document': f}
                headers = {'Authorization': f'Bearer {self.api_key}'}
                
                print("Uploading to Cloud Server...")
                response = requests.post(f"{SERVER_URL}/wiki/ingest", files=files, headers=headers)
                
                if response.status_code == 202:
                    print("Server accepted the file! Processing in background...")
                    job_id = response.json().get("jobId")
                    if job_id:
                        poll_for_result(job_id, self.api_key, filename)
                else:
                    err_msg = response.json().get('message', response.text)
                    print(f"Server Error: {err_msg}")
        except Exception as e:
            print(f"Upload failed: {e}")

def startWatching(api_key):
    event_handler = FileDropHandler(api_key)
    observer = Observer()
    observer.schedule(event_handler, INPUT_FOLDER, recursive=True)
    observer.start()

    print("\nWatcher Started")
    print(f"Monitoring '{INPUT_FOLDER}' for changes.")
    print("Press CTRL+C to stop watching and return to menu.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n\nWatcher paused by user.")
    
    observer.join() 
    return  

# MAIN MENU
if __name__ == "__main__":
    print("\n===============================")
    print("    Welcome to LLM-Wiki CLI    ")
    print("Based on the idea of LLM Knowledge Bases acting as a Second Brain by Andrej Karpathy")
    print("===============================")
    
    while True:
        print("\nMAIN MENU")
        print("1) Login & Start")
        print("2) Register & Start")
        print("3) Change Custom LLM Key")
        print("4) Exit")
        
        choice = input("> ")
        API_KEY = None
        
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
            
        if API_KEY and choice in ['1', '2']:
            startWatching(API_KEY)