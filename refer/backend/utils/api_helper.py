import pysolr
import spacy
import nltk
import torch
import json
import datetime
import os

from NeuralNets.models import build_model
from NeuralNets.utils.tokenizer import build_tokenizer
from NeuralNets.trainer import TrainingArgs
from NeuralNets.dataloader import get_dataloaders_from_list

from collections import Counter
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from sentence_transformers import SentenceTransformer, util
from typing import List, Any, Tuple
from response_model import SolrResponse, Comment, Keyword

# BASE_URL = "http://localhost:8983/solr/mycollection/"
BASE_URL = "http://solr:8983/solr/reddit/" # Solr base URL

model = SentenceTransformer('all-MiniLM-L6-v2')
nlp_en = spacy.load("en_core_web_sm") #spacy model for NLP tasks
nltk.download('punkt_tab')
current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, "../models/classification/config.json")
model_path = os.path.join(current_dir, "../models/classification/model.pth")
with open(config_path, 'r') as f:
    config = json.load(f) # load mddel config file

training_args = TrainingArgs(
**config["trainer_args"]
)
tokenizer = build_tokenizer(config["tokenizer_config"])

aggregation = config['model_config']['args'].get('aggregation', 'last')
if aggregation=='attention':
    config['model_config']['args']['attention'] = True

model_type = config['model_config']['model_type']
model = build_model(config["model_config"], tokenizer=tokenizer)
if os.path.exists(model_path):
    model.load_state_dict(torch.load(model_path, weights_only=True))
    model.to("cuda")
    model.eval()
else:
    raise ValueError('Model file does not exist. Please perform the training step first')

tokenizer = build_tokenizer(config["tokenizer_config"])


def connect_to_solr():
    """
    Connect to solr
    """
    default_params = {
        "rows": 5,
        "sort": "score desc",
    }

    return pysolr.Solr(BASE_URL, always_commit=True, timeout=10), default_params

def get_keywords_from_spacy_and_LDA(documents: List[str]) -> List[Keyword]:
    """
    Uses spacy for smarter tokenization and extract keywords from documentsu using lda as well
    :param documents: list of documents to extract keywords from
    :param top_k: number of top keywords to extract
    :return: list of keywords
    """
    processed_docs = []

    for doc in documents:
        # spacy_doc = nlp_en(doc.lower())
        spacy_doc = [""]
        tokens = [
            token.lemma_ for token in spacy_doc 
            if not token.is_stop and not token.is_punct and token.is_alpha and len(token.lemma_) > 2
        ]
        processed_docs.append(" ".join(tokens))

    # Create CountVectorizer from cleaned text
    if len(processed_docs) < 2:
        vectorizer = CountVectorizer(max_df=1.0, min_df=1, stop_words='english')
    else:
        vectorizer = CountVectorizer(max_df=0.95, min_df=2, stop_words='english')
    X = vectorizer.fit_transform(processed_docs)

    # Apply LDA
    lda = LatentDirichletAllocation(n_components=5, random_state=42)
    lda.fit(X)

    # Get top words per topic
    feature_names = vectorizer.get_feature_names_out()
    top_keywords = set()

    for topic_idx, topic in enumerate(lda.components_):
        top_word_indices = topic.argsort()[:-20 - 1:-1]
        top_words = [feature_names[i] for i in top_word_indices]
        top_keywords.update(top_words)

    # Count occurrences in the original corpus
    word_counts = Counter(" ".join(processed_docs).split())
    
    # Build Keyword objects
    keywords = [Keyword(keyword=word, count=word_counts[word]) for word in top_keywords if word in word_counts]
    return sorted(keywords, key=lambda x: x.count, reverse=True)

def extract_keywords_semantic(query: str, documents: List[str]) -> List[Keyword]:
    """
    Uses sentence transformers to extract keywords from documents using semantic similarity
    :param query: query to extract keywords from
    :param documents: list of documents to extract keywords from
    :param top_k: number of top keywords to extract
    :return: list of keywords
    """
    # combine documents for simplicity
    full_text = " ".join(documents)
    # spacy_doc = nlp_en(full_text.lower())
    spacy_doc = [""]
    candidates = list(set([
        token.lemma_ for token in spacy_doc
        if not token.is_stop and not token.is_punct and token.is_alpha and len(token.lemma_) > 2
    ]))

    # generate embeddings
    query_embedding = model.encode(query, convert_to_tensor=True)
    candidate_embeddings = model.encode(candidates, convert_to_tensor=True)
    similarities = util.pytorch_cos_sim(query_embedding, candidate_embeddings)[0]
    
    keyword_scores = list(zip(candidates, similarities.cpu().numpy()))
    sorted_keywords = sorted(keyword_scores, key=lambda x: x[1], reverse=True)[:20]

    keyword_counts = Counter([
        token.lemma_ for token in spacy_doc
        if token.lemma_ in dict(sorted_keywords)
    ])

    return [Keyword(keyword=keyword, count=keyword_counts[keyword]) for keyword, _ in sorted_keywords if keyword in keyword_counts]

