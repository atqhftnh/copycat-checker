import re, subprocess, os
import logging
from django.conf import settings

from util.textcleanup import calculate_unique_score_for_chunk, split_into_chunks, normalize_text
from util.handlequeries import build_query_result

logger = logging.getLogger(__name__)

def get_queries(filename, num_queries=10):
    '''
    :param filename: The filename for the PDF
    :param num_queries: number of top-scored text chunks to return as queries
    :return: list of (chunk, score) tuples
    '''
    scored_chunks = []
    absolute_file_path = os.path.join(settings.MEDIA_ROOT, filename)

    print(f"DEBUG (pdf.py): settings.PDF_TO_TEXT: '{settings.PDF_TO_TEXT}'")
    print(f"DEBUG (pdf.py): Does PDF_TO_TEXT file exist? {os.path.isfile(settings.PDF_TO_TEXT)}")
    print(f"DEBUG (pdf.py): Is PDF_TO_TEXT executable? {os.access(settings.PDF_TO_TEXT, os.X_OK)}")
    print(f"DEBUG (pdf.py): Absolute input PDF path: '{absolute_file_path}'")
    print(f"DEBUG (pdf.py): Does input PDF file exist? {os.path.isfile(absolute_file_path)}")

    pdf_to_text_output = subprocess.check_output([settings.PDF_TO_TEXT, "-layout", absolute_file_path, "-"])
    try:
        text = pdf_to_text_output.decode('utf-8')
    except UnicodeDecodeError:
        text = pdf_to_text_output.decode('ISO-8859-1')

    print(f"DEBUG: Full extracted text:\n{text}\n---")

    # NEW: use enhanced chunking (with short final chunk handling)
    chunks = split_into_chunks(
        text,
        num_words=12,
        overlap_words=6,
        ignore_chunks_below_num_words=3,
        remove_stopwords=False
    )

    print(f"DEBUG: Total chunks from split_into_chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}: {chunk}")

    # Score each chunk
    for chunk in chunks:
        num_words_len3 = sum(1 for word in chunk.split() if len(word) >= 3)
        score = 1 if num_words_len3 >= 8 else 0

        word_no_whitespace = chunk.replace(' ', '')
        word_only_alpha = re.sub(r'[^a-zA-Z]+', '', word_no_whitespace)
        if len(word_no_whitespace) > 0 and (len(word_only_alpha) / len(word_no_whitespace)) > 0.75:
            score += 1

        scored_chunks.append((chunk, score))

    print(f"DEBUG (get_queries): Total scored_chunks: {len(scored_chunks)}")
    if scored_chunks:
        print(f"DEBUG (get_queries): Top 5 scored_chunks:\n{scored_chunks[:5]}")

    # Prioritize chunks with score == 2
    full_score_chunks = [chunk for chunk in scored_chunks if chunk[1] == 2]
    print(f"DEBUG (get_queries): Total full_score_chunks (score == 2): {len(full_score_chunks)}")

    if full_score_chunks:
        print(f"DEBUG (get_queries): First few full_score_chunks:\n{full_score_chunks[:5]}")
    else:
        print("WARNING: No high-quality chunks scored 2 — this may reduce result quality.")

    # Use uniqueness score if too many good chunks
    if len(full_score_chunks) > num_queries:
        print("INFO: Using uniqueness scoring to refine chunks.")
        scored_chunks = []
        for chunk_text, base_score in full_score_chunks:
            unique_score = calculate_unique_score_for_chunk(chunk_text)
            scored_chunks.append((chunk_text, base_score + unique_score))

    return build_query_result(scored_chunks, num_queries, source=text)
