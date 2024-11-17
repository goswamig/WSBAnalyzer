# verify_setup.py
import requests
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, timezone
import logging
from dotenv import load_dotenv
import os
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

def check_influxdb_http():
    """Check if InfluxDB is responding to HTTP requests"""
    try:
        response = requests.get('http://localhost:8086/health')
        logger.info(f"InfluxDB HTTP Status: {response.status_code}")
        logger.info(f"InfluxDB Health Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error checking InfluxDB HTTP: {e}")
        return False

def verify_write_read():
    """Verify writing and reading from InfluxDB"""
    load_dotenv()
    
    # Get configuration
    url = os.getenv('INFLUXDB_URL')
    token = os.getenv('INFLUXDB_TOKEN')
    org = os.getenv('INFLUXDB_ORG')
    bucket = os.getenv('INFLUXDB_BUCKET')
    
    logger.info("InfluxDB Configuration:")
    logger.info(f"URL: {url}")
    logger.info(f"Org: {org}")
    logger.info(f"Bucket: {bucket}")
    logger.info(f"Token length: {len(token) if token else 0}")
    
    # Create client
    client = InfluxDBClient(
        url=url,
        token=token,
        org=org
    )
    
    try:
        # Check health
        health = client.health()
        logger.info(f"InfluxDB Client Health: {health}")
        
        # Check buckets
        buckets_api = client.buckets_api()
        buckets = buckets_api.find_buckets().buckets
        logger.info("\nAvailable Buckets:")
        for b in buckets:
            logger.info(f"- {b.name}")
        
        # Verify our bucket exists
        our_bucket = next((b for b in buckets if b.name == bucket), None)
        if not our_bucket:
            logger.error(f"Bucket '{bucket}' not found!")
            return False
        logger.info(f"Found bucket: {bucket}")
        
        # Create write API with synchronous mode
        write_api = client.write_api(write_options=SYNCHRONOUS)
        
        # Create test point
        current_time = datetime.now(timezone.utc)
        point = Point("test_measurement")\
            .tag("test_id", "verify_test")\
            .field("value", 100.0)\
            .time(current_time)
            
        # Write point
        logger.info("Writing test point...")
        write_api.write(bucket=bucket, org=org, record=point)
        logger.info("Write completed")
        
        # Wait a moment for write to propagate
        time.sleep(1)
        
        # Query the written data
        query = f'''
        from(bucket: "{bucket}")
            |> range(start: -1h)
            |> filter(fn: (r) => r["_measurement"] == "test_measurement")
            |> filter(fn: (r) => r["test_id"] == "verify_test")
            |> yield(name: "last")
        '''
        
        logger.info("Querying test point...")
        query_api = client.query_api()
        result = query_api.query(query=query, org=org)
        
        # Check results
        if result and len(result) > 0:
            for table in result:
                for record in table.records:
                    logger.info(f"Found record: time={record.get_time()}, value={record.get_value()}")
            logger.info("Successfully verified read/write operations")
            return True
        else:
            logger.error("No data found in query results")
            return False
            
    except Exception as e:
        logger.error(f"Error during verification: {e}")
        return False
        
    finally:
        # Clean up
        write_api.close()
        client.close()

if __name__ == "__main__":
    logger.info("Starting InfluxDB verification...")
    
    if not check_influxdb_http():
        logger.error("InfluxDB is not responding to HTTP requests")
        sys.exit(1)
        
    if not verify_write_read():
        logger.error("Write/read verification failed")
        sys.exit(1)
        
    logger.info("All checks passed successfully!")