
import re
from typing import List

def recursive_character_text_splitter(
    text: str, 
    chunk_size: int = 1000, 
    chunk_overlap: int = 100
) -> List[str]:
    """
    Splits text into chunks recursively by trying separators in order:
    \n\n, \n, space, empty string.
    
    This is a simplified implementation of LangChain's RecursiveCharacterTextSplitter.
    """
    if not text:
        return []
    
    separators = ["\n\n", "\n", " ", ""]
    final_chunks = []
    
    # Start with the whole text
    _split_text(text, separators, chunk_size, chunk_overlap, final_chunks)
    
    return final_chunks

def _split_text(text: str, separators: List[str], chunk_size: int, chunk_overlap: int, final_chunks: List[str]):
    """Internal recursive split function"""
    
    # 1. Choose separator
    separator = separators[-1]
    new_separators = []
    
    for i, sep in enumerate(separators):
        if sep == "":
            separator = ""
            break
        if sep in text:
            separator = sep
            new_separators = separators[i+1:]
            break
            
    # 2. Split
    splits = text.split(separator) if separator else list(text)
    
    # 3. Merge splits into chunks
    current_chunk = []
    current_length = 0
    
    for split in splits:
        # If split is huge, recurse on it
        if len(split) > chunk_size:
            if new_separators:
                _split_text(split, new_separators, chunk_size, chunk_overlap, final_chunks)
            else:
                # Last resort: hard cut would be here, but for now just add it or truncation logic
                final_chunks.append(split[:chunk_size])
            continue
            
        # Check if adding this split exceeds chunk_size
        if current_length + len(split) + len(separator) > chunk_size:
            # Commit current chunk
            if current_chunk:
                doc = separator.join(current_chunk)
                if doc.strip():
                    final_chunks.append(doc)
            
            # Start new chunk with overlap?
            # Simplified: just start new chunk with current split
            # For overlap, we'd need to keep previous splits. Complexity for now: No overlap or simple carry over.
            
            current_chunk = [split]
            current_length = len(split)
        else:
            current_chunk.append(split)
            current_length += len(split) + len(separator)
            
    # Last chunk
    if current_chunk:
        doc = separator.join(current_chunk)
        if doc.strip():
            final_chunks.append(doc)
