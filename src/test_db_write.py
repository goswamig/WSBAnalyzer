# test_db_write.py
from db_config import WSBTimeSeriesDB
from datetime import datetime, timezone
import logging
from dotenv import load_dotenv
import os
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_db_write():
    """Test writing and reading from InfluxDB"""
    load_dotenv()
    
    # Initialize database
    db = WSBTimeSeriesDB(
        url=os.getenv('INFLUXDB_URL', 'http://localhost:8086'),
        token=os.getenv('INFLUXDB_TOKEN'),
        org=os.getenv('INFLUXDB_ORG'),
        bucket=os.getenv('INFLUXDB_BUCKET')
    )
    
    try:
        # Write test point
        success = db.write_point(
            measurement="wsb_sentiment",
            tags={"ticker": "TEST_STOCK"},
            fields={
                "sentiment_score": 0.75,
                "confidence": 0.9,
                "mention_count": 1
            },
            timestamp=datetime.now(timezone.utc)
        )
        
        if not success:
            logger.error("Failed to write test data")
            return False
            
        # Wait a moment for the write to propagate
        logger.info("Waiting for write to propagate...")
        time.sleep(2)
        
        # Read back the data
        latest = db.query_latest_records(1)
        logger.info(f"Read back data: {latest}")
        
        # Get database stats
        stats = db.get_database_stats()
        logger.info(f"Database stats: {stats}")
        
        # Print database details
        logger.info(f"Database URL: {os.getenv('INFLUXDB_URL')}")
        logger.info(f"Organization: {os.getenv('INFLUXDB_ORG')}")
        logger.info(f"Bucket: {os.getenv('INFLUXDB_BUCKET')}")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    test_db_write()