from django.conf import settings
from django.shortcuts import render
from .forms import TextForm
import pysolr
from datetime import datetime, timezone
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import re
from collections import Counter


STOPWORDS = set(stopwords.words('english'))
lemmatizer = WordNetLemmatizer()

DDL_OPTIONS = {
    'tool': [
        'cursor', 'claude_code', 'codex', 'copilot', 'gemini', 
        'replit', 'aider', 'windsurf', 'cline', 'opencode'
    ],
    'reason': ['speed', 'code_quality', 'correctness', 'ux', 'integrations'],
    'workflow': ['prototyping', 'debugging', 'refactoring', 'testing'],
    'trust': ['production', 'reliability', 'hallucination', 'privacy'],
}

def home(request):
    form = TextForm()
    return render(request, 'home.html', {'form': form})

def search(request):
    solr = pysolr.Solr(settings.SOLR_URL, timeout=10)

    query = request.GET.get('q', '').strip()
    if query:
        clean_query = re.sub(r'[^a-zA-Z\s]', '', query.lower())
        words = clean_query.split()
        meaningful_words = [
            lemmatizer.lemmatize(w, pos='v') 
            for w in words 
            if w not in STOPWORDS and len(w) > 2
        ]

        if not meaningful_words:
            meaningful_words = words

        solr_query = " AND ".join([f"text_index:{word}~1" for word in meaningful_words])
    else:
        solr_query = "*:*"
    
    # 2. Pagination Logic
    page = int(request.GET.get('page', 1))
    rows_per_page = 10
    start_index = (page - 1) * rows_per_page

    solr_params = {
        'facet': 'on',
        'facet.field': ['final_class_str', 'text_clean_tokens'],
        'facet.limit': rows_per_page,
        'f.text_clean_tokens.facet.limit': 100,
        'f.text_clean_tokens.facet.mincount': 5,
        'rows': rows_per_page,
        'start': start_index,
        'sort': request.GET.get('sort', 'rank_score desc'),
        'fq': []
    }

    # 4. Apply Advanced Filters
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

    for field in ['tool', 'reason', 'workflow', 'trust']:
        val = request.GET.get(field)
        if val:
            solr_params['fq'].append(f'{field}:"{val}"')

    search_results = solr.search(solr_query, **solr_params)

    # Helper Functions
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

    stats = {}
    total_found = search_results.hits
    final_class_facets = search_results.facets.get('facet_fields', {}).get('final_class_str', [])
    if total_found > 0:
        for i in range(0, len(final_class_facets), 2):
            label, count = final_class_facets[i], final_class_facets[i+1]
            stats[label] = count

    raw_text_facets = search_results.facets.get('facet_fields', {}).get('text_clean_tokens', [])
    cloud_data = []
    
    for i in range(0, len(raw_text_facets), 2):
        word, count = raw_text_facets[i].lower(), raw_text_facets[i+1]
        # Filter: ignore stopwords, short words, and pure numbers
        if word not in STOPWORDS and len(word) > 2 and not word.isdigit():
            cloud_data.append([word, count])

    # word_counter = Counter()
    # if total_found > 0:
    #     cloud_results = solr.search(solr_query, fl='text_clean', rows=total_found, fq=solr_params['fq'])
    #     for doc in cloud_results.docs:
    #         text = doc.get('text_clean', '')
    #         if isinstance(text, list):
    #             text = ' '.join(text)
    #         for word in re.findall(r'[a-z]+', text.lower()):
    #             if word not in STOPWORDS and len(word) > 2 and not word.isdigit():
    #                 word_counter[word] += 1
    # cloud_data = [[word, count] for word, count in word_counter.most_common(50)]

    # 8. Pagination
    total_pages = (total_found // rows_per_page) + (1 if total_found % rows_per_page > 0 else 0)

    context = {
        'results': docs,
        'query': query,
        'stats': stats,
        'cloud_data': cloud_data[:50],  # Pass top 50 filtered words
        'qtime': search_results.qtime,
        'total_hits': total_found,
        'page': page,
        'total_pages': total_pages,
        'has_next': page < total_pages,
        'has_prev': page > 1,
        'next_page': page + 1,
        'prev_page': page - 1,
        'all_tools': DDL_OPTIONS['tool'],
        'all_reasons': DDL_OPTIONS['reason'],
        'all_workflows': DDL_OPTIONS['workflow'],
        'all_trust_levels': DDL_OPTIONS['trust'],
    }
    return render(request, 'search.html', context)