from math import ceil
import re
import os
from bs4 import BeautifulSoup
from nltk.tokenize import sent_tokenize # Uncomment if you install NLTK for sentence tokenization
from nltk.corpus import stopwords # Uncomment if you install NLTK for robust stop words
# from nltk.stem import PorterStemmer, WordNetLemmatizer # Uncomment for stemming/lemmatization

# Make sure you've installed required libraries:
# pip install beautifulsoup4
# pip install lxml # A fast HTML parser for BeautifulSoup
# pip install html5lib # Another HTML parser, used by your code, ensure it's installed

# If using NLTK features:
# pip install nltk
# import nltk
# nltk.download('punkt') # For sent_tokenize
# nltk.download('stopwords') # For more comprehensive stop words
# nltk.download('wordnet') # For lemmatization

# --- GLOBAL SETTINGS / INITIALIZATIONS ---
# Initialize stemmer/lemmatizer once if using
# stemmer = PorterStemmer()
# lemmatizer = WordNetLemmatizer()
nltk_stop_words = set(stopwords.words('english')) # More comprehensive list


# --- TEXT NORMALIZATION FUNCTIONS ---

def normalize_text(text):
    """
    Applies comprehensive text normalization steps:
    - Lowercasing
    - Removing HTML entities (if any remain)
    - Removing all non-alphanumeric characters (except spaces)
    - Reducing multiple spaces to single spaces
    - (Optional) Unicode normalization
    """
    if not isinstance(text, str): # Handle non-string input gracefully
        return ""
        
    text = text.lower() # 1. Lowercasing
    
    # Remove any remaining HTML entities (like &amp;)
    text = BeautifulSoup(text, 'html.parser').get_text()

    # Keep only alphanumeric characters and spaces
    # re.sub(r'[^a-z0-9\s]', '', text) - if you want to remove hyphens too
    # Your current regex keeps ' and - : [^a-zA-Z0-9\'-]+
    # Let's use a slightly more general one for now that keeps only word characters and spaces
    text = re.sub(r'[^\w\s]', ' ', text) # Remove non-word characters (including most punctuation)
                                       # '\w' matches alphanumeric + underscore
    
    # Normalize unicode characters to ASCII equivalents if possible (e.g., é -> e)
    # This might remove some non-English characters. Use with caution based on your data.
    # import unicodedata
    # text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')

    text = re.sub(r'\s+', ' ', text).strip() # Reduce multiple spaces to single, and trim whitespace
    return text


def remove_stopwords_from_text(text, custom_stop_words=None):
    """Removes stop words from a given text string."""
    words = text.split()
    # Use NLTK's stop words if available and no custom list is provided
    # current_stop_words = custom_stop_words if custom_stop_words is not None else set(stop_words())
    # If NLTK stop words are available and preferred, use:
    current_stop_words = custom_stop_words if custom_stop_words is not None else nltk_stop_words
    
    filtered_words = [word for word in words if word not in current_stop_words]
    return ' '.join(filtered_words)


# def apply_stemming_or_lemmatization(text):
#     """Applies stemming or lemmatization to the text."""
#     words = text.split()
#     # For stemming:
#     # stemmed_words = [stemmer.stem(word) for word in words]
#     # For lemmatization: (requires part-of-speech tagging for best results, simple version below)
#     # lemmatized_words = [lemmatizer.lemmatize(word) for word in words]
#     # return ' '.join(stemmed_words) # or lemmatized_words
#     return text # Placeholder if not using


# --- CHUNKING STRATEGY ---

# TODO Change this (et al) into generators? (yield instead of .append??)
def split_into_chunks(
    text,
    num_words=12,
    overlap_words=6,
    ignore_chunks_below_num_words=3,
    remove_stopwords=False,
    filter_poor_quality=False
):
    """
    Splits text into overlapping chunks, ensuring all content is considered, including short final parts.
    Parameters:
    - text: full document text (normalized outside or inside)
    - num_words: desired number of words per chunk
    - overlap_words: number of overlapping words between chunks
    - ignore_chunks_below_num_words: minimum length to include a chunk
    - remove_stopwords: whether to apply stopword removal before chunking
    - filter_poor_quality: placeholder for applying additional filtering (currently unused)
    """
    # 1. Normalize text
    processed_text = normalize_text(text)

    # 2. Optionally remove stopwords
    if remove_stopwords:
        processed_text = remove_stopwords_from_text(processed_text)

    words = processed_text.split()
    chunks = []

    if not words:
        return []

    # Step size = how far to move forward between chunks
    step_size = max(1, num_words - overlap_words)

    # 3. Main chunking loop
    for i in range(0, len(words), step_size):
        sub_words = words[i: i + num_words]

        if len(sub_words) >= ignore_chunks_below_num_words:
            chunk = ' '.join(sub_words)
            chunks.append(chunk)

    # 4. Check for a leftover final part (not included due to step size)
    if len(words) % step_size != 0:
        remaining_words = words[-(len(words) % step_size):]
        if len(remaining_words) >= ignore_chunks_below_num_words:
            chunk = ' '.join(remaining_words)
            if chunk not in chunks:
                chunks.append(chunk)

    return chunks


