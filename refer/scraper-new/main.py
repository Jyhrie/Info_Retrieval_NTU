import praw
import pandas as pd
import yaml
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import time 
import prawcore

def load_config(config_file='../config.yaml'):
    """
    Load configuration data from a YAML file.
    
    Args:
        config_file (str): Path to the YAML configuration file
        
    Returns:
        dict: Configuration parameters loaded from the file
    """
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
    return config

# Load Reddit API credentials and scraping config from config.yamle
config = load_config()
CLIENT_ID = config['reddit']['client_id']
CLIENT_SECRET = config['reddit']['client_secret']
USER_AGENT = config['reddit']['user_agent']

subreddits = config['scraping']['subreddits']
posts_per_subreddit = config['scraping']['posts_per_subreddit']

# Initialize Reddit instance
reddit = praw.Reddit(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, user_agent=USER_AGENT)

# Initialize sentiment analyzer
analyzer = SentimentIntensityAnalyzer()

# List of specific trading platforms
trading_platforms = [
    "robinhood", "webull", "td ameritrade", "thinkorswim", "fidelity", "schwab", 
    "etrade", "interactive brokers", "ibkr", "tastyworks", "merrill edge", 
    "vanguard", "sofi", "public", "moomoo", "tradingview", "m1 finance", 
    "tradestation", "tda", "futu", "tiger brokers", "firstrade", "ally invest",
    "degiro", "trading212", "plus500", "etoro", "saxo", "questrade", "wealthsimple",
    "ib", "tasty", "think or swim", "tos", "ameritrade", "charles schwab",
    "coinbase", "binance", "kraken", "gemini", "ftx", "kucoin", "crypto.com",
    "bitstamp", "huobi", "blockfi", "celsius", "voyager", "metamask", "trust wallet",
    "trading app", "brokerage", "trading platform", "broker"
]

# List of opinion-related keywords
opinion_keywords = [    
    # Opinion indicators
    "experience", "review", "thoughts", "feedback", "opinions", "recommendation", "suggest",
    "avoid", "stay away", "prefer", "better than", "worse than", "compared to", "versus",
    "good", "bad", "terrible", "excellent", "amazing", "awful", "horrible", "great",
    "recommend", "worth it", "not worth", "disappointed", "satisfied", "impressed", 
    "frustrating", "reliable", "unreliable", "convenient", "inconvenient", "user-friendly",
    "complicated", "straightforward", "easy to use", "difficult", "learning curve",
    
    # Evaluation terms
    "pros", "cons", "advantages", "disadvantages", "like", "dislike", "hate", "love",
    "rating", "star", "rank", "compare", "comparison", "alternative", "switch",
    "best", "worst", "top", "overrated", "underrated", "value for money"
]

# Keep the original keywords for additional context (fees, features, etc.)
additional_keywords = [    
    # Fees and costs
    "fee", "commission", "pricing", "cost", "expensive", "cheap", "affordable", "subscription",
    "monthly fee", "annual fee", "transaction fee", "hidden charges", "price", "pricing plan",
    
    # Trading features
    "options", "stock", "stocks", "futures", "forex", "crypto", "etf", "mutual fund", 
    "bonds", "derivatives", "margin", "leverage", "short selling", "fractional shares",
    "pre-market", "after-hours", "extended hours", "limit order", "stop loss", 
    
    # User experience
    "interface", "dashboard", "ui", "ux", "user interface", "intuitive", "clunky", "buggy",
    "responsive", "lag", "glitch", "crash", "latency", "loading time", "navigation",
    
    # Features and tools
    "chart", "charting", "analysis", "research", "screener", "scanner", "alert", "notification",
    "watchlist", "portfolio", "tracking", "news feed", "indicator", "technical analysis",
    "fundamental analysis", "educational", "tutorial", "mobile app", "desktop",
    
    # Support and service
    "customer service", "support", "help", "response time", "customer care", "assistance",
    "live chat", "phone support", "email support", "onboarding", "account opening"
]

def is_opinionated(comment_body):
    """
    Determine if a comment expresses a strong opinion based on sentiment analysis.
    
    Args:
        comment_body (str): The text of the comment to analyze
        
    Returns:
        bool: True if the comment contains strongly positive or negative sentiment,
              False otherwise
    """
    sentiment = analyzer.polarity_scores(comment_body)
    # Threshold for considering a comment opinionated
    return sentiment['compound'] > 0.25 or sentiment['compound'] < -0.25

