from django.conf import settings
from django.shortcuts import render
from .forms import TextForm
import pysolr

def home(request):
    form = TextForm()
    return render(request, 'home.html', {'form': form})


def search(request):
    # 1. Get Parameters from the Horizontal Search Bar
    query = request.GET.get('q', '').strip()
    # Default to wildcard if empty to show all 14,715 records
    solr_query = f"text_clean:{query}~4" if query else "*:*"
    
    # 2. Pagination Logic (10 results per box)
    page = int(request.GET.get('page', 1))
    rows_per_page = 10
    start_index = (page - 1) * rows_per_page

    # 3. Setup Solr Parameters
    solr_params = {
        'facet': 'on',
        'facet.field': 'final_class',
        'rows': rows_per_page,
        'start': start_index,
        'sort': request.GET.get('sort', 'rank_score desc'),
        'fq': []
    }

    # 4. Apply Advanced Filters (Horizontal Accordion)
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date or end_date:
        s = f"{start_date}T00:00:00Z" if start_date else "*"
        e = f"{end_date}T23:59:59Z" if end_date else "*"
        solr_params['fq'].append(f"created_at:[{s} TO {e}]")

    polarity = request.GET.get('polarity')
    if polarity:
        solr_params['fq'].append(f"polarity:{polarity}")

    # 5. Execute Solr Search
    solr = pysolr.Solr(settings.SOLR_URL, timeout=10)
    search_results = solr.search(solr_query, **solr_params)

    # 6. Calculate Sentiment Distribution for Analytics Modal
    stats = {}
    total_found = search_results.hits
    if total_found > 0:
        facets = search_results.facets.get('facet_fields', {}).get('final_class', [])
        for i in range(0, len(facets), 2):
            label, count = facets[i], facets[i+1]
            stats[label] = round((count / total_found) * 100, 2)

    # 7. Pagination Meta for Template
    total_pages = (total_found // rows_per_page) + (1 if total_found % rows_per_page > 0 else 0)

    context = {
        'results': search_results.docs,
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