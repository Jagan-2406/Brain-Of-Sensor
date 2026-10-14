from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, extract, text
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
import os

Base = declarative_base()

class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    zone = Column(String, nullable=False)
    object = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    source = Column(String, nullable=False) 
    urgency = Column(String, nullable=True)
    reason_codes = Column(String, nullable=True)
    historical_avg = Column(Float, nullable=True)
    priority_tag_json = Column(String, nullable=True)
    summary_text = Column(String, nullable=True)

#SQLite
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'bos.db'))
engine = create_engine(f'sqlite:///{db_path}', echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """Create the tables if they don't exist and perform column migrations."""
    Base.metadata.create_all(engine)
    
    with engine.connect() as conn:
        
        try:
            conn.execute(text("SELECT priority_tag_json FROM events LIMIT 1"))
        except Exception:
            try:
                conn.execute(text("ALTER TABLE events ADD COLUMN priority_tag_json TEXT"))
                conn.commit()
                print("Migrated DB: Added 'priority_tag_json' column to 'events' table.")
            except Exception:
                pass
                
        
        try:
            conn.execute(text("SELECT summary_text FROM events LIMIT 1"))
        except Exception:
            try:
                conn.execute(text("ALTER TABLE events ADD COLUMN summary_text TEXT"))
                conn.commit()
                print("Migrated DB: Added 'summary_text' column to 'events' table.")
            except Exception:
                pass

def get_zone_history(zone, hour_of_day, lookback_days=30):
    """
    Returns the average number of events that historically happen during `hour_of_day`
    in `zone` across the last `lookback_days`.
    """
    session = SessionLocal()
    try:
        
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=lookback_days)
        
        
        count = session.query(Event).filter(
            Event.zone == zone,
            Event.timestamp >= cutoff_date,
            extract('hour', Event.timestamp) == hour_of_day
        ).count()
    
        
        average_per_hour_occurrence = count / lookback_days if lookback_days > 0 else 0
        return count, average_per_hour_occurrence
    finally:
        session.close()
