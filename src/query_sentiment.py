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
    
    return WSBTimeSeriesDB(
        url=os.getenv('INFLUXDB_URL'),
        token=os.getenv('INFLUXDB_TOKEN'),
        org=os.getenv('INFLUXDB_ORG'),
        bucket=os.getenv('INFLUXDB_BUCKET')
    )

def query_sentiment(ticker: str = None, days: int = None, start_date: str = None, 
                   end_date: str = None, output: str = None):
    """
    Query sentiment data with various filters
    
    Args:
        ticker: Stock ticker symbol
        days: Number of days to look back
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        output: Output file path for CSV export
    """
    try:
        db = setup_db()
        
        # Handle date parameters
        if days:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
        elif not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        # Query data
        sentiment_data = db.query_ticker_sentiment(ticker, start_date, end_date)
        
        # Convert to DataFrame for easy handling
        df = pd.DataFrame(sentiment_data)
        
        if df.empty:
            logger.warning(f"No data found for ticker {ticker} in specified date range")
            return
            
        # Calculate some basic statistics
        stats = {
            'average_sentiment': df['weighted_sentiment'].mean(),
            'total_mentions': df['mention_count'].sum(),
            'highest_confidence': df['confidence'].max(),
            'date_range': f"{df['time'].min()} to {df['time'].max()}"
        }
        
        # Print summary
        print("\nSentiment Analysis Summary:")
        print("-" * 50)
        print(f"Ticker: {ticker}")
        print(f"Date Range: {stats['date_range']}")
        print(f"Average Weighted Sentiment: {stats['average_sentiment']:.2f}")
        print(f"Total Mentions: {stats['total_mentions']}")
        print(f"Highest Confidence: {stats['highest_confidence']:.2f}")
        
        # Export to CSV if requested
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
    parser = argparse.ArgumentParser(description='Query WSB sentiment data')
    parser.add_argument('--ticker', type=str, help='Stock ticker symbol')
    parser.add_argument('--days', type=int, help='Number of days to look back')
    parser.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--output', type=str, help='Output CSV file path')
    
    args = parser.parse_args()
    
    if not any([args.ticker, args.days, args.start, args.end]):
        parser.print_help()
        return
        
    query_sentiment(
        ticker=args.ticker,
        days=args.days,
        start_date=args.start,
        end_date=args.end,
        output=args.output
    )

if __name__ == "__main__":
    main()