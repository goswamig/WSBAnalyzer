# db_config.py
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import os
from datetime import datetime
from typing import Dict, List, Optional
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
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()
        self.org = org
        self.bucket = bucket
        
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
            
    def close(self):
        """Close the database connection"""
        self.client.close()

# Example environment variables needed for InfluxDB
'''
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_token_here
INFLUXDB_ORG=your_org
INFLUXDB_BUCKET=wsb_sentiment
'''