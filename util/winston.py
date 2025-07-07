import os
import requests
import nltk
from nltk.corpus import stopwords
import string
from collections import Counter
from nltk.probability import FreqDist

WINSTON_AI_API_KEY = "CP95u8a7Jy5Yw6jS7L1sSERCsKyd2u11e2W8cCOg30b8c6bc"
WINSTON_AI_API_URL = "https://api.gowinston.ai/v2/ai-content-detection"

def detect_ai_content(text):
    """
    Uses WinstonAI to detect if the provided text is likely AI-generated.

    Returns:
        tuple: (ai_probability_score as float, label as str)
    """
    if not text.strip():
        return -1, "No text"

    headers = {
        "Authorization": f"Bearer {WINSTON_AI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "text": text,
        "sentences": True,
        "language": "en"
    }

    try:
        response = requests.post(WINSTON_AI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        if "score" in data:
            human_score = data["score"]  # e.g., 92 means 92% human
            ai_score = round(100 - human_score, 2)  # AI score = 100 - human score
            label = "Likely AI-Generated" if ai_score >= 50 else "Likely Human-Written"
            return ai_score, label
        else:
            return -1, "Invalid response"

    except requests.exceptions.RequestException as e:
        print(f"WinstonAI API error: {e}")
        return -1, "API Error"
    except Exception as e:
        print(f"Unexpected error during AI detection: {e}")
        return -1, "Unexpected Error"
    

def get_winston_ai_prediction(text):
    if not text.strip():
        return None

    if not WINSTON_AI_API_KEY:
        print("WinstonAI API Key not set in environment variables.") # Log to console
        return None

    headers = {
        "Authorization": f"Bearer {WINSTON_AI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": text,
        "sentences": True,
        "language": "en"
    }

    try:
        response = requests.post(WINSTON_AI_API_URL, headers=headers, json=payload)
        response.raise_for_status() 
        data = response.json()
        
        if 'score' in data:
            human_score = data['score'] 
            ai_probability = (100 - human_score) / 100.0 
            return ai_probability
        else:
            print(f"WinstonAI API response did not contain expected 'score' field. Response: {data}")
            return None

    except requests.exceptions.RequestException as e: 
        print(f"Error calling WinstonAI API: {e}. Response: {e.response.text if e.response else 'No response'}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred in WinstonAI prediction: {e}")
        return None

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
