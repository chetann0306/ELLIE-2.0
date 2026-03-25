"""
Optimize AI responses for better audio clarity and natural speech.
"""

def optimize_response(text):
    """
    Optimize response text for TTS.
    - Remove special characters
    - Fix abbreviations
    - Add pauses with punctuation
    """
    if not text:
        return text
    
    # Replace common abbreviations
    replacements = {
        'AI': 'Artificial Intelligence',
        'ML': 'Machine Learning',
        'API': 'API',
        'IoT': 'Internet of Things',
        'URL': 'URL',
        'HTTP': 'HTTP',
        'SMS': 'SMS',
        'GPS': 'GPS',
        'WiFi': 'Wi-Fi',
        'USB': 'USB',
        'PDF': 'PDF',
        'etc.': 'etcetera',
        'Mr.': 'Mister',
        'Mrs.': 'Misses',
        'Dr.': 'Doctor',
        'St.': 'Street',
        'Ave.': 'Avenue',
        'Inc.': 'Incorporated',
        'Ltd.': 'Limited',
        'Co.': 'Company',
        '&': 'and',
        '@': 'at',
    }
    
    for abbrev, replacement in replacements.items():
        text = text.replace(abbrev, replacement)
    
    # Remove extra spaces
    text = ' '.join(text.split())
    
    # Remove or replace problematic characters
    problematic_chars = {
        '*': '',
        '_': '',
        '-': ' ',
        '|': ',',
        '`': "'",
    }
    
    for char, replacement in problematic_chars.items():
        text = text.replace(char, replacement)
    
    # Add commas for natural pauses (after 20 words)
    words = text.split()
    if len(words) > 20:
        for i in range(20, len(words), 20):
            if i < len(words) and words[i-1][-1] not in '.,!?':
                words[i-1] += ','
    
    return ' '.join(words)


def split_long_response(text, max_length=200):
    """
    Split long responses into chunks for better delivery.
    """
    if len(text) <= max_length:
        return [text]
    
    sentences = text.replace('! ', '!|').replace('? ', '?|').replace('. ', '.|').split('|')
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_length:
            current_chunk += sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks if chunks else [text]