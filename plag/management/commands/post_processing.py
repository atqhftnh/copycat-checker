import urllib.request
from urllib.error import HTTPError, URLError
from socket import timeout
import threading
import os 

from django.core.management.base import BaseCommand
from django.conf import settings 

from plag.models import ScanResult, ScanLog, Query 
from util.textcleanup import html_to_basic_text, normalize_text, generate_ngrams, remove_stopwords_from_text

QUERY_PRESENCE_THRESHOLD = 0.20

class Command(BaseCommand):
    help = 'Gets N scan result histories, and sees whether they are real matches or not - if the former, calculate a % of duplication (via Y threads)'

    scan_results = []
    current_result_idx = 0
    lock = threading.Lock()

    def add_arguments(self, parser):
        parser.add_argument('num_resources_to_scan', type=int,
                            help='Number of scan results to process')
        parser.add_argument('number_of_threads', type=int,
                            help='Number of threads to use for processing')

    def process_result(self, thread_id):
        self.stdout.write(f'Thread #{thread_id} starting')

        while True:
            result = None
            with self.lock:
                if self.current_result_idx < len(self.scan_results):
                    result = self.scan_results[self.current_result_idx]
                    self.current_result_idx += 1
                else:
                    break 

            if result:
                try:
                    post_process_result(result)
                except Exception as e:
                    self.stderr.write(f"ERROR: Thread #{thread_id} failed to process ScanResult ID {result.id}: {e}")
                    if not result.post_scanned: 
                        result.perc_of_duplication = -2 
                        result.post_fail_reason = f"Internal processing error: {e}"
                        result.post_fail_type = ScanLog.E 
                        result.post_scanned = True
                        result.save()

        self.stdout.write(f'Thread #{thread_id} ending')

    def handle(self, *args, **options):
        num_to_scan = options['num_resources_to_scan']
        num_threads = options['number_of_threads']

        self.stdout.write(f"Fetching {num_to_scan} scan results for post-processing with {num_threads} threads...")

        self.scan_results = list(
            ScanResult.objects.filter(post_scanned=False, post_fail_type__isnull=True)
            .order_by('timestamp')
            .select_related('query') 
            [:num_to_scan]
        )
        
        if not self.scan_results:
            self.stdout.write(self.style.WARNING("No scan results found for post-processing."))
            return

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=self.process_result, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()

        self.stdout.write(self.style.SUCCESS(f'Successfully completed post-processing for {len(self.scan_results)} scan results.'))


