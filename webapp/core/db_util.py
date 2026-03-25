import pysolr
from django.conf import settings

# Pull the URL from your settings.py
# Fallback to 127.0.0.1 to avoid the Windows localhost/IPv6 issue
SOLR_URL = getattr(settings, 'HAYSTACK_CONNECTIONS', {}).get('default', {}).get('URL', 'http://127.0.0.1:8983/solr/info_retrieval')

class SolrManager:
    def __init__(self, url=SOLR_URL):
        self.solr = pysolr.Solr(url, always_commit=True, timeout=10)

    def upload_data(self, docs):
        try:
            self.solr.add(docs)
            return {"status": "success", "message": f"Indexed {len(docs)} documents."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_data(self, query="*:*", rows=10):
        try:
            results = self.solr.search(query, rows=rows)
            # results.docs is the list of dictionaries returned by Solr
            return {
                "status": "success",
                "total_found": results.hits,
                "data": results.docs
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # def delete_all(self):
    #     """Clears the entire index. Use with caution!"""
    #     self.solr.delete(q='*:*')
    #     return {"status": "success", "message": "Index cleared."}