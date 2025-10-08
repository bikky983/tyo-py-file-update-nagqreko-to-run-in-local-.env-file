"""
Configuration module for Nepali News Summarizer.
Handles environment variables and API settings.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# DeepSeek API Configuration
DEEPSEEK_API_KEY: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL: str = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")

# Alternative LLM API Keys (for future extensibility)
OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")

# LLM API Configuration
LLM_REQUEST_TIMEOUT: int = int(os.getenv("LLM_REQUEST_TIMEOUT", "60"))
LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "3"))
LLM_RETRY_DELAY: float = float(os.getenv("LLM_RETRY_DELAY", "1.0"))

# DeepSeek Model Configuration
DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_MAX_TOKENS: int = int(os.getenv("DEEPSEEK_MAX_TOKENS", "150"))
DEEPSEEK_TEMPERATURE: float = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.3"))

# Nepali Summarization Prompts
NEPALI_SYSTEM_PROMPT: str = """तपाईं एक विशेषज्ञ नेपाली समाचार सारांशकर्ता हुनुहुन्छ। तपाईंको काम नेपाली समाचार लेखहरूलाई छोटो र स्पष्ट सारांशमा रूपान्तरण गर्नु हो।

निर्देशनहरू:
- केवल १-२ वाक्यमा सारांश दिनुहोस्
- नेपाली भाषामा मात्र जवाफ दिनुहोस्
- मुख्य तथ्यहरू र महत्वपूर्ण जानकारी समावेश गर्नुहोस्
- अनावश्यक विवरणहरू हटाउनुहोस्
- स्पष्ट र सरल भाषा प्रयोग गर्नुहोस्
- एक पटकमा एकै समाचार लेखको सारांश गर्नुहोस्"""

NEPALI_USER_PROMPT_TEMPLATE: str = """--- समाचार लेख सुरु ---
शीर्षक: {title}

मुख्य समाचार:
{text}
--- समाचार लेख समाप्त ---

कृपया माथिको नेपाली समाचार लेखको १-२ वाक्यमा सारांश दिनुहोस्। केवल नेपाली भाषामा जवाफ दिनुहोस्:"""

# English fallback prompts (if needed)
ENGLISH_SYSTEM_PROMPT: str = """You are an expert Nepali news summarizer. Your job is to create concise summaries of Nepali news articles.

Instructions:
- Provide summary in exactly 1-2 sentences
- Respond ONLY in Nepali language (देवनागरी script)
- Include main facts and important information
- Remove unnecessary details
- Use clear and simple language"""

ENGLISH_USER_PROMPT_TEMPLATE: str = """Please provide a 1-2 sentence summary of this Nepali news article in Nepali language:

{text}

Summary (in Nepali only):"""

# Rate Limiting Configuration
RATE_LIMIT_CALLS_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_CALLS_PER_MINUTE", "20"))
RATE_LIMIT_CALLS_PER_HOUR: int = int(os.getenv("RATE_LIMIT_CALLS_PER_HOUR", "1000"))

# Logging Configuration
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE: str = os.getenv("LOG_FILE", "logs/nepali_news_summarizer.log")
DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

def validate_api_configuration() -> tuple[bool, str]:
    """
    Validate that required API configuration is present.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not DEEPSEEK_API_KEY:
        return False, "DEEPSEEK_API_KEY is not set in environment variables"
    
    if not DEEPSEEK_API_URL:
        return False, "DEEPSEEK_API_URL is not set in environment variables"
    
    # Accept both OpenRouter (sk-or-v1-) and DeepSeek (sk-) API keys
    if not (DEEPSEEK_API_KEY.startswith("sk-") or DEEPSEEK_API_KEY.startswith("Sk-")):
        return False, "DEEPSEEK_API_KEY appears to be invalid (should start with 'sk-' or 'sk-or-v1-')"
    
    return True, "API configuration is valid"

def get_api_headers() -> dict:
    """
    Get headers for API requests.
    
    Returns:
        dict: Headers including authorization
    """
    return {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "Nepali-News-Summarizer/1.0"
    }

def get_summarization_request_body(text: str, title: str = "", language: str = "ne") -> dict:
    """
    Generate request body for summarization API call.
    
    Args:
        text: Text to summarize
        language: Language code ("ne" for Nepali, "en" for English)
    
    Returns:
        dict: Request body for API call
    """
    # Choose prompts based on language preference
    if language == "ne":
        system_prompt = NEPALI_SYSTEM_PROMPT
        user_prompt = NEPALI_USER_PROMPT_TEMPLATE.format(title=title, text=text)
    else:
        system_prompt = ENGLISH_SYSTEM_PROMPT
        user_prompt = ENGLISH_USER_PROMPT_TEMPLATE.format(text=text)
    
    return {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": DEEPSEEK_MAX_TOKENS,
        "temperature": DEEPSEEK_TEMPERATURE,
        "stream": False
    }
