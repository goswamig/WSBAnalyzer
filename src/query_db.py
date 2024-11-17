from db_config import WSBTimeSeriesDB
import os
import pandas as pd
from datetime import datetime, timedelta

def get_simplified_stats(db):
    """
    Get simplified database statistics using a more reliable query
    """
    try:
        # Count total records
        count_query = f'''
        from(bucket: "{db.bucket}")
            |> range(start: -30d)
            |> filter(fn: (r) => r["_measurement"] == "wsb_sentiment")
            |> filter(fn: (r) => r["_field"] == "weighted_sentiment")
            |> count()
        '''
        
        # Count unique tickers (modified to avoid type collision)
        tickers_query = f'''
        from(bucket: "{db.bucket}")
            |> range(start: -30d)
            |> filter(fn: (r) => r["_measurement"] == "wsb_sentiment")
            |> filter(fn: (r) => r["_field"] == "weighted_sentiment")
            |> group(columns: ["ticker"])
            |> count()
            |> count()
        '''
        
        # Execute queries
        result = db.query_api.query(count_query, org=db.org)
        total_records = 0
        if result and len(result) > 0 and len(result[0].records) > 0:
            total_records = result[0].records[0].get_value()

        result = db.query_api.query(tickers_query, org=db.org)
        unique_tickers = 0
        if result and len(result) > 0 and len(result[0].records) > 0:
            unique_tickers = result[0].records[0].get_value()

        return {
            "total_records": total_records,
            "unique_tickers": unique_tickers
        }
    except Exception as e:
        print(f"Error getting simplified stats: {e}")
        return {
            "total_records": 0,
            "unique_tickers": 0
        }

def get_ticker_sentiment_table(db, days_back=7):
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
                    'confidence': float(record.values.get('confidence', 1)),  # Default confidence to 1 if not available
                })

        if not data:
            print("No data found in the specified time range")
            return None

        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Calculate weighted average sentiment for each ticker-date combination
        df['weighted_sentiment'] = df['sentiment'] * df['confidence']
        pivot_df = df.pivot_table(
            values='weighted_sentiment',
            index='ticker',
            columns='date',
            aggfunc='mean'  # Uses mean for multiple entries on same date
        ).round(2)  # Round to 2 decimal places
        
        # Sort columns by date (newest to oldest)
        pivot_df = pivot_df.reindex(sorted(pivot_df.columns, reverse=True), axis=1)
        
        # Sort rows by the most recent date's absolute sentiment value
        most_recent_date = pivot_df.columns[0]
        pivot_df['abs_sentiment'] = pivot_df[most_recent_date].abs()
        pivot_df = pivot_df.sort_values('abs_sentiment', ascending=False)
        pivot_df = pivot_df.drop('abs_sentiment', axis=1)
        
        return pivot_df
    except Exception as e:
        print(f"Error getting ticker stats: {e}")
        return {

        }

def print_sentiment_table(df):
    if df is None or df.empty:
        print("No data to display")
        return
        
    # Print header
    print("\n=== Ticker Sentiment Analysis ===")
    print("(Positive = Bullish, Negative = Bearish)")
    print("\nSentiment ranges from -1 (most bearish) to +1 (most bullish)")
    print("-" * 80)
    
    # Convert DataFrame to string with custom formatting
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    
    # Create a styled string representation
    print(df.fillna('-').to_string())
    print("-" * 80)
    
    # Print summary
    print("\nSummary:")
    print(f"Total Tickers Tracked: {len(df.index)}")
    print(f"Date Range: {df.columns[-1]} to {df.columns[0]}")
    
    # Get most bullish and bearish tickers from latest date
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



# Initialize DB connection
db = WSBTimeSeriesDB(
    url=os.getenv('INFLUXDB_URL', 'http://influxdb:8086'),
    token=os.getenv('INFLUXDB_TOKEN', 'my-super-secret-influx-token'),
    org=os.getenv('INFLUXDB_ORG', 'wsb_analytics'),
    bucket=os.getenv('INFLUXDB_BUCKET', 'wsb_sentiment')
)

try:
    # Get simplified statistics
    print("\n=== Database Statistics ===")
    stats = get_simplified_stats(db)
    print(f"Total Records: {stats['total_records']}")
    print(f"Unique Tickers: {stats['unique_tickers']}")

    # Get all data from the last 24 hours with additional fields
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

    # Get and print the sentiment table for the last 7 days
    sentiment_df = get_ticker_sentiment_table(db, days_back=7)
    print_sentiment_table(sentiment_df)

except Exception as e:
    print(f"Error querying database: {e}")
finally:
    # Close the connection
    db.close()