def mentions_trading_platform(comment_text):
    """
    Check if a comment mentions any trading platform from the predefined list.
    
    Args:
        comment_text (str): The text of the comment to analyze
        
    Returns:
        bool: True if the comment mentions at least one trading platform,
              False otherwise
    """
    comment_lower = comment_text.lower()
    return any(platform.lower() in comment_lower for platform in trading_platforms)

def contains_opinion_keywords(comment_text):
    """
    Check if a comment contains any opinion-related keywords.
    
    Args:
        comment_text (str): The text of the comment to analyze
        
    Returns:
        bool: True if the comment contains opinion-related keywords,
              False otherwise
    """
    comment_lower = comment_text.lower()
    return any(keyword.lower() in comment_lower for keyword in opinion_keywords)

def scrape_subreddit(subreddit_name, limit=posts_per_subreddit):
    """
    Scrape comments from a subreddit that express opinions about trading platforms.
    
    Args:
        subreddit_name (str): Name of the subreddit to scrape
        limit (int): Maximum number of posts to scrape
        
    Returns:
        list: A list of dictionaries containing relevant comment information
    """
    # Get the subreddit
    subreddit = reddit.subreddit(subreddit_name)
    
    # Collect posts and comments data
    comments_data = []
    
    # Add a try-except block to handle rate limiting
    try:
        for submission in subreddit.hot(limit=limit):
            # Get the post content (selftext contains the body of the post)
            post_content = submission.selftext if submission.selftext else "[No text content]"
            
            
            # Collect post details
            submission.comments.replace_more(limit=0)  # Remove "MoreComments"
            
            for comment in submission.comments.list():
                # Filter out blank comments and comments that are too short
                if not comment.body.strip() or len(comment.body.split()) < 5:
                    continue
                
                # Check if comment mentions a trading platform
                if not mentions_trading_platform(comment.body):
                    continue
                    
                # Check if comment contains opinion-related keywords
                if not contains_opinion_keywords(comment.body):
                    continue
                    
                # Check sentiment only if the above two conditions are met
                if not is_opinionated(comment.body):
                    continue
                
                # Collect relevant comment details
                created_timestamp = datetime.utcfromtimestamp(comment.created_utc)
                readable_date = created_timestamp.strftime("%d %B %Y")  

                # Collect comment information
                comment_info = {
                    'subreddit': subreddit_name,
                    'title': submission.title,
                    'post_id': submission.id,
                    'post_url': submission.url,
                    'post_content': post_content,  
                    'comment_id': comment.id,
                    'comment_body': comment.body,
                    'comment_author': comment.author.name if comment.author else 'unknown',
                    'comment_score': comment.score,
                    'created': comment.created_utc,
                    'created_iso': created_timestamp.isoformat(),
                    'readable_date': readable_date,
                    'sentiment': analyzer.polarity_scores(comment.body)['compound']
                }
                comments_data.append(comment_info)
                
    
    except prawcore.exceptions.TooManyRequests:
        print(f"Hit rate limit while scraping r/{subreddit_name}. Waiting 60 seconds...")
        time.sleep(60)  # Wait 1 minute if rate limited
        print("Resuming scraping...")
    
    except Exception as e:
        print(f"Error while scraping r/{subreddit_name}: {str(e)}")
    
    return comments_data


def save_to_csv(data, filename="results.csv"):
    """
    Save the collected comment data to a CSV file.
    
    Args:
        data (list): List of dictionaries containing comment information
        filename (str): Name of the CSV file to save the data to
    
    Returns:
        None
    """
    # Save the data to CSV
    if data:
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        print(f"Successfully saved {len(data)} comments to {filename}")
    else:
        print("No comments were found matching the criteria")

def main():
    """
    Main function to execute the Reddit comment scraping process.
    
    This function:
    1. Iterates through the configured subreddits
    2. Scrapes each subreddit for comments about trading platforms
    3. Collects and filters relevant comments
    4. Saves all collected comments to a CSV file
    """
    all_comments = []
    
    for subreddit in subreddits:
        print(f"Scraping comments from subreddit: {subreddit}")
        comments = scrape_subreddit(subreddit, limit=posts_per_subreddit)
        print(f"Found {len(comments)} relevant comments in r/{subreddit}")
        all_comments.extend(comments)
    
    print(f"Total comments collected: {len(all_comments)}")
    save_to_csv(all_comments)

if __name__ == "__main__":
    main()