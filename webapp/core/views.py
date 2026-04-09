from django.conf import settings
from django.shortcuts import render
from .forms import TextForm
import pysolr
from datetime import datetime, timezone

def home(request):
    form = TextForm()
    return render(request, 'home.html', {'form': form})


def search(request):
    #1. Get Parameters from the Horizontal Search Bar
    query = request.GET.get('q', '').strip()
    #Default to wildcard if empty to show all 14,715 records
    solr_query = f"text_clean:{query}~4" if query else "*:*"
    
    #2. Pagination Logic (10 results per box)
    page = int(request.GET.get('page', 1))
    rows_per_page = 10
    start_index = (page - 1) * rows_per_page

    #3. Setup Solr Parameters
    solr_params = {
        'facet': 'on',
        'facet.field': 'final_class',
        'rows': rows_per_page,
        'start': start_index,
        'sort': request.GET.get('sort', 'rank_score desc'),
        'fq': []
    }

    #4. Apply Advanced Filters (Horizontal Accordion)
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date or end_date:
        try:
            s = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() if start_date else "*"
        except ValueError:
            s = "*"
        try:
            e = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() if end_date else "*"
        except ValueError:
            e = "*"
        solr_params['fq'].append(f"date:[{s} TO {e}]")

    polarity = request.GET.get('polarity')
    if polarity:
        solr_params['fq'].append(f"polarity:[{polarity} TO {polarity}]")

    record_type = request.GET.get('record_type')
    if record_type:
        solr_params['fq'].append(f"record_type:{record_type}")

    #5.Solr Search
    solr = pysolr.Solr(settings.SOLR_URL, timeout=10)
    search_results = solr.search(solr_query, **solr_params)

    #Normalize Solr docs: unwrap single-element lists to plain scalars
    def unwrap(val):
        if isinstance(val, list):
            return val[0] if val else ""
        return val

    def fmt_date(val):
        try:
            return datetime.fromtimestamp(float(val), tz=timezone.utc).strftime("%d/%m/%Y")
        except Exception:
            return val

    def normalize(doc):
        d = {k: unwrap(v) for k, v in doc.items()}
        if d.get("date"):
            d["date"] = fmt_date(d["date"])
        return d

    docs = [normalize(doc) for doc in search_results.docs]

    #6.Calculate Sentiment Distribution for Analytics Modal
    stats = {}
    total_found = search_results.hits
    if total_found > 0:
        facets = search_results.facets.get('facet_fields', {}).get('final_class', [])
        for i in range(0, len(facets), 2):
            label, count = facets[i], facets[i+1]
            stats[label] = round((count / total_found) * 100, 2)

    # 7. Pagination
    total_pages = (total_found // rows_per_page) + (1 if total_found % rows_per_page > 0 else 0)

    context = {
        'results': docs,
        'query': query,
        'stats': stats,
        'qtime': search_results.qtime,
        'total_hits': total_found,
        'page': page,
        'total_pages': total_pages,
        'has_next': page < total_pages,
        'has_prev': page > 1,
        'next_page': page + 1,
        'prev_page': page - 1,
    }
    return render(request, 'search.html', context)