import pickle
from pathlib import Path
from math import log
from collections import defaultdict
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.darkweb_search.database.database import get_all_documents, get_session
from src.darkweb_search.utils.text import preprocess_text


class BM25Index:
    def __init__(self, corpus: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.corpus = corpus
        self.k1 = k1
        self.b = b
        self.N = len(corpus)
        self.doc_lens = [len(doc) for doc in corpus]
        self.avg_doc_len = sum(self.doc_lens) / self.N if self.N else 0.0
        self.df: dict[str, int] = {}
        for doc in corpus:
            for term in set(doc):
                self.df[term] = self.df.get(term, 0) + 1
        self.idf: dict[str, float] = {
            term: log((self.N - df + 0.5) / (df + 0.5) + 1)
            for term, df in self.df.items()
        }

    def score(self, query_tokens: list[str], idx: int) -> float:
        term_freqs: dict[str, int] = {}
        for term in self.corpus[idx]:
            term_freqs[term] = term_freqs.get(term, 0) + 1
        score: float = 0.0
        for term in query_tokens:
            tf = term_freqs.get(term, 0)
            if tf <= 0:
                continue
            idf = self.idf.get(term, 0.0)
            denom = tf + self.k1 * (
                1 - self.b + self.b * self.doc_lens[idx] / self.avg_doc_len
            )
            score += idf * tf * (self.k1 + 1) / denom
        return score

    def query(self, query_tokens: list[str]) -> list[float]:
        return [self.score(query_tokens, i) for i in range(self.N)]


class Indexer:
    def __init__(self, index_dir: Path = Path("data/indices")):
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def build_boolean_index(
        self, docs: list[str], ids: list[int]
    ) -> dict[str, set[int]]:
        inverted: dict[str, set[int]] = defaultdict(set)
        for text, doc_id in zip(docs, ids):
            for token in set(text.split()):
                inverted[token].add(doc_id)
        return inverted

    def build_tfidf_index(self, raw_docs: list[str]) -> tuple[Any, TfidfVectorizer]:
        vectorizer = TfidfVectorizer(analyzer=preprocess_text)
        matrix = vectorizer.fit_transform(raw_docs)
        return matrix, vectorizer

    def build_bm25_index(self, tokenized_docs: list[list[str]]) -> BM25Index:
        return BM25Index(tokenized_docs)

    def save_index(self, obj: Any, name: str) -> None:
        path = self.index_dir / name
        with open(path, "wb") as f:
            pickle.dump(obj, f)

    def load_index(self, name: str) -> Any:
        path = self.index_dir / name
        with open(path, "rb") as f:
            return pickle.load(f)

    def reindex_all(self) -> None:
        session = get_session()
        raw_docs, doc_ids = get_all_documents(session)
        session.close()

        # Preprocess texts once
        processed_strs = [" ".join(preprocess_text(doc)) for doc in raw_docs]
        processed_tokens = [preprocess_text(doc) for doc in raw_docs]

        # Boolean index
        bool_idx = self.build_boolean_index(processed_strs, doc_ids)
        self.save_index(bool_idx, "boolean_index.pkl")

        # TF-IDF index
        tfidf_mat, tfidf_vec = self.build_tfidf_index(raw_docs)
        self.save_index((tfidf_mat, tfidf_vec, doc_ids), "tfidf_index.pkl")

        # BM25 index
        bm25_idx = self.build_bm25_index(processed_tokens)
        self.save_index((bm25_idx, doc_ids), "bm25_index.pkl")

    def search_boolean(self, query: str) -> list[int]:
        idx: dict[str, set[int]] = self.load_index("boolean_index.pkl")
        tokens = preprocess_text(query)
        if not tokens:
            return []
        docs: set[int] = idx.get(tokens[0], set()).copy()
        for t in tokens[1:]:
            docs &= idx.get(t, set())
        return sorted(docs)

    def search_tfidf(self, query: str) -> list[tuple[int, float]]:
        matrix, vectorizer, doc_ids = self.load_index("tfidf_index.pkl")
        qv = vectorizer.transform([query])
        scores = cosine_similarity(qv, matrix)[0]
        return sorted(zip(doc_ids, scores), key=lambda x: x[1], reverse=True)

    def search_bm25(self, query: str) -> list[tuple[int, float]]:
        bm25_idx, doc_ids = self.load_index("bm25_index.pkl")
        tokens = preprocess_text(query)
        scores = bm25_idx.query(tokens)
        return sorted(zip(doc_ids, scores), key=lambda x: x[1], reverse=True)
