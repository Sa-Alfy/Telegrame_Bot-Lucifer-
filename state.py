import json
import os

STATE_FILE = "state.json"

# Global state dictionary to hold the on/off status of our APIs
API_STATE = {
    "groq": True,
    "pollinations": True,
    "daraz": True
}

def load_state():
    global API_STATE
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                saved_state = json.load(f)
                API_STATE.update(saved_state)
        except Exception as e:
            print(f"Failed to load state: {e}")

def save_state():
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(API_STATE, f, indent=4)
    except Exception as e:
        print(f"Failed to save state: {e}")

# Load the state initially
load_state()
