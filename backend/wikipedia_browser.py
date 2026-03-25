import eel
import wikipedia
import webbrowser
import threading
from urllib.parse import quote

@eel.expose
def search_and_open_wikipedia(query):
    """
    Search Wikipedia and open the result in the default browser.
    Returns: {success: bool, title: str, url: str, message: str, error: str}
    """
    try:
        if not query or len(query.strip()) < 2:
            return {"success": False, "error": "Please provide a search term"}
        
        # Search Wikipedia
        results = wikipedia.search(query, results=5)
        
        if not results:
            return {"success": False, "error": f"No Wikipedia results found for '{query}'"}
        
        # Get the first result
        try:
            page = wikipedia.page(results[0])
        except wikipedia.exceptions.DisambiguationError as e:
            # If disambiguation page, try the first option
            if e.options:
                page = wikipedia.page(e.options[0])
            else:
                return {"success": False, "error": "Disambiguation page with no options"}
        except wikipedia.exceptions.PageError:
            return {"success": False, "error": f"Page not found for '{results[0]}'"}
        
        # Open in browser
        webbrowser.open(page.url)
        
        return {
            "success": True,
            "title": page.title,
            "url": page.url,
            "message": f"Opening Wikipedia page for {page.title}"
        }
    
    except Exception as e:
        error_msg = str(e)
        print(f"Wikipedia search error: {error_msg}")
        return {"success": False, "error": f"Search failed: {error_msg}"}


@eel.expose
def get_wikipedia_summary(query):
    """
    Get Wikipedia summary without opening browser.
    Returns: {success: bool, title: str, summary: str, url: str, error: str}
    """
    try:
        if not query or len(query.strip()) < 2:
            return {"success": False, "error": "Please provide a search term"}
        
        # Search Wikipedia
        results = wikipedia.search(query, results=5)
        
        if not results:
            return {"success": False, "error": f"No Wikipedia results found for '{query}'"}
        
        # Get the first result
        try:
            page = wikipedia.page(results[0])
        except wikipedia.exceptions.DisambiguationError as e:
            if e.options:
                page = wikipedia.page(e.options[0])
            else:
                return {"success": False, "error": "Disambiguation page"}
        except wikipedia.exceptions.PageError:
            return {"success": False, "error": f"Page not found"}
        
        # Get summary (limit to 1000 characters for display)
        summary = page.summary[:1000] + "..." if len(page.summary) > 1000 else page.summary
        
        return {
            "success": True,
            "title": page.title,
            "summary": summary,
            "full_summary": page.summary,
            "url": page.url,
            "word_count": len(page.content.split())
        }
    
    except Exception as e:
        error_msg = str(e)
        print(f"Wikipedia summary error: {error_msg}")
        return {"success": False, "error": f"Error: {error_msg}"}


@eel.expose
def open_wikipedia_url(page_title):
    """
    Open a specific Wikipedia page by title.
    Returns: {success: bool, url: str, message: str, error: str}
    """
    try:
        page = wikipedia.page(page_title)
        webbrowser.open(page.url)
        
        return {
            "success": True,
            "url": page.url,
            "title": page.title,
            "message": f"Opening {page.title}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@eel.expose
def search_wikipedia_all_results(query):
    """
    Get all search results (up to 10) from Wikipedia.
    Returns: {success: bool, results: list, message: str, error: str}
    """
    try:
        if not query or len(query.strip()) < 2:
            return {"success": False, "error": "Please provide a search term"}
        
        # Search Wikipedia
        results = wikipedia.search(query, results=10)
        
        if not results:
            return {"success": False, "error": f"No Wikipedia results found for '{query}'"}
        
        results_list = []
        for result in results:
            try:
                page = wikipedia.page(result)
                results_list.append({
                    "title": page.title,
                    "url": page.url,
                    "preview": page.summary[:200] + "..." if len(page.summary) > 200 else page.summary
                })
            except:
                # Skip pages that have errors
                pass
        
        return {
            "success": True,
            "results": results_list,
            "count": len(results_list),
            "message": f"Found {len(results_list)} Wikipedia results for '{query}'"
        }
    
    except Exception as e:
        error_msg = str(e)
        print(f"Wikipedia search error: {error_msg}")
        return {"success": False, "error": f"Search failed: {error_msg}"}