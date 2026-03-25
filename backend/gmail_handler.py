import eel
import webbrowser
import threading

@eel.expose
def open_gmail():
    """
    Open Gmail in the default browser.
    Returns: {success: bool, message: str}
    """
    try:
        gmail_url = "https://mail.google.com"
        webbrowser.open(gmail_url)
        return {"success": True, "message": "Opening Gmail in your browser"}
    except Exception as e:
        error_msg = f"Error opening Gmail: {str(e)}"
        print(error_msg)
        return {"success": False, "error": error_msg}

def open_gmail_async():
    """Open Gmail in a background thread."""
    thread = threading.Thread(target=open_gmail, daemon=True)
    thread.start()