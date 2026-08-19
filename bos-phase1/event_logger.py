import csv
import os

LOG_FILE = 'events.csv'

def log_event(event_dict):
    """
    Appends the event to events.csv.
    """
    file_exists = os.path.isfile(LOG_FILE)
    
    with open(LOG_FILE, mode='a', newline='') as csvfile:
        fieldnames = ['timestamp', 'zone', 'object', 'confidence']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # Write header if file doesn't exist or is empty
        if not file_exists or os.path.getsize(LOG_FILE) == 0:
            writer.writeheader()
            
        writer.writerow(event_dict)
