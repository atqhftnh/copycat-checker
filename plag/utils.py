# plag/utils.py

import io
import urllib.request
from urllib.error import HTTPError, URLError
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams # Used for better text layout analysis
from typing import Optional # Or from typing import Union

def extract_text_from_pdf_url(pdf_url: str) -> Optional[str]:
    """
    Downloads a PDF from a URL and extracts its text content using pdfminer.six.

    Args:
        pdf_url: The URL of the PDF file.

    Returns:
        The extracted text content as a string, or None if extraction fails.
    """
    try:
        # Add a User-Agent header to mimic a browser, as some servers block default Python user-agents
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        req = urllib.request.Request(pdf_url, headers=headers)

        with urllib.request.urlopen(req, timeout=15) as response: # Increased timeout for potentially larger PDFs
            pdf_bytes = response.read()

        # Use io.StringIO to capture the extracted text
        text_buffer = io.StringIO()

        # LAParams helps preserve the reading order and layout of the text
        # You can adjust parameters like char_margin, word_margin, line_margin for fine-tuning
        laparams = LAParams()

        # extract_text_to_fp writes text to a file-like object
        extract_text_to_fp(io.BytesIO(pdf_bytes), text_buffer, laparams=laparams)

        extracted_text = text_buffer.getvalue()
        return extracted_text

    except (HTTPError, URLError) as e:
        print(f"Error fetching PDF from {pdf_url}: {e}")
        return None
    except Exception as e:
        print(f"Error extracting text from PDF {pdf_url}: {e}")
        return None