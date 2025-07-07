import requests
from django.conf import settings
import re

def run_request(queries, exclude_urls=[]):
    result = []
    print(f"DEBUG (run_request): run_request received {len(queries)} queries. Type: {type(queries)}")
    for query in queries:
        try:
            api_result = requests.get(
                settings.GOOGLE_SEARCH_API_ENDPOINT,
                params={
                    "key": settings.GOOGLE_SEARCH_API_KEY,
                    "cx": settings.GOOGLE_SEARCH_ENGINE_ID,
                    "q": query,
                    "num": 10, # Number of search results to retrieve per query
                    }
                )
            api_result.raise_for_status()

            data = api_result.json()
            if "items" in data:
                for item in data["items"]:
                    item_link = item.get('link', '')
                    item_title = item.get('title', '')
                    item_snippet = item.get('snippet', '')
                    item_display_link = item.get('displayLink', item_link)

                    # Only add if not in excluded_urls and not a duplicate URL
                    if item_link not in exclude_urls and not any(d.get('url') == item_link for d in result):
                        result.append({
                            'displayurl': item_display_link,
                            'desc': item_snippet,
                            'url': item_link,
                            'title': item_title,
                            'query': query # Store the original query for context
                        })
            # else: # You might not want to print this for every query with no items
            #      print(f"No items found in Google Custom Search API response for query: '{query}'")

        except requests.exceptions.RequestException as e:
            # print(f"Google Custom Search API error for query '{query}': {e}") # Log this carefully in production
            # For robust production, consider returning an error flag or handling gracefully
            pass # Continue to next query if one fails
    return result

def add_result(api_row, result_list, excluded_urls):
    # This function is not used in your `run_request` but is present.
    # Its logic is duplicated inside `run_request`.
    # You might want to refactor `run_request` to use this helper.
    if api_row.get('url') not in excluded_urls and not any(d.get('url') == api_row.get('url') for d in result_list):
        result_list.append({
            'displayurl': api_row.get('displayurl', ''),
            'desc': api_row.get('desc', ''),
            'url': api_row.get('url', ''),
            'title': api_row.get('title', '')
        })

def build_query_result(chunks_with_scores, num_queries, source=''):
    """
    Builds the query result dictionary.
    If num_queries is None, returns all scored chunks as data.
    Otherwise, sorts and returns the top num_queries chunks.
    """
    if not chunks_with_scores:
        return {
            'success': False,
            'data': [],
            'source': source
        }

    if num_queries is None:
        # If num_queries is None, return all queries (the text part of the tuple)
        # You might still want to sort them, perhaps by initial score, even if returning all.
        # Let's sort them to maintain consistent order, for example.
        sorted_chunks = sorted(chunks_with_scores, key=lambda score: score[1], reverse=True)
        data_to_return = [top_text[0] for top_text in sorted_chunks]
    else:
        # Original logic: sort by score and take the top N
        sorted_chunks = sorted(chunks_with_scores, key=lambda score: score[1], reverse=True)[:num_queries]
        data_to_return = [top_text[0] for top_text in sorted_chunks]

    return {
        'success': True,
        'data': data_to_return,
        'source': source
    }