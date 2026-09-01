import datetime
import random
from database import SessionLocal, Event, init_db

def generate_synthetic_events(days=30):
    """Generates synthetic historical events for zone_1 and zone_2."""
    session = SessionLocal()
    
    # Check if we already have synthetic data to avoid duplication
    existing = session.query(Event).filter(Event.source == 'synthetic').first()
    if existing:
        print("Synthetic data already exists. Skipping generation.")
        session.close()
        return

    print(f"Generating {days} days of synthetic history...")
    
    now = datetime.datetime.now()
    events_to_add = []
    
    for day_offset in range(days):
        current_date = now - datetime.timedelta(days=day_offset)
        
        for hour in range(24):
            # Daytime (7 AM to 9 PM)
            if 7 <= hour <= 21:
                # Generate 3 to 12 person events per hour per zone
                person_count_z1 = random.randint(3, 12)
                person_count_z2 = random.randint(3, 12)
                
                # Occasional car event
                car_count_z1 = random.randint(0, 2)
            # Nighttime (9 PM to 7 AM)
            else:
                # Generate 0 to 1 person events per hour per zone
                person_count_z1 = random.randint(0, 1)
                person_count_z2 = random.randint(0, 1)
                car_count_z1 = 0
                
            # Helper to create events
            def create_events(count, zone, obj_class):
                for _ in range(count):
                    # Random minute and second within the hour
                    minute = random.randint(0, 59)
                    second = random.randint(0, 59)
                    event_time = current_date.replace(hour=hour, minute=minute, second=second)
                    
                    e = Event(
                        timestamp=event_time,
                        zone=zone,
                        object=obj_class,
                        confidence=round(random.uniform(0.6, 0.95), 2),
                        source='synthetic'
                    )
                    events_to_add.append(e)

            create_events(person_count_z1, 'zone_1', 'person')
            create_events(person_count_z2, 'zone_2', 'person')
            create_events(car_count_z1, 'zone_1', 'car')

    session.bulk_save_objects(events_to_add)
    session.commit()
    session.close()
    print(f"Successfully generated {len(events_to_add)} synthetic events.")

if __name__ == "__main__":
    init_db()
    generate_synthetic_events()