def get_results(query: str, subreddits: List[str], start_date: str) -> Tuple[SolrResponse, List[Keyword]]:
    """
    Get results and top keywords from solr
    :param query: query to search for
    :param additional_params: additional params to pass to solr
    :return: results from solr
    """
    solr, default_params = connect_to_solr()
    params = default_params.copy()

    query = "comment_content:" + query
    
    # Add additional filters to the query
    fq = ["comment_content:good OR comment_content:great OR comment_content:bad OR comment_content:terrible"]
    if len(subreddits) > 0:
        subreddit_query = " OR ".join([f"subreddit:{subreddit}" for subreddit in subreddits])
        fq.append(f"{subreddit_query}")
    # not todays date
    if start_date != datetime.date.today().isoformat():
        fq.append(f"datetime:[{start_date} TO *]")
    #Add filters to the params
    params["fq"] = fq
    try:
        results = solr.search(query, **params)
        raw_response = results.raw_response
        solr_response = raw_response["response"]

        if len(solr_response["docs"]) == 0:
            return SolrResponse(**solr_response), []

        documents = [doc.get("comment_content", "") for doc in solr_response["docs"]]

        # Step 1: Get TF-IDF-based keyword extraction
        if len(solr_response["docs"]) > 2:
            lda_keywords = get_keywords_from_spacy_and_LDA(documents)
        else:
            lda_keywords = []
        # Step 2: Get semantic keyword extraction
        query = query.replace("comment_content:", "")
        fq_string = fq[0].replace("comment_content:", "")
        fq = fq_string.replace(" OR ", " ")
        semantic_query = query + " " + fq
        semantic_keywords = extract_keywords_semantic(semantic_query, documents)
        
        # Create dictionaries for fast look-up
        lda_dict = {kw.keyword: kw.count for kw in lda_keywords}
        semantic_dict = {kw.keyword: kw.count for kw in semantic_keywords}

        combined_scores = {}
        all_keywords = set(lda_dict.keys()).union(semantic_dict.keys())

        for keyword in all_keywords:
            lda_score = lda_dict.get(keyword, 0)
            semantic_score = semantic_dict.get(keyword, 0)
            # Boost keywords that appear in both extractions (e.g., multiply semantic score by 2)
            if keyword in lda_dict and keyword in semantic_dict:
                combined_score = lda_score + (semantic_score * 2)
            else:
                combined_score = lda_score + semantic_score
            combined_scores[keyword] = combined_score

        # Convert back to Keyword objects
        combined_keywords = [Keyword(keyword=kw, count=score) for kw, score in combined_scores.items()]
        sorted_combined_keywords = sorted(combined_keywords, key=lambda x: x.count, reverse=True)
        keywords = sorted_combined_keywords[:10]

        return SolrResponse(**solr_response), keywords
    
    except pysolr.SolrError as e:
        print(f"Solr error: {e}")
        return SolrResponse(numFound=0, start=0, docs=[], keywords=[])
    
def convert_to_query_response(solr_response: SolrResponse) -> Tuple[int, List[str], List[Comment]]:
    """
    Convert solr response to query response
    """
    recordCount = solr_response.numFound
    #get unique subreddits from solr response
    subreddits = set()
    comments = []

    for doc in solr_response.docs:
        subreddits.add(doc.subreddit)
        comments.append({
            "text": doc.comment_content,
            "sentiment": get_sentiment(doc.comment_content)
        })

    return recordCount, list(subreddits), comments

# TODO: add sentiment analysis
def get_sentiment(text: str) -> str:
    """
    Get sentiment of text
    """
    input_lst = [text]
    infer_loader = get_dataloaders_from_list(
        input_lst,
        bs=1,
        tokenizer=tokenizer, 
        dataset_args=config["data_config"], 
        training_args=training_args
    )
    outs = []
    for input, length in infer_loader:
        input = input.to("cuda")
        with torch.no_grad():
            output = model(input)
    output = output.to("cpu")
    print("size:", output.size())
    print("Model type", model_type)
    print("Agg", aggregation)
    if model_type!='CNN':
        if aggregation=='last':
            output = output[range(input.size()[0]), length - 1]
            print("last: ", output.shape)
        elif aggregation=='mean':
            output = torch.mean(output, axis=1)
        elif aggregation=='max':
            output = torch.max(output, axis=1).values
    
    outs.extend(output.tolist())
    out = outs[0]
    # softmax
    out = torch.nn.functional.softmax(torch.tensor(out), dim=0)
    # get the index of the max value
    index = torch.argmax(out).item()
    print("out", out)
    print("index", index)
    if index == 0:
        return "negative"
    else:
        return "positive"
    # get the value of the max value
    