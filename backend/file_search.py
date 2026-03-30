import os
import platform
import subprocess

def search_local_files(filename):
    """
    Rapidly sweeps the user's primary directories for a matching file.
    Returns the absolute path of the first match, or None.
    """
    # Get the current user's home directory (e.g., C:\Users\Chaitanya)
    home = os.path.expanduser('~')
    
    # Targeted sweep: Only search where personal files actually live
    search_dirs = [
        os.path.join(home, 'Documents'),
        os.path.join(home, 'Desktop'),
        os.path.join(home, 'Downloads')
    ]
    
    filename_lower = filename.lower().strip()
    
    print(f"🔍 Sweeping primary directories for: '{filename_lower}'...")
    
    for directory in search_dirs:
        if not os.path.exists(directory):
            continue
            
        # Walk through the directory tree
        for root, dirs, files in os.walk(directory):
            for file in files:
                # If the search term is anywhere in the filename
                if filename_lower in file.lower():
                    exact_path = os.path.join(root, file)
                    print(f"✅ File located: {exact_path}")
                    return exact_path
                    
    print("❌ File not found in targeted sweep.")
    return None

def open_file(filepath):
    """
    Opens the file automatically using the OS default application.
    """
    try:
        if platform.system() == 'Windows':
            os.startfile(filepath)
        elif platform.system() == 'Darwin':  # macOS
            subprocess.call(('open', filepath))
        else:  # Linux
            subprocess.call(('xdg-open', filepath))
        return True
    except Exception as e:
        print(f"⚠️ Error opening file: {e}")
        return False