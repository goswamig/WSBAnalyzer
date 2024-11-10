import praw
import pandas as pd
import datetime
from typing import List, Dict, Tuple
import yfinance as yf
from openai import OpenAI
import json
import logging
from datetime import datetime, timedelta
from collections import Counter
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

    def scrape_wsb_posts(self, time_filter: str = 'day', min_score: int = 1) -> List[Dict]:
        """
        Scrape posts from r/wallstreetbets using multiple sorting methods to ensure comprehensive coverage
        
        Args:
            time_filter: Time filter for posts ('day', 'week', 'month', etc.)
            min_score: Minimum score (upvotes) for a post to be included
        """
        posts = {}  # Using dict to avoid duplicates by post ID
        subreddit = self.reddit.subreddit('wallstreetbets')
        
        # Define different sorting methods to get comprehensive coverage
        sort_methods = {
            'hot': subreddit.hot,
            'new': subreddit.new,
            'top': lambda: subreddit.top(time_filter=time_filter),
            'rising': subreddit.rising
        }
        
        try:
            current_date = datetime.now().date()
            
            for sort_name, sort_method in sort_methods.items():
                logger.info(f"Scraping {sort_name} posts...")
                
                try:
                    for post in sort_method():
                        post_date = datetime.fromtimestamp(post.created_utc).date()
                        
                        # Only include posts from the current date and with minimum score
                        if post_date == current_date and post.score >= min_score:
                            if post.id not in posts:  # Avoid duplicates
                                post_data = {
                                    'id': post.id,
                                    'title': post.title,
                                    'body': post.selftext,
                                    'score': post.score,
                                    'created_utc': datetime.fromtimestamp(post.created_utc),
                                    'url': post.url,
                                    'num_comments': post.num_comments,
                                    'upvote_ratio': post.upvote_ratio,
                                    'sort_type': sort_name,  # Track where we found this post
                                    'is_self': post.is_self,  # Is it a text post?
                                    'link_flair_text': post.link_flair_text if hasattr(post, 'link_flair_text') else None
                                }
                                
                                # Skip posts that are likely not relevant
                                if any(flair in str(post_data['link_flair_text']).lower() 
                                      for flair in ['meme', 'shitpost', 'weekend']):
                                    continue
                                
                                posts[post.id] = post_data
                
                except Exception as e:
                    logger.error(f"Error in {sort_name} scraping: {e}")
                    continue  # Continue with next sort method if one fails
            
            post_list = list(posts.values())
            
            # Additional logging for visibility
            logger.info(f"Scraping Summary:")
            logger.info(f"Total posts scraped: {len(post_list)}")
            
            if post_list:  # Only if we have posts
                logger.info(f"Posts by sort type: {dict(Counter(p['sort_type'] for p in post_list))}")
                logger.info(f"Time range: {min(p['created_utc'] for p in post_list)} to {max(p['created_utc'] for p in post_list)}")
            else:
                logger.warning("No posts were found matching the criteria!")
                
            return post_list
            
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
        if not posts:
            logger.warning("No posts provided for analysis")
            # Return empty DataFrame with correct columns
            return pd.DataFrame(columns=['date', 'ticker', 'dominant_sentiment', 'avg_confidence', 
                                      'total_score', 'mention_count', 'reasoning_summary'])
        
        sentiment_results = []
        logger.info(f"Analyzing {len(posts)} posts for sentiment...")
        
        for post in posts:
            text = f"{post['title']} {post['body']}"
            tickers = self.extract_tickers(text)
            
            if tickers:
                logger.info(f"Found tickers in post {post['id']}: {tickers}")
                sentiment = self.analyze_sentiment(text, tickers)
                
                for ticker, data in sentiment.items():
                    result = {
                        'date': post['created_utc'].date(),
                        'ticker': ticker,
                        'sentiment': data['sentiment'],
                        'confidence': data['confidence'],
                        'reasoning': data.get('reasoning', ''),
                        'post_score': post['score'],
                        'post_url': post['url']
                    }
                    sentiment_results.append(result)
        
        if not sentiment_results:
            logger.warning("No sentiment results found in any posts")
            return pd.DataFrame(columns=['date', 'ticker', 'dominant_sentiment', 'avg_confidence', 
                                      'total_score', 'mention_count', 'reasoning_summary'])
        
        df = pd.DataFrame(sentiment_results)
        logger.info(f"Generated sentiment results for {len(df)} ticker mentions")
        
        # Aggregate results
        agg_df = df.groupby(['date', 'ticker']).agg({
            'sentiment': lambda x: x.mode().iloc[0] if not x.empty else 'neutral',
            'confidence': 'mean',
            'post_score': 'sum',
            'post_url': 'count',
            'reasoning': lambda x: '; '.join(set(x))[:200]
        }).reset_index()
        
        agg_df.columns = ['date', 'ticker', 'dominant_sentiment', 'avg_confidence', 
                         'total_score', 'mention_count', 'reasoning_summary']
        
        return agg_df

    def save_report(self, df: pd.DataFrame, filename: str = None):
        """
        Save the report to CSV and generate a summary
        """
        if filename is None:
            filename = f"wsb_sentiment_report_{datetime.now().strftime('%Y%m%d')}.csv"
            
        # Save the full report
        df.to_csv(filename, index=False)
        logger.info(f"Report saved to {filename}")
        
        if df.empty:
            logger.warning("No data to summarize")
            return {
                'total_tickers_analyzed': 0,
                'most_mentioned_tickers': {},
                'sentiment_distribution': {},
                'high_confidence_calls': []
            }
        
        # Create a copy of the dataframe and convert date column to string
        df_summary = df.copy()
        df_summary['date'] = df_summary['date'].astype(str)
        
        # Ensure mention_count is numeric
        df_summary['mention_count'] = pd.to_numeric(df_summary['mention_count'], errors='coerce').fillna(0).astype(int)
        
        # Generate summary statistics
        summary = {
            'total_tickers_analyzed': int(df_summary['ticker'].nunique()),
            'most_mentioned_tickers': df_summary.groupby('ticker')['mention_count'].sum().astype(int).nlargest(5).to_dict(),
            'sentiment_distribution': df_summary.groupby('dominant_sentiment')['mention_count'].sum().astype(int).to_dict(),
            'high_confidence_calls': df_summary[df_summary['avg_confidence'] > 0.8].to_dict('records')
        }
        
        # Save summary to JSON
        summary_filename = f"wsb_sentiment_summary_{datetime.now().strftime('%Y%m%d')}.json"
        with open(summary_filename, 'w') as f:
            json.dump(summary, f, indent=4)
            
        logger.info(f"Generated summary with {len(summary['most_mentioned_tickers'])} top tickers")
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