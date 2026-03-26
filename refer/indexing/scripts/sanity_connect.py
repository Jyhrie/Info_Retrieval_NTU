# from urllib.request import urlopen
# from urllib.parse import urlencode, quote
# import json
import pysolr
import time

# Build the query
base_url = "http://localhost:8983/solr/mycollection"

#connect to solr
solr = pysolr.Solr(base_url, always_commit=True, timeout=10)

# params = {
#     "q": 'body:"stock options" AND type:post',
#     "wt": "json",        # get results in JSON
#     "rows": 10,          # limit results
#     "sort": "score desc" # sort by score
# }

# full_url = base_url + urlencode(params, quote_via=quote)


# ------------------------- Test One Query first -------------------------
params = {
    "rows": 5,
    "sort": "score desc"
}

query = 'comment_content:moomoo AND subreddit:webull'

start = time.time()
results = solr.search(query, **params)
end = time.time()

print("Results: ", len(results))
print("Time taken: {:.3f} seconds".format(end-start))
for doc in results:
    print(doc)

# ------------------------- Test Multiple Queries -------------------------
query_list = [
    'comment_content:"bad"',
    'comment_content:"moomoo" AND subbreddit:webull',
    'score:[30 TO *]'
    'subreddit:moomoo_official',
    'comment_content:"horrible" OR comment_content:"IBKR"',
]

for q in query_list:
    start = time.time()
    results = solr.search(q, rows=5)
    end = time.time()

    print(f"Query: {q}")
    print(f" - Results: {len(results)}")
    print(f" - Time: {end - start:.4f}s\n")
