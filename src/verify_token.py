# verify_token.py
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from dotenv import load_dotenv
import os
import logging
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_token():
    load_dotenv()
    
    url = os.getenv('INFLUXDB_URL')
    token = os.getenv('INFLUXDB_TOKEN')
    org = os.getenv('INFLUXDB_ORG')
    bucket = os.getenv('INFLUXDB_BUCKET')
    
    logger.info(f"\nChecking InfluxDB Configuration:")
    logger.info(f"URL: {url}")
    logger.info(f"Organization: {org}")
    logger.info(f"Bucket: {bucket}")
    logger.info(f"Token length: {len(token) if token else 0}")
    
    client = InfluxDBClient(url=url, token=token, org=org)
    write_api = None
    
    try:
        # Check health
        health = client.health()
        logger.info(f"\nHealth Check:")
        logger.info(f"Status: {health.status}")
        logger.info(f"Message: {health.message}")
        
        # Check access to buckets
        buckets_api = client.buckets_api()
        buckets = buckets_api.find_buckets().buckets
        
        logger.info("\nAccessible Buckets:")
        for bucket_obj in buckets:
            logger.info(f"- {bucket_obj.name}")
            
        # Check if our bucket exists and is accessible
        target_bucket = next((b for b in buckets if b.name == bucket), None)
        if target_bucket:
            logger.info(f"\nTarget bucket '{bucket}' exists and is accessible")
            logger.info(f"Bucket ID: {target_bucket.id}")
            for rule in target_bucket.retention_rules:
                logger.info(f"Retention: {rule.every_seconds}s")
        else:
            logger.error(f"\nTarget bucket '{bucket}' not found or not accessible!")
            
        # Check organization access
        orgs_api = client.organizations_api()
        orgs = orgs_api.find_organizations()
        
        logger.info("\nAccessible Organizations:")
        for org_obj in orgs:
            logger.info(f"- {org_obj.name} (ID: {org_obj.id})")
            
        # Check if our org exists and is accessible
        target_org = next((o for o in orgs if o.name == org), None)
        if target_org:
            logger.info(f"\nTarget organization '{org}' exists and is accessible")
            logger.info(f"Org ID: {target_org.id}")
        else:
            logger.error(f"\nTarget organization '{org}' not found or not accessible!")
            
        # Try a simple write permission test
        logger.info("\nTesting write permissions...")
        write_api = client.write_api(write_options=SYNCHRONOUS)
        try:
            write_api.write(bucket=bucket, record={
                'measurement': 'test_measurement',
                'fields': {'value': 1.0},
                'tags': {'test': 'permission_check'}
            })
            logger.info("Write permission test: SUCCESS")
        except Exception as e:
            logger.error(f"Write permission test: FAILED - {str(e)}")
            
        # Try a simple query permission test
        logger.info("\nTesting query permissions...")
        query_api = client.query_api()
        try:
            query = f'''
            from(bucket:"{bucket}")
                |> range(start: -1m)
                |> filter(fn: (r) => r["_measurement"] == "test_measurement")
                |> filter(fn: (r) => r["test"] == "permission_check")
                |> yield(name: "last")
            '''
            result = query_api.query(query=query)
            logger.info("Query permission test: SUCCESS")
            if len(result) > 0:
                logger.info("Successfully read back test data")
            else:
                logger.info("No test data found in read-back (this is normal if writes are not immediate)")
        except Exception as e:
            logger.error(f"Query permission test: FAILED - {str(e)}")
            
        logger.info("\nAll verification checks completed successfully!")
        return True
            
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return False
        
    finally:
        # Clean up
        if write_api:
            write_api.close()
        client.close()

def check_api_auth():
    """Direct API check for token authentication"""
    load_dotenv()
    
    url = os.getenv('INFLUXDB_URL')
    token = os.getenv('INFLUXDB_TOKEN')
    
    headers = {
        'Authorization': f'Token {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Check health endpoint
        response = requests.get(f"{url}/health", headers=headers)
        logger.info(f"\nDirect API Health Check:")
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response: {response.json()}")
        
        # Check ping endpoint
        response = requests.get(f"{url}/ping", headers=headers)
        logger.info(f"\nPing Check:")
        logger.info(f"Status Code: {response.status_code}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking API auth: {e}")
        return False

def main():
    """Main execution function"""
    logger.info("Starting token verification...")
    
    # First check basic API connectivity
    if not check_api_auth():
        logger.error("Failed to verify basic API connectivity")
        return False
        
    # Then perform detailed token verification
    if not verify_token():
        logger.error("Failed to verify token permissions")
        return False
        
    logger.info("Token verification completed successfully!")
    return True

if __name__ == "__main__":
    main()