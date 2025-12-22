"""
Utility functions for the AnkiPH addon
"""


def escape_anki_search(text: str) -> str:
    """
    Escape special characters for Anki search queries.
    
    Parentheses and other special characters in deck names or search terms
    will break Anki's search syntax if not properly escaped.
    
    Args:
        text: The text to escape (deck name, guid, etc.)
    
    Returns:
        Escaped text safe for use in Anki search queries
    """
    if not text:
        return text
    
    # Parentheses must be escaped with backslash
    text = text.replace("(", r"\(")
    text = text.replace(")", r"\)")
    # Escape double quotes
    text = text.replace('"', r'\"')
    # Escape colons in values (but not in search operators like deck:)
    # Note: Only escape colons that aren't part of deck:: subdeck notation
    # For now, we don't escape colons as they're needed for subdeck paths
    
    return text
