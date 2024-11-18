# query_sentiment.py
import argparse
from datetime import datetime, timedelta
import pandas as pd
from db_config import WSBTimeSeriesDB
from dotenv import load_dotenv
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_db():
    """Setup database connection using environment variables"""
    load_dotenv()
    
    # When running locally, we need to connect to the exposed port on localhost
    influxdb_url = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
    
    # If running locally and URL contains 'influxdb', replace it with localhost
    if 'influxdb' in influxdb_url and not os.getenv('DOCKER_ENV'):
        influxdb_url = 'http://localhost:8086'
    
    logger.info(f"Connecting to InfluxDB at: {influxdb_url}")
    
    return WSBTimeSeriesDB(
        url=influxdb_url,
        token=os.getenv('INFLUXDB_TOKEN', 'my-super-secret-influx-token'),
        org=os.getenv('INFLUXDB_ORG', 'wsb_analytics'),
        bucket=os.getenv('INFLUXDB_BUCKET', 'wsb_sentiment')
        )

def get_ticker_sentiment_table(db, days_back=7):
    """Get sentiment data in a table format with dates as columns"""
    try:
        # Query to get all sentiment data for the last n days
        query = f'''
        from(bucket: "{db.bucket}")
            |> range(start: -{days_back}d)
            |> filter(fn: (r) => r["_measurement"] == "wsb_sentiment")
            |> pivot(rowKey: ["_time", "ticker"], columnKey: ["_field"], valueColumn: "_value")
        '''
        
        result = db.query_api.query(query, org=db.org)
        
        # Process the data into a format suitable for pandas
        data = []
        for table in result:
            for record in table.records:
                # Convert sentiment words to numbers if needed
                sentiment_value = record.values.get('weighted_sentiment', 0)
                if isinstance(sentiment_value, str):
                    sentiment_map = {'bullish': 1, 'neutral': 0, 'bearish': -1}
                    sentiment_value = sentiment_map.get(sentiment_value.lower(), 0)
                
                data.append({
                    'date': record.get_time().strftime('%Y-%m-%d'),
                    'ticker': record.values.get('ticker'),
                    'sentiment': float(sentiment_value),
                    'confidence': float(record.values.get('confidence', 1))
                })

        if not data:
            logger.warning("No data found in the specified time range")
            return None

        # Convert to DataFrame and pivot
        df = pd.DataFrame(data)
        df['weighted_sentiment'] = df['sentiment'] * df['confidence']
        pivot_df = df.pivot_table(
            values='weighted_sentiment',
            index='ticker',
            columns='date',
            aggfunc='mean'
        ).round(2)
        
        # Sort columns by date (newest to oldest)
        pivot_df = pivot_df.reindex(sorted(pivot_df.columns, reverse=True), axis=1)
        
        # Sort rows by the most recent date's absolute sentiment value
        most_recent_date = pivot_df.columns[0]
        pivot_df['abs_sentiment'] = pivot_df[most_recent_date].abs()
        pivot_df = pivot_df.sort_values('abs_sentiment', ascending=False)
        pivot_df = pivot_df.drop('abs_sentiment', axis=1)
        
        return pivot_df
        
    except Exception as e:
        logger.error(f"Error getting ticker sentiment table: {e}")
        return None

def print_sentiment_table(df):
    """Print formatted sentiment table with summary"""
    if df is None or df.empty:
        logger.warning("No data to display")
        return
        
    print("\n=== Ticker Sentiment Analysis ===")
    print("(Positive = Bullish, Negative = Bearish)")
    print("\nSentiment ranges from -1 (most bearish) to +1 (most bullish)")
    print("-" * 80)
    
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    
    print(df.fillna('-').to_string())
    print("-" * 80)
    
    print("\nSummary:")
    print(f"Total Tickers Tracked: {len(df.index)}")
    print(f"Date Range: {df.columns[-1]} to {df.columns[0]}")
    
    # Show most bullish and bearish tickers
    latest_date = df.columns[0]
    latest_data = df[latest_date].dropna()
    if not latest_data.empty:
        most_bullish = latest_data[latest_data > 0].nlargest(3)
        most_bearish = latest_data[latest_data < 0].nsmallest(3)
        
        print(f"\nMost Bullish Tickers ({latest_date}):")
        for ticker, sentiment in most_bullish.items():
            print(f"{ticker}: {sentiment:+.2f}")
            
        print(f"\nMost Bearish Tickers ({latest_date}):")
        for ticker, sentiment in most_bearish.items():
            print(f"{ticker}: {sentiment:+.2f}")

