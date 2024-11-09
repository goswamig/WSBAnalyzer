import praw
import pandas as pd
import datetime
from typing import List, Dict, Tuple
import yfinance as yf
from openai import OpenAI
import json
import logging
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wsb_sentiment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WSBSentimentAnalyzer:
    def __init__(self, reddit_client_id: str, reddit_client_secret: str, reddit_user_agent: str, openai_api_key: str):
        """
        Initialize the WSB Sentiment Analyzer with necessary API credentials
        """
        self.reddit = praw.Reddit(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            user_agent=reddit_user_agent
        )
        self.openai_client = OpenAI(api_key=openai_api_key)
        
        # Load known stock tickers
        self.stock_tickers = self._load_stock_tickers()
        
    def _load_stock_tickers(self) -> set:
        """Load stock tickers from Yahoo Finance"""
        try:
            # You might want to maintain a local cache of tickers and update periodically
            # This is a simplified version
            common_tickers = set(pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'])
            return {ticker.upper() for ticker in common_tickers}
        except Exception as e:
            logger.error(f"Error loading stock tickers: {e}")
            return set()

    def scrape_wsb_posts(self, time_filter: str = 'day', limit: int = 100) -> List[Dict]:
        """
        Scrape posts from r/wallstreetbets
        """
        posts = []
        subreddit = self.reddit.subreddit('wallstreetbets')
        
        try:
            for post in subreddit.top(time_filter=time_filter, limit=limit):
                post_data = {
                    'id': post.id,
                    'title': post.title,
                    'body': post.selftext,
                    'score': post.score,
                    'created_utc': datetime.fromtimestamp(post.created_utc),
                    'url': post.url,
                    'num_comments': post.num_comments
                }
                posts.append(post_data)
                
            logger.info(f"Successfully scraped {len(posts)} posts from WSB")
            return posts
        except Exception as e:
            logger.error(f"Error scraping WSB posts: {e}")
            return []

    def extract_tickers(self, text: str) -> List[str]:
        """
        Extract stock tickers from text
        """
        words = text.upper().split()
        # Filter words that match known stock tickers
        return [word for word in words if word in self.stock_tickers]

    def analyze_sentiment(self, text: str, tickers: List[str]) -> Dict:
        """
        Analyze sentiment using OpenAI API
        """
        if not tickers:
            return {}
            
        system_prompt = """
        You are a financial sentiment analyzer. Analyze the given text for sentiment regarding specific stock tickers.
        For each ticker mentioned, classify the sentiment as either 'bullish', 'bearish', or 'neutral'.
        Also provide a confidence score from 0 to 1.
        
        Return your analysis in the following JSON format:
        {
            "TICKER": {
                "sentiment": "bullish/bearish/neutral",
                "confidence": 0.XX,
                "reasoning": "brief explanation"
            }
        }
        
        Only include tickers that are actually discussed in the text.
        """
        
        user_prompt = f"""
        Analyze the sentiment for these tickers: {', '.join(tickers)}
        
        Text: {text}
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # or "gpt-3.5-turbo" for faster, cheaper analysis
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent analysis
                response_format={"type": "json_object"}
            )
            
            # Parse the JSON response
            sentiment_data = json.loads(response.choices[0].message.content)
            return sentiment_data
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {}

    def generate_daily_report(self, posts: List[Dict]) -> pd.DataFrame:
        """
        Generate a daily sentiment report
        """
        sentiment_results = []
        
        for post in posts:
            text = f"{post['title']} {post['body']}"
            tickers = self.extract_tickers(text)
            
            if tickers:
                sentiment = self.analyze_sentiment(text, tickers)
                
                for ticker, data in sentiment.items():
                    result = {
                        'date': post['created_utc'].date(),
                        'ticker': ticker,
                        'sentiment': data['sentiment'],
                        'confidence': data['confidence'],
                        'reasoning': data.get('reasoning', ''),  # Added reasoning field
                        'post_score': post['score'],
                        'post_url': post['url']
                    }
                    sentiment_results.append(result)
        
        df = pd.DataFrame(sentiment_results)
        
        # Aggregate results
        agg_df = df.groupby(['date', 'ticker']).agg({
            'sentiment': lambda x: x.mode().iloc[0] if not x.empty else 'neutral',
            'confidence': 'mean',
            'post_score': 'sum',
            'post_url': 'count',
            'reasoning': lambda x: '; '.join(set(x))[:200]  # Combine unique reasonings with length limit
        }).reset_index()
        
        agg_df.columns = ['date', 'ticker', 'dominant_sentiment', 'avg_confidence', 'total_score', 'mention_count', 'reasoning_summary']
        return agg_df

    def save_report(self, df: pd.DataFrame, filename: str = None):
        """
        Save the report to CSV and generate a summary
        """
        if filename is None:
            filename = f"wsb_sentiment_report_{datetime.now().strftime('%Y%m%d')}.csv"
            
        df.to_csv(filename, index=False)
        logger.info(f"Report saved to {filename}")
        
        # Create a copy of the dataframe and convert date column to string
        df_summary = df.copy()
        df_summary['date'] = df_summary['date'].astype(str)  # Added this line
        
        # Generate summary statistics
        summary = {
            'total_tickers_analyzed': df['ticker'].nunique(),
            'most_mentioned_tickers': df.groupby('ticker')['mention_count'].sum().nlargest(5).to_dict(),
            'sentiment_distribution': df.groupby('dominant_sentiment')['mention_count'].sum().to_dict(),
            'high_confidence_calls': df_summary[df_summary['avg_confidence'] > 0.8].to_dict('records')  # Changed df to df_summary here
        }
        
        # Save summary to JSON
        summary_filename = f"wsb_sentiment_summary_{datetime.now().strftime('%Y%m%d')}.json"
        with open(summary_filename, 'w') as f:
            json.dump(summary, f, indent=4)
        
        return summary

def main():
    # Load configuration from environment variables or config file
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    analyzer = WSBSentimentAnalyzer(
        reddit_client_id=os.getenv('REDDIT_CLIENT_ID'),
        reddit_client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
        reddit_user_agent=os.getenv('REDDIT_USER_AGENT'),
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )
    
    # Scrape posts
    posts = analyzer.scrape_wsb_posts()
    
    # Generate report
    report_df = analyzer.generate_daily_report(posts)
    
    # Save report and get summary
    summary = analyzer.save_report(report_df)
    
    # Log summary
    logger.info("Daily WSB Sentiment Analysis Summary:")
    logger.info(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()