# --- EXISTING FUNCTIONS (Potentially Modified) ---

def stop_words():
    # It's better to store this as a set for faster lookup, especially if the list is long.
    return ["a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't", "as",
            "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can't",
            "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
            "each", "few", "for", "from", "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd",
            "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
            "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it'd", "it'll", "it's", "its",
            "itself", "let's", "me", "more", "most", "must", "mustn't", "my", "myself", "no", "nor", "not", "of", "off",
            "on", "once", "only", "or", "other", "ought", "our", "ours", "out", "over", "own", "same", "she", "she'd",
            "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that'll", "that's", "the",
            "their", "theirs", "them", "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
            "they've", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we",
            "we'd", "we'll", "we're", "we've", "went", "were", "weren't", "what", "what's", "when", "when's", "where",
            "where's", "which", "while", "who", "who's", "whom", "why", "with", "won't", "would", "wouldn't", "you",
            "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", ]


def stop_phrases():
    return ["share this article", "all rights reserved", "contact us", "privacy policy", ]


def calculate_unique_score_for_chunk(chunk, stop_words_set=None, stop_phrases_list=None):
    """ Calculate the uniqueness (and add to parent score) of the given 'chunk'.
        This is calculated as (numWords - numStopWords) / numWords - i.e. higher is better.
            # Score +1 if the uniqueness is >= 35% and < 50%
            # Score +2 if the uniqueness is >= 50% and < 70%
            # Score +3 if the uniqueness is >= 70% and < 90%
            # Score +4 if the uniqueness is >= 90%
        The only caveat is that if a stop phrase is encountered, the score is set to -9 before uniqueness is calculated
    """
    # Use provided sets/lists or default to calling the functions
    current_stop_words = stop_words_set if stop_words_set is not None else set(stop_words())
    current_stop_phrases = stop_phrases_list if stop_phrases_list is not None else stop_phrases()

    for stop in current_stop_phrases:
        if stop in chunk:
            return -9 # This chunk is a stop phrase, mark as very low quality

    words = chunk.split()
    num_words = len(words)
    if num_words == 0: # Avoid division by zero
        return 0

    num_stopword_intersection = len([word for word in words if word.lower() in current_stop_words])

    unique_perc = (num_words - num_stopword_intersection) / num_words

    if 0.35 <= unique_perc < 0.5:
        return 1
    elif 0.5 <= unique_perc < 0.7:
        return 2
    elif 0.7 <= unique_perc < 0.9:
        return 3
    elif unique_perc >= 0.9:
        return 4
    else:
        return 0


def choose_bs_parser(html):
    """ If the HTMl5 doctype or tags are present, use the HTML5 parser. Else, use the standard Python parser."""
    if re.match(r"<(section|nav|article|aside|header|footer|main).*?>", html) or re.match(r"<!DOCTYPE html>", html, re.IGNORECASE):
        return "html5lib"
    else:
        return "html.parser"


def html_to_basic_text(html):
    """
    Converts HTML to basic text, applying initial cleaning.
    """
    try:
        soup = BeautifulSoup(html, choose_bs_parser(html))
        # Get all text, then normalize it further
        basic_text = soup.get_text()
        return normalize_text(basic_text) # Use the new normalize_text function
    except Exception as e:
        print(f"Error processing HTML to basic text: {e}")
        return ''


def generate_ngrams(text, n=3):
    """Generates N-grams from a given text."""
    # It's usually best to normalize text before generating ngrams
    normalized_text = normalize_text(text)
    words = normalized_text.split(' ')
    ngrams = []
    for w in range(len(words) - n + 1):
        ngram = ' '.join(words[w:w + n])
        ngrams.append(ngram)
    return ngrams


def amend_filepath_slashes(path):
    alt_sep = ("\\" if os.sep == "/" else "/")
    return path.replace(os.sep, alt_sep).replace(alt_sep, os.sep)