def post_process_result(result):
    """
    Performs post-processing for a single ScanResult, including false positive checks
    and calculating the individual query's duplication percentage.
    """
    # Initial check: Ensure the ScanResult has a valid associated Query object
    if not hasattr(result, 'query') or not result.query or not result.query.query:
        result.perc_of_duplication = 0.0 # Set to 0.0 for clarity if no query
        result.post_fail_reason = 'Internal Error: ScanResult is missing associated Query text.'
        result.post_fail_type = ScanLog.E # 'E' for Error
        result.post_scanned = True
        result.save()
        print(f"ERROR: ScanResult ID {result.id} is missing associated Query text. Skipping.")
        return result

    original_specific_query_text = result.query.query

    print(f"\n--- Post-processing Debug for ScanResult ID: {result.id} ---")
    print(f"Matched URL: {result.match_url}")
    original_query_preview = original_specific_query_text[:100].replace('\n', ' ').strip()
    print(f"Original Specific Query Text (from DB): '{original_query_preview}...'")

    # Skip processing if matched URL is a document file type (as per your existing TODO)
    # You might want to implement actual document parsing here in the future
    if result.match_url.lower().endswith(('doc', 'docx', 'pdf', 'pptx')):
        result.perc_of_duplication = 0.0
        result.post_fail_reason = 'Skipped: Matched URL is a document file type (not processed).'
        result.post_fail_type = ScanLog.I # 'I' for Ignored
        result.post_scanned = True
        result.save()
        print(f"SKIPPED: ScanResult ID {result.id}. Matched URL is a document file type.")
        return result

    url_text = ""
    # Attempt to fetch content from the matched URL
    try:
        req = urllib.request.Request(result.match_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.63 Safari/537.36'
        })
        with urllib.request.urlopen(req, timeout=10) as response:
            url_result = response.read()
            try:
                url_text = url_result.decode('utf-8')
            except UnicodeDecodeError:
                url_text = url_result.decode('ISO-8859-1', errors='ignore')
    except (HTTPError, URLError) as e:
        result.perc_of_duplication = 0.0
        result.post_fail_reason = f'URL Fetch Error: {str(e)}'
        result.post_fail_type = ScanLog.H # 'H' for HTTP error
        result.post_scanned = True
        result.save()
        print(f"ERROR: ScanResult ID {result.id} - URL Fetch Error for {result.match_url}: {e}")
        return result
    except timeout as t:
        result.perc_of_duplication = 0.0
        result.post_fail_reason = 'URL timed out'
        result.post_fail_type = ScanLog.H
        result.post_scanned = True
        result.save()
        print(f"ERROR: ScanResult ID {result.id} - URL Timed Out for {result.match_url}")
        return result
    except Exception as e: # Catch any other unexpected errors during URL fetch
        result.perc_of_duplication = 0.0
        result.post_fail_reason = f'Unexpected URL Fetch/Decode Error: {str(e)}'
        result.post_fail_type = ScanLog.H
        result.post_scanned = True
        result.save()
        print(f"FATAL ERROR: ScanResult ID {result.id} - Unexpected URL Fetch Error for {result.match_url}: {e}")
        return result

    # Check if content was fetched from the URL
    if not url_text.strip():
        result.perc_of_duplication = 0.0
        result.post_fail_reason = 'No content found at URL.'
        result.post_fail_type = ScanLog.C # 'C' for Content related issue
        result.post_scanned = True
        result.save()
        print(f"INFO: ScanResult ID {result.id} - No content fetched from {result.match_url}")
        return result

    # Convert HTML content to basic text
    result_text = html_to_basic_text(url_text)
    if not result_text.strip():
        result.perc_of_duplication = 0.0
        result.post_fail_reason = 'No extractable text from URL content.'
        result.post_fail_type = ScanLog.C
        result.post_scanned = True
        result.save()
        print(f"INFO: ScanResult ID {result.id} - No extractable text from HTML for {result.match_url}")
        return result
    
    # Debug print for extracted URL text
    cleaned_result_text_preview = result_text[:200].replace('\n', ' ').strip()
    print(f"Extracted URL Text (first 200 chars): '{cleaned_result_text_preview}...'")

    # --- FALSE POSITIVE DETECTION LOGIC ---

    # Process the original specific query text
    normalized_specific_query_text = normalize_text(original_specific_query_text)
    normalized_specific_query_text_no_stopwords = remove_stopwords_from_text(normalized_specific_query_text)
    
    # *** FIX HERE: Convert to set ***
    specific_query_trigrams = set(generate_ngrams(normalized_specific_query_text_no_stopwords.lower()))
    
    cleaned_specific_query_preview = normalized_specific_query_text_no_stopwords[:100].replace('\n', ' ').strip()
    print(f"Normalized Specific Query Text (no stopwords): '{cleaned_specific_query_preview}...'")
    print(f"Specific Query Trigrams Count: {len(specific_query_trigrams)}")

    # Process the matched document text from the URL
    normalized_matched_doc_text = normalize_text(result_text)
    normalized_matched_doc_text_no_stopwords = remove_stopwords_from_text(normalized_matched_doc_text)
    
    # *** FIX HERE: Convert to set ***
    matched_doc_trigrams = set(generate_ngrams(normalized_matched_doc_text_no_stopwords.lower()))
    
    cleaned_matched_doc_preview = normalized_matched_doc_text_no_stopwords[:200].replace('\n', ' ').strip()
    print(f"Normalized Matched Doc Text (no stopwords): '{cleaned_matched_doc_preview}...'")
    print(f"Matched Document Trigrams Count: {len(matched_doc_trigrams)}")

    # Calculate common trigrams between the specific query and the matched document
    # This line will now work correctly because both are sets
    common_trigrams_specific = len(specific_query_trigrams.intersection(matched_doc_trigrams))
    print(f"Common Trigrams Count (Specific Query vs. Matched Doc): {common_trigrams_specific}")

    # Calculate Overlap Percentage for the Specific Query vs. Matched Document
    overlap_percentage_specific_query = 0.0
    if len(specific_query_trigrams) > 0:
        overlap_percentage_specific_query = (common_trigrams_specific / len(specific_query_trigrams)) * 100
    print(f"Overlap Percentage (Specific Query vs. Matched Doc): {overlap_percentage_specific_query:.2f}%")

    print(f"Current Query Presence Threshold: {QUERY_PRESENCE_THRESHOLD * 100:.2f}%")

    is_specific_query_sufficiently_present = False
    if len(specific_query_trigrams) > 0:
        if (overlap_percentage_specific_query / 100) >= QUERY_PRESENCE_THRESHOLD:
            is_specific_query_sufficiently_present = True

    # Apply false positive check
    if not is_specific_query_sufficiently_present:
        result.perc_of_duplication = -1.0 # Use -1.0 to clearly mark false positive for JS
        result.post_fail_reason = 'False positive: Specific query not sufficiently found in result content.'
        result.post_fail_type = ScanLog.C
        print(f"--- MARKED AS FALSE POSITIVE (Specific Query): Overlap {overlap_percentage_specific_query:.2f}% < {QUERY_PRESENCE_THRESHOLD * 100:.2f}% ---")
    else:
        # Match Confirmed: Set the individual ScanResult's percentage
        print(f"--- SPECIFIC QUERY PASSED FALSE POSITIVE CHECK ---")
        result.perc_of_duplication = round(overlap_percentage_specific_query, 2) # Store the individual query's overlap
        result.post_fail_reason = "" # Clear any previous fail reason
        result.post_fail_type = None

        # --- DEBUGGING FOR Source Full Doc Trigrams Count: 0 ---
        source_text_full_doc = result.result_log.protected_source
        
        print(f"\n--- DEBUG: Inside post_process_result, processing full source for overall % ---")
        raw_source_full_doc_preview = str(source_text_full_doc)[:200].replace('\n', ' ').strip()
        print(f"DEBUG: Raw result.result_log.protected_source (first 200 chars): '{raw_source_full_doc_preview}...'")
        print(f"DEBUG: Length of raw result.result_log.protected_source: {len(str(source_text_full_doc))}")
        
        source_text_full_doc_cleaned = ""
        if source_text_full_doc:
            try:
                source_text_full_doc_cleaned = html_to_basic_text(str(source_text_full_doc))
            except Exception as e:
                print(f"WARNING: Could not process protected_source for full doc trigrams: {e}. Using raw string as cleaned.")
                source_text_full_doc_cleaned = str(source_text_full_doc)
        else:
            print("WARNING: ScanLog.protected_source is empty. Cannot calculate overall plagiarism accurately.")

        cleaned_full_doc_preview = source_text_full_doc_cleaned[:200].replace('\n', ' ').strip()
        print(f"DEBUG: Cleaned source_text_full_doc_cleaned (first 200 chars): '{cleaned_full_doc_preview}...'")
        print(f"DEBUG: Length of cleaned source_text_full_doc_cleaned: {len(source_text_full_doc_cleaned)}")
        
        normalized_source_full_doc_text = normalize_text(source_text_full_doc_cleaned)
        normalized_source_full_doc_text_no_stopwords = remove_stopwords_from_text(normalized_source_full_doc_text)
        
        normalized_full_doc_no_stopwords_preview = normalized_source_full_doc_text_no_stopwords[:200].replace('\n', ' ').strip()
        print(f"DEBUG: Normalized (no stopwords) source_text_full_doc (first 200 chars): '{normalized_full_doc_no_stopwords_preview}...'")
        print(f"DEBUG: Length of normalized (no stopwords) source_text_full_doc: {len(normalized_source_full_doc_text_no_stopwords)}")

        # *** FIX HERE: Convert to set ***
        source_full_doc_trigrams = set(generate_ngrams(normalized_source_full_doc_text_no_stopwords.lower()))
        
        print(f"Source Full Doc Trigrams Count: {len(source_full_doc_trigrams)}")
        print(f"--- END DEBUG: Processing full source for overall % ---\n")

        print(f"Match Confirmed. This individual match is {result.perc_of_duplication:.2f}% duplicated.")

    result.post_scanned = True # Mark as processed regardless of pass/fail
    result.save() # Save the ScanResult with its final percentage and status

    print(f"Final perc_dup (Individual Result): {result.perc_of_duplication}")
    print(f"Final post_fail_reason: {result.post_fail_reason}")
    print(f"--- End Post-processing Debug for ScanResult ID: {result.id} ---\n")

    return result