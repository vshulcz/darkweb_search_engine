import string
import pickle
from math import log
from collections import defaultdict

import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from database.database import get_all_documents


def preprocess_text(text):
    if not text:
        return []

    nltk.download("punkt")
    nltk.download("wordnet")
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    tokens = word_tokenize(text)
    tokens = [token for token in tokens if token.isalpha()]
    tokens = [WordNetLemmatizer().lemmatize(token) for token in tokens]

    return tokens


def load_documents_processed():
    docs, doc_ids = get_all_documents()
    processed_docs = [" ".join(preprocess_text(doc)) for doc in docs]
    return processed_docs, doc_ids


def build_boolean_index(processed_docs, doc_ids):
    inverted_index = defaultdict(set)
    for doc, doc_id in zip(processed_docs, doc_ids):
        tokens = doc.split()
        for token in set(tokens):
            inverted_index[token].add(doc_id)
    return dict(inverted_index)


def build_tfidf_index(raw_docs):
    vectorizer = TfidfVectorizer(analyzer=preprocess_text)
    tfidf_matrix = vectorizer.fit_transform(raw_docs)
    return tfidf_matrix, vectorizer


class BM25Index:
    def __init__(self, corpus_tokens, k1=1.5, b=0.75):
        self.corpus = corpus_tokens
        self.k1 = k1
        self.b = b
        self.N = len(corpus_tokens)
        self.doc_lens = [len(doc) for doc in corpus_tokens]
        self.avg_doc_len = sum(self.doc_lens) / self.N if self.N > 0 else 0
        self.df = {}
        for doc in corpus_tokens:
            unique_terms = set(doc)
            for term in unique_terms:
                self.df[term] = self.df.get(term, 0) + 1
        self.idf = {}
        for term, df in self.df.items():
            self.idf[term] = log((self.N - df + 0.5) / (df + 0.5) + 1)

    def score(self, query_tokens, index):
        score = 0.0
        doc = self.corpus[index]
        term_freqs = {}
        for term in doc:
            term_freqs[term] = term_freqs.get(term, 0) + 1
        for term in query_tokens:
            if term not in term_freqs:
                continue
            freq = term_freqs[term]
            term_idf = self.idf.get(term, 0)
            denom = freq + self.k1 * (
                1 - self.b + self.b * self.doc_lens[index] / self.avg_doc_len
            )
            score += term_idf * (freq * (self.k1 + 1)) / denom
        return score

    def query(self, query_tokens):
        scores = []
        for i in range(self.N):
            s = self.score(query_tokens, i)
            scores.append(s)
        return scores


def build_bm25_index(processed_docs_tokens):
    return BM25Index(processed_docs_tokens)


def save_index(index_obj, filename):
    with open(filename, "wb") as f:
        pickle.dump(index_obj, f)
    print(f"[✓] Сохранён индекс в {filename}")


def load_index(filename):
    with open(filename, "rb") as f:
        return pickle.load(f)


def main_indexing():
    raw_docs, doc_ids = get_all_documents()
    processed_docs_str, _ = load_documents_processed()

    boolean_index = build_boolean_index(processed_docs_str, doc_ids)
    save_index(boolean_index, "boolean_index.pkl")

    tfidf_matrix, tfidf_vectorizer = build_tfidf_index(raw_docs)
    save_index((tfidf_matrix, tfidf_vectorizer, doc_ids), "tfidf_index.pkl")

    processed_docs_tokens = [preprocess_text(doc) for doc in raw_docs]
    bm25_index = build_bm25_index(processed_docs_tokens)
    save_index((bm25_index, doc_ids), "bm25_index.pkl")


def search_boolean(query):
    boolean_index = load_index("boolean_index.pkl")
    tokens = preprocess_text(query)
    if not tokens:
        return []

    docs = None
    for token in tokens:
        token_docs = boolean_index.get(token, set())
        if docs is None:
            docs = token_docs
        else:
            docs = docs.intersection(token_docs)
    if docs is None:
        return []
    return list(docs)


def search_tfidf(query):
    tfidf_matrix, vectorizer, doc_ids = load_index("tfidf_index.pkl")
    query_vec = vectorizer.transform([query])
    scores = cosine_similarity(query_vec, tfidf_matrix)[0]
    results = list(zip(doc_ids, scores))
    results = sorted(results, key=lambda x: x[1], reverse=True)
    return results


def search_bm25(query):
    bm25_index, doc_ids = load_index("bm25_index.pkl")
    tokens = preprocess_text(query)
    scores = bm25_index.query(tokens)
    results = list(zip(doc_ids, scores))
    results = sorted(results, key=lambda x: x[1], reverse=True)
    return results
