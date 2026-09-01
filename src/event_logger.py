import csv
import os
import datetime
from database import SessionLocal, Event, init_db

LOG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'events.csv'))

# Ensure the database tables exist when this module loads
init_db()

def log_event(event_dict):
    """
    Appends the event to events.csv and inserts it into the database.
    """
    file_exists = os.path.isfile(LOG_FILE)
    
    # 1. Log to CSV
    with open(LOG_FILE, mode='a', newline='') as csvfile:
        fieldnames = ['timestamp', 'zone', 'object', 'confidence', 'source']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
        
        # Write header if file doesn't exist or is empty
        if not file_exists or os.path.getsize(LOG_FILE) == 0:
            writer.writeheader()
            
        writer.writerow(event_dict)

    # 2. Log to Database
    session = SessionLocal()
    try:
        # Convert ISO format string back to datetime object for SQLite
        dt_obj = datetime.datetime.fromisoformat(event_dict['timestamp'])
        db_event = Event(
            timestamp=dt_obj,
            zone=event_dict['zone'],
            object=event_dict['object'],
            confidence=event_dict['confidence'],
            source=event_dict.get('source', 'real')
        )
        session.add(db_event)
        session.commit()
    except Exception as e:
        print(f"Database logging error: {e}")
        session.rollback()
    finally:
        session.close()