def get_latest_records(limit: int = 10):
    """Get the most recent records from the database"""
    try:
        db = setup_db()
        data = db.query_latest_records(limit)
        
        if not data:
            logger.warning("No recent records found")
            return
            
        df = pd.DataFrame(data)
        print("\nMost Recent Records:")
        print("-" * 50)
        print(df)
        return df
        
    except Exception as e:
        logger.error(f"Error getting latest records: {e}")
        raise
    finally:
        db.close()

def check_detailed_stats():
    """Get detailed statistics including latest records and sentiment table"""
    try:
        db = setup_db()
        
        # Get basic stats
        stats = db.get_database_stats()
        print("\nDatabase Statistics:")
        print("-" * 50)
        print(f"Total Records: {stats.get('total_records', 'N/A')}")
        print(f"Unique Tickers: {stats.get('unique_tickers', 'N/A')}")
        print(f"Date Range: {stats.get('date_range', 'N/A')}")
        print(f"Average Records per Day: {stats.get('avg_records_per_day', 'N/A')}")

        # Get latest 24-hour records
        print("\n=== Latest Records (Last 24 hours) ===")
        query = f'''
        from(bucket: "{db.bucket}")
            |> range(start: -24h)
            |> filter(fn: (r) => r["_measurement"] == "wsb_sentiment")
            |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
            |> sort(columns: ["_time"], desc: true)
        '''
        
        result = db.query_api.query(query, org=db.org)
        records_found = False
        print("\nDetailed Sentiment Analysis:")
        for table in result:
            for record in table.records:
                records_found = True
                print(f"\nTime: {record.get_time()}")
                print(f"Ticker: {record.values.get('ticker')}")
                print(f"Weighted Sentiment: {record.values.get('weighted_sentiment', 'N/A')}")
                print(f"Confidence: {record.values.get('confidence', 'N/A')}")
                print(f"Mention Count: {record.values.get('mention_count', 'N/A')}")
                print(f"Total Score: {record.values.get('total_score', 'N/A')}")
                print("-" * 50)
        
        if not records_found:
            print("No records found in the last 24 hours")

        # Get and print sentiment table
        sentiment_df = get_ticker_sentiment_table(db, days_back=7)
        print_sentiment_table(sentiment_df)
        
    except Exception as e:
        logger.error(f"Error checking detailed stats: {e}")
        raise
    finally:
        db.close()

def query_sentiment(ticker: str = None, days: int = None, start_date: str = None,
                   end_date: str = None, output: str = None):
    """Query sentiment data with various filters"""
    try:
        db = setup_db()
        
        if days:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
        elif not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        sentiment_data = db.query_ticker_sentiment(ticker, start_date, end_date)
        df = pd.DataFrame(sentiment_data)
        
        if df.empty:
            logger.warning(f"No data found for ticker {ticker} in specified date range")
            return
            
        stats = {
            'average_sentiment': df['weighted_sentiment'].mean(),
            'total_mentions': df['mention_count'].sum(),
            'highest_confidence': df['confidence'].max(),
            'date_range': f"{df['time'].min()} to {df['time'].max()}"
        }
        
        print("\nSentiment Analysis Summary:")
        print("-" * 50)
        print(f"Ticker: {ticker}")
        print(f"Date Range: {stats['date_range']}")
        print(f"Average Weighted Sentiment: {stats['average_sentiment']:.2f}")
        print(f"Total Mentions: {stats['total_mentions']}")
        print(f"Highest Confidence: {stats['highest_confidence']:.2f}")
        
        if output:
            df.to_csv(output, index=False)
            print(f"\nDetailed data exported to: {output}")
            
        return df
        
    except Exception as e:
        logger.error(f"Error querying sentiment data: {e}")
        raise
    finally:
        db.close()

def main():
    try:
        parser = argparse.ArgumentParser(description='Query WSB sentiment data')
        parser.add_argument('--ticker', type=str, help='Stock ticker symbol')
        parser.add_argument('--days', type=int, help='Number of days to look back')
        parser.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)')
        parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD)')
        parser.add_argument('--output', type=str, help='Output CSV file path')
        parser.add_argument('--latest', type=int, help='Show N most recent records')
        parser.add_argument('--stats', action='store_true', help='Show basic database statistics')
        parser.add_argument('--detailed', action='store_true', help='Show detailed statistics and sentiment table')
        
        args = parser.parse_args()
        
        if args.latest:
            get_latest_records(args.latest)
        elif args.stats:
            check_detailed_stats()
        elif args.detailed:
            check_detailed_stats()
        elif any([args.ticker, args.days, args.start, args.end]):
            query_sentiment(
                ticker=args.ticker,
                days=args.days,
                start_date=args.start,
                end_date=args.end,
                output=args.output
            )
        else:
            parser.print_help()

    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise
    finally:
        logger.info("Script execution completed")

if __name__ == "__main__":
    try:
        main()
        # Force exit to clean up any hanging connections
        os._exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        os._exit(1)