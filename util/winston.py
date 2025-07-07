import os
import requests
import nltk
from nltk.corpus import stopwords
import string
from collections import Counter
from nltk.probability import FreqDist
import logging

logger = logging.getLogger(__name__)

def _get_winston_config():
    """Helper to get API key and URL from environment variables."""
    api_key = os.environ.get('WINSTON_AI_API_KEY')
    api_url = os.environ.get('WINSTON_AI_API_URL', "https://api.winstonai.com/v2/ai-content-detection")
    # Provide a default URL, but make sure to set it on Render if it's different.
    return api_key, api_url

def detect_ai_content(text):
    """
    Uses WinstonAI to detect if the provided text is likely AI-generated.

    Returns:
        tuple: (ai_probability_score as float, label as str)
    """
    if not text.strip():
        return -1, "No text"
    
    api_key, api_url = _get_winston_config()
    if not api_key:
        logger.error("WinstonAI API Key not set in environment variables for detect_ai_content.")
        return -1, "API Key Missing"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "CopycatChecker/1.0 (Django-detect_ai_content)" # Good practice
    }

    payload = {
        "text": text,
        "sentences": True,
        "language": "en"
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=60) # Added timeout
        response.raise_for_status()
        data = response.json()

        if "score" in data:
            human_score = data["score"]  # e.g., 92 means 92% human
            ai_score = round(100 - human_score, 2)  # AI score = 100 - human score
            label = "Likely AI-Generated" if ai_score >= 50 else "Likely Human-Written"
            return ai_score, label
        else:
            logger.error(f"WinstonAI API response missing 'score' key in detect_ai_content. Response: {data}")
            return -1, "Invalid response"

    except requests.exceptions.HTTPError as http_err:
        status_code = http_err.response.status_code
        response_text = http_err.response.text if http_err.response else "No response body."
        logger.error(f"WinstonAI API HTTP Error in detect_ai_content ({status_code}): {response_text}")

        if status_code == 403:
            # More specific check for token/credit issues
            if "credits" in response_text.lower() or "token" in response_text.lower() or "limit" in response_text.lower():
                return -1, "Insufficient Token for AI Check" # Or a more detailed internal code
            else:
                return -1, "API Access Denied"
        elif status_code == 400:
            return -1, "Bad Request to API"
        elif status_code == 422:
            return -1, "Unprocessable Entity (API)"
        elif status_code >= 500:
            return -1, "WinstonAI Server Error"
        else:
            return -1, f"API Error ({status_code})"

    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"WinstonAI API Connection Error in detect_ai_content: {conn_err}")
        return -1, "API Connection Error"
    except requests.exceptions.Timeout as timeout_err:
        logger.error(f"WinstonAI API Timeout Error in detect_ai_content: {timeout_err}")
        return -1, "API Timeout"
    except Exception as e:
        logger.exception(f"Unexpected error in detect_ai_content: {e}")
        return -1, "Unexpected Error"
    

def get_winston_ai_prediction(text):
    api_key, api_url = _get_winston_config()

    if not api_key:
        logger.error("WinstonAI API key is not set.")
        return None, "API Key Missing" # Return None for score, specific message for label

    if not text or not text.strip():
        logger.info("No text provided for WinstonAI analysis.")
        return None, "No Text Provided"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "text": text
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status() # This will raise an HTTPError for 4xx/5xx responses

        data = response.json()
        ai_score = data.get('score')
        ai_label = data.get('label')

        return ai_score, ai_label

    except requests.exceptions.HTTPError as e:
        # Catch specific HTTP errors
        if e.response.status_code == 403:
            logger.warning(f"WinstonAI API 403 Forbidden: Check API key or account limits. Error: {e.response.text}")
            return None, "API Forbidden (Check Key/Credits)" # Specific label for 403
        elif e.response.status_code == 400:
            logger.error(f"WinstonAI API 400 Bad Request: Invalid payload. Error: {e.response.text}")
            return None, "API Bad Request"
        else:
            logger.error(f"WinstonAI API HTTP Error {e.response.status_code}: {e.response.text}")
            return None, f"API Error {e.response.status_code}" # Generic HTTP error

    except requests.exceptions.ConnectionError as e:
        logger.error(f"WinstonAI API Connection Error: Failed to establish connection. Error: {e}")
        return None, "Network Unreachable" # Previously seen error

    except requests.exceptions.Timeout as e:
        logger.error(f"WinstonAI API Timeout Error: Request timed out. Error: {e}")
        return None, "API Timeout"

    except requests.exceptions.RequestException as e:
        logger.error(f"WinstonAI API Generic Request Error: {e}")
        return None, "API Request Failed"

    except ValueError as e: # Catch JSON decoding errors
        logger.error(f"WinstonAI API response not valid JSON. Error: {e}")
        return None, "Invalid API Response"


def calculate_burstiness(text):
    if not text.strip():
        return 0.0
    tokens = nltk.word_tokenize(text.lower())
    stop_words = set(stopwords.words('english'))
    tokens = [token for token in tokens if token not in stop_words and token not in string.punctuation]
    if not tokens:
        return 0.0
    word_freq = FreqDist(tokens)
    repeated_count = sum(count > 1 for count in word_freq.values())
    if len(word_freq) == 0:
        return 0.0
    burstiness_score = repeated_count / len(word_freq)
    return burstiness_score


def get_top_repeated_words(text):
    if not text.strip():
        return []
    tokens = text.split()
    stop_words = set(stopwords.words('english'))
    tokens = [token.lower() for token in tokens if token.lower() not in stop_words and token.lower() not in string.punctuation]
    if not tokens:
        return []
    word_counts = Counter(tokens)
    return word_counts.most_common(10)
