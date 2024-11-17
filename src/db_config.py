# db_config.py
from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union
import logging

logger = logging.getLogger(__name__)

class WSBTimeSeriesDB:
    def __init__(self, url: str, token: str, org: str, bucket: str):
        """
        Initialize InfluxDB client
        
        Args:
            url: InfluxDB server URL
            token: InfluxDB authentication token
            org: InfluxDB organization
            bucket: InfluxDB bucket name
        """
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.write_api = self.client.write_api(            write_options=WriteOptions(
                batch_size=500,
                flush_interval=10_000,
                jitter_interval=2_000,
                retry_interval=5_000,
                max_retries=5,
                max_retry_delay=30_000,
                exponential_base=2
            ))
        self.query_api = self.client.query_api()
        self.org = org
        self.bucket = bucket
        
    def write_point(self, measurement: str, tags: Dict, fields: Dict, timestamp: Optional[datetime] = None) -> bool:
        """
        Write a single point to the database
        
        Args:
            measurement: Name of the measurement
            tags: Dictionary of tags
            fields: Dictionary of fields
            timestamp: Optional timestamp (defaults to current UTC time)
        """
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)

            point = Point(measurement)
            
            # Add tags
            for key, value in tags.items():
                point = point.tag(key, value)
                
            # Add fields
            for key, value in fields.items():
                if isinstance(value, bool):
                    point = point.field(key, value)
                elif isinstance(value, (int, float)):
                    point = point.field(key, float(value))
                else:
                    point = point.field(key, str(value))
                    
            point = point.time(timestamp)
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.info(f"Successfully wrote point: measurement={measurement}, tags={tags}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing point to database: {e}")
            return False
        
    def store_sentiment_data(self, df_row: Dict):
        """
        Store sentiment data point in InfluxDB
        
        Args:
            df_row: Dictionary containing sentiment data for a ticker
        """
        try:
            # Convert sentiment to numeric value (+1 for bullish, -1 for bearish, 0 for neutral)
            sentiment_value = {
                'bullish': 1,
                'bearish': -1,
                'neutral': 0
            }.get(df_row['dominant_sentiment'].lower(), 0)
            
            # Calculate weighted sentiment (sentiment * confidence)
            weighted_sentiment = sentiment_value * df_row['avg_confidence']
            
            # Create InfluxDB point
            point = Point("wsb_sentiment") \
                .tag("ticker", df_row['ticker']) \
                .field("weighted_sentiment", weighted_sentiment) \
                .field("confidence", df_row['avg_confidence']) \
                .field("mention_count", df_row['mention_count']) \
                .field("total_score", df_row['total_score']) \
                .time(datetime.strptime(str(df_row['date']), '%Y-%m-%d'))
            
            # Write to InfluxDB
            self.write_api.write(bucket=self.bucket, record=point)
            logger.info(f"Stored sentiment data for {df_row['ticker']} on {df_row['date']}")
            
        except Exception as e:
            logger.error(f"Error storing sentiment data: {e}")
            raise

    def store_summary_data(self, summary: Dict):
        """
        Store summary data point in InfluxDB
        """
        pass
        
    def query_ticker_sentiment(self, ticker: str, start_time: str, end_time: Optional[str] = None) -> List[Dict]:
        """
        Query sentiment data for a specific ticker
        
        Args:
            ticker: Stock ticker symbol
            start_time: Start time in format 'YYYY-MM-DD'
            end_time: Optional end time in format 'YYYY-MM-DD'
        
        Returns:
            List of sentiment data points
        """
        try:
            # Build Flux query
            if end_time is None:
                end_time = datetime.now().strftime('%Y-%m-%d')
                
            query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: {start_time}, stop: {end_time})
                |> filter(fn: (r) => r["ticker"] == "{ticker}")
                |> filter(fn: (r) => r["_measurement"] == "wsb_sentiment")
            '''
            
            # Execute query
            result = self.query_api.query(query=query, org=self.org)
            
            # Process results
            sentiment_data = []
            for table in result:
                for record in table.records:
                    sentiment_data.append({
                        'time': record.get_time().strftime('%Y-%m-%d'),
                        'ticker': record.values.get('ticker'),
                        'weighted_sentiment': record.values.get('weighted_sentiment'),
                        'confidence': record.values.get('confidence'),
                        'mention_count': record.values.get('mention_count'),
                        'total_score': record.values.get('total_score')
                    })
            
            return sentiment_data
            
        except Exception as e:
            logger.error(f"Error querying sentiment data: {e}")
            raise


    def query_latest_records(self, limit: int = 10) -> List[Dict]:
        """
        Query the most recent records from the database
        
        Args:
            limit: Number of records to return
        """
        try:
            query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: -30d)
                |> filter(fn: (r) => r["_measurement"] == "wsb_sentiment")
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: {limit})
            '''
            
            result = self.query_api.query(query, org=self.org)
            
            records = []
            for table in result:
                for record in table.records:
                    records.append({
                        'time': record.get_time().strftime('%Y-%m-%d %H:%M:%S'),
                        'ticker': record.values.get('ticker', ''),
                        'sentiment_score': record.get_value(),
                        'confidence': record.values.get('confidence', 0.0),
                        'mention_count': record.values.get('mention_count', 0)
                    })
            
            return records
            
        except Exception as e:
            logger.error(f"Error querying latest records: {e}")
            raise

    def get_database_stats(self) -> Dict:
        """
        Get basic statistics about the database contents
        """
        try:
            # Query for total records
            count_query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: -30d)
                |> filter(fn: (r) => r["_measurement"] == "wsb_sentiment")
                |> count()
            '''
            
            # Query for unique tickers
            tickers_query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: -30d)
                |> filter(fn: (r) => r["_measurement"] == "wsb_sentiment")
                |> distinct(column: "ticker")
                |> count()
            '''
            
            # Query for date range
            range_query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: -30d)
                |> filter(fn: (r) => r["_measurement"] == "wsb_sentiment")
                |> first()
                |> yield(name: "first")
                
            from(bucket: "{self.bucket}")
                |> range(start: -30d)
                |> filter(fn: (r) => r["_measurement"] == "wsb_sentiment")
                |> last()
                |> yield(name: "last")
            '''
            
            # Execute queries
            total_records = 0
            result = self.query_api.query(count_query, org=self.org)
            for table in result:
                for record in table.records:
                    total_records = record.get_value()
            
            unique_tickers = 0
            result = self.query_api.query(tickers_query, org=self.org)
            for table in result:
                for record in table.records:
                    unique_tickers = record.get_value()
            
            first_date = None
            last_date = None
            result = self.query_api.query(range_query, org=self.org)
            for table in result:
                for record in table.records:
                    if table.name == 'first':
                        first_date = record.get_time()
                    elif table.name == 'last':
                        last_date = record.get_time()
            
            # Calculate average records per day
            if first_date and last_date:
                days_diff = (last_date - first_date).days or 1  # Avoid division by zero
                avg_records = total_records / days_diff
                date_range = f"{first_date.strftime('%Y-%m-%d')} to {last_date.strftime('%Y-%m-%d')}"
            else:
                avg_records = 0
                date_range = "No data"
            
            return {
                'total_records': total_records,
                'unique_tickers': unique_tickers,
                'date_range': date_range,
                'avg_records_per_day': round(avg_records, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            raise
            


    def close(self):
        """Close the database connection"""
        try:
            self.write_api.close()
            self.client.close()
            logger.info("Database connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")

# Example environment variables needed for InfluxDB
'''
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_token_here
INFLUXDB_ORG=wsb_analytics
INFLUXDB_BUCKET=wsb_sentiment
'''