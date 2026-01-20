import logging
import sys
from typing import Optional

# ANSI Color Codes
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

# Level Colors
LEVEL_COLORS = {
    logging.DEBUG: BLUE,
    logging.INFO: GREEN,
    logging.WARNING: YELLOW,
    logging.ERROR: RED,
    logging.CRITICAL: MAGENTA + BOLD,
}

# Tag Colors (Round-robin or fixed)
TAG_COLOR = CYAN + BOLD

class ColoredFormatter(logging.Formatter):
    """
    Custom Formatter that adds colors to the log output.
    Format: Time | Level | [TAG] | Message
    """
    def format(self, record):
        # Format time first
        record.asctime = self.formatTime(record, self.datefmt)
        
        # Determine colors
        level_color = LEVEL_COLORS.get(record.levelno, WHITE)
        tag = getattr(record, 'tag', None)
        
        # Build message parts
        time_str = f"{WHITE}{record.asctime}{RESET}"
        level_str = f"{level_color}{record.levelname:<8}{RESET}"
        
        if tag:
            # Application Log with Tag
            tag_str = f"{TAG_COLOR}[{tag}]{RESET}"
            msg_str = f"{level_color}{record.getMessage()}{RESET}"
            return f"{time_str} | {level_str} | {tag_str} | {msg_str}"
        else:
            # System Log (no tag) - Keep it simpler or add a default tag
            # To distinguish system logs clearly, we can use a simpler format or a default tag
            tag_str = f"{WHITE}[SYSTEM]{RESET}"
            msg_str = f"{WHITE}{record.getMessage()}{RESET}" # Keep system logs standard white
            return f"{time_str} | {level_str} | {tag_str} | {msg_str}"

class NexusLoggerAdapter(logging.LoggerAdapter):
    """
    Custom Logger Adapter that adds a tag to the record.
    """
    def process(self, msg, kwargs):
        # We don't modify the message here anymore, 
        # we pass the tag to extra dict so Formatter can pick it up
        extra = kwargs.get('extra', {})
        extra['tag'] = self.extra.get('tag', 'UNKNOWN')
        kwargs['extra'] = extra
        return msg, kwargs

def configure_logging(level: int = logging.INFO):
    """
    Configure the root logger with stream handler and colored formatter.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    if root_logger.handlers:
        root_logger.handlers = []

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    formatter = ColoredFormatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s", 
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    
    root_logger.addHandler(handler)
    
    # Set levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)

def get_logger(name: str, tag: str = "APP") -> logging.LoggerAdapter:
    """
    Get a logger with a specific tag.
    """
    logger = logging.getLogger(name)
    return NexusLoggerAdapter(logger, {'tag': tag})
