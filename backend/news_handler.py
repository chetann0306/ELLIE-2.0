import eel
import requests
from bs4 import BeautifulSoup
import threading
import feedparser
import webbrowser
from urllib.parse import quote

@eel.expose
def open_google_news():
    """
    Open Google News in the default browser.
    Returns: {success: bool, message: str}
    """
    try:
        news_url = "https://news.google.com"
        webbrowser.open(news_url)
        return {"success": True, "message": "Opening Google News in your browser"}
    except Exception as e:
        error_msg = f"Error opening Google News: {str(e)}"
        print(error_msg)
        return {"success": False, "error": error_msg}


@eel.expose
def open_google_news_search(query):
    """
    Open Google News search results for a query.
    Returns: {success: bool, url: str, message: str}
    """
    try:
        if not query or len(query.strip()) < 2:
            return {"success": False, "error": "Please provide a search term"}
        
        # Google News search URL
        search_query = quote(query)
        news_url = f"https://news.google.com/search?q={search_query}"
        
        webbrowser.open(news_url)
        
        return {
            "success": True,
            "url": news_url,
            "message": f"Opening Google News search for '{query}'"
        }
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(error_msg)
        return {"success": False, "error": error_msg}


@eel.expose
def open_google_news_category(category):
    """
    Open Google News for a specific category.
    Categories: World, Business, Technology, Entertainment, Sports, Science, Health
    """
    try:
        categories = {
            "world": "https://news.google.com/topics/CAAqIggKIhBDQkFTSHFxN0wyNUtSa0FOAA",
            "business": "https://news.google.com/topics/CAAqIggKIhBDQkFTSHFxN0wyNUtSa0FOZA",
            "technology": "https://news.google.com/topics/CAAqIggKIhBDQkFTSHFxN0wyNUtSa0FNAA",
            "entertainment": "https://news.google.com/topics/CAAqIggKIhBDQkFTSHFxN0wyNUtSa0FZAA",
            "sports": "https://news.google.com/topics/CAAqIggKIhBDQkFTSHFxN0wyNUtSa0FHAA",
            "science": "https://news.google.com/topics/CAAqIggKIhBDQkFTSHFxN0wyNUtSa0FBAA",
            "health": "https://news.google.com/topics/CAAqIggKIhBDQkFTSHFxN0wyNUtSa0FFAA"
        }
        
        category_lower = category.lower().strip()
        
        if category_lower not in categories:
            # If category not found, search instead
            return open_google_news_search(category)
        
        news_url = categories[category_lower]
        webbrowser.open(news_url)
        
        return {
            "success": True,
            "url": news_url,
            "message": f"Opening Google News - {category_lower.capitalize()}"
        }
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(error_msg)
        return {"success": False, "error": error_msg}


@eel.expose
def get_latest_news():
    """
    Fetch latest news headlines from multiple sources.
    Returns: {success: bool, headlines: list, message: str, error: str}
    """
    try:
        headlines = []
        
        # Method 1: Try using RSS feeds (more reliable)
        headlines.extend(_fetch_rss_news())
        
        # If RSS fails or returns empty, try web scraping
        if not headlines or len(headlines) < 3:
            headlines.extend(_fetch_google_news_scrape())
        
        if not headlines:
            return {"success": False, "error": "Could not fetch news at this time"}
        
        # Get top 3 headlines
        top_headlines = headlines[:3]
        
        # Create readable message
        message = "Here are the latest news headlines:\n"
        for idx, headline in enumerate(top_headlines, 1):
            message += f"{idx}. {headline['title']}\n"
        
        return {
            "success": True,
            "headlines": top_headlines,
            "message": message,
            "count": len(top_headlines)
        }
    
    except Exception as e:
        error_msg = f"Error fetching news: {str(e)}"
        print(error_msg)
        return {"success": False, "error": error_msg}


@eel.expose
def open_news_link(url):
    """
    Open a specific news link in browser.
    """
    try:
        if not url or len(url.strip()) < 5:
            return {"success": False, "error": "Invalid URL"}
        
        webbrowser.open(url)
        return {"success": True, "message": "Opening news article"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _fetch_rss_news():
    """Fetch news from RSS feeds."""
    try:
        headlines = []
        
        # BBC News RSS
        try:
            bbc_feed = feedparser.parse('http://feeds.bbc.co.uk/news/rss.xml')
            for entry in bbc_feed.entries[:2]:
                headlines.append({
                    "title": entry.get('title', 'No title'),
                    "link": entry.get('link', '#'),
                    "source": "BBC News",
                    "summary": entry.get('summary', '')[:150]
                })
        except:
            pass
        
        # Reuters RSS
        try:
            reuters_feed = feedparser.parse('https://feeds.reuters.com/reuters/topNews')
            for entry in reuters_feed.entries[:2]:
                headlines.append({
                    "title": entry.get('title', 'No title'),
                    "link": entry.get('link', '#'),
                    "source": "Reuters",
                    "summary": entry.get('summary', '')[:150]
                })
        except:
            pass
        
        # The Guardian RSS
        try:
            guardian_feed = feedparser.parse('https://www.theguardian.com/international/rss')
            for entry in guardian_feed.entries[:1]:
                headlines.append({
                    "title": entry.get('title', 'No title'),
                    "link": entry.get('link', '#'),
                    "source": "The Guardian",
                    "summary": entry.get('summary', '')[:150]
                })
        except:
            pass
        
        return headlines
    
    except Exception as e:
        print(f"RSS fetch error: {str(e)}")
        return []


def _fetch_google_news_scrape():
    """Fallback: Scrape Google News."""
    try:
        url = "https://news.google.com"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        headlines = []
        
        # Find article elements
        article_elements = soup.find_all('a', class_=lambda x: x and 'article' in x.lower())
        
        for elem in article_elements[:5]:
            title = elem.get_text(strip=True)
            link = elem.get('href', '#')
            if title and len(title) > 10:
                headlines.append({
                    "title": title,
                    "link": link,
                    "source": "Google News"
                })
        
        return headlines
    
    except Exception as e:
        print(f"Google News scrape error: {str(e)}")
        return []


@eel.expose
def get_india_news():
    """
    Fetch latest news specific to India.
    """
    try:
        headlines = []
        
        # Indian news sources
        # Times of India RSS (if available)
        try:
            toi_feed = feedparser.parse('https://timesofindia.indiatimes.com/rssfeedstopstories.cms')
            for entry in toi_feed.entries[:3]:
                headlines.append({
                    "title": entry.get('title', 'No title'),
                    "link": entry.get('link', '#'),
                    "source": "Times of India",
                    "summary": entry.get('summary', '')[:150]
                })
        except:
            pass
        
        # NDTV News
        try:
            ndtv_feed = feedparser.parse('https://feeds.ndtv.com/ndtvnews-top-stories')
            for entry in ndtv_feed.entries[:2]:
                headlines.append({
                    "title": entry.get('title', 'No title'),
                    "link": entry.get('link', '#'),
                    "source": "NDTV",
                    "summary": entry.get('summary', '')[:150]
                })
        except:
            pass
        
        if not headlines:
            return _fetch_google_news_scrape()
        
        return headlines
    
    except Exception as e:
        print(f"India news error: {str(e)}")
        return []