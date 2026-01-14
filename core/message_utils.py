"""
Utility functions for message handling, including splitting long messages.
"""


def split_message(text: str, max_length: int = 4096) -> list[str]:
    """
    Split a message into chunks that don't exceed max_length characters.
    Tries to split on newlines when possible to avoid breaking in the middle of a line.
    
    Args:
        text: Message text to split
        max_length: Maximum length per chunk (default: 4096 for Telegram)
    
    Returns:
        List of message chunks
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    remaining = text
    
    while len(remaining) > max_length:
        # Try to find the last newline within the max_length
        chunk = remaining[:max_length]
        last_newline = chunk.rfind('\n')
        
        if last_newline > max_length * 0.8:  # If newline is in the last 20%, use it
            chunk = remaining[:last_newline + 1]
            remaining = remaining[last_newline + 1:]
        else:
            # No good newline found, split at max_length
            chunk = remaining[:max_length]
            remaining = remaining[max_length:]
        
        chunks.append(chunk)
    
    if remaining:
        chunks.append(remaining)
    
    return chunks
