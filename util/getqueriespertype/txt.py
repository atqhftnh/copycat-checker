from util.textcleanup import split_into_chunks, calculate_unique_score_for_chunk, normalize_text
from util.handlequeries import build_query_result


def get_queries(source, num_queries=3):
    scored_chunks = []

    for chunk in split_into_chunks(source, filter_poor_quality=True):
        score = calculate_unique_score_for_chunk(chunk)
        scored_chunks.append((normalize_text(chunk), score))

    return build_query_result(scored_chunks, num_queries, source=source)