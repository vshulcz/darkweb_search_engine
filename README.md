# DarkWeb Search Engine

A **modular** dark web crawler and search engine that:
- Collects hidden service pages asynchronously via Tor
- Automatically discovers seed URLs via onion search engines
- Indexes content using **Boolean**, **TF‑IDF**, and **BM25** models
- Provides risk assessment (keyword‑based & zero‑shot AI)

## ⚠️ Disclaimer

This project is intended for educational and research purposes only.
Accessing the dark web may involve legal, ethical, and security risks.
Use responsibly, stay anonymous, and always comply with your local laws.

## Features
- **Async Crawling** over Tor (Socks5 proxy)
- **Automated Seed Discovery** from onion search engines
- **Multi‑Model Indexing**: Boolean, TF‑IDF, BM25
- **AI‑Driven Risk Assessment**: keyword lookup & HuggingFace zero‑shot
- **Rich CLI** with colored, sorted output
- **Persistent Storage**: SQLite + SQLAlchemy ORM

## Requirements
- **Python 3.11+**
- **Tor** running locally on port 9050 (for .onion access)
- **uv** for dependency management

## Installation
1. Clone the repository:
```bash
git clone https://github.com/vshulcz/darkweb_search_engine.git
cd darkweb_search_engine
```
2. Install dependencies:
```bash
uv sync
```

## Usage
All commands are available via `python main.py`.

### Crawl
Fetch seed URLs for a query and crawl hidden services:
```bash
python main.py crawl \
  --query "onion forum" \
  --max-depth 2 \
  --concurrency 5
```

### Index
Rebuild all search indices (Boolean, TF‑IDF, BM25) from DB:
```bash
python main.py index
```

### Search
Query the indexed corpus. Only top 5 results shown:
```bash
# Boolean model
python main.py search --query "buy onion domain" --model boolean

# TF-IDF model
python main.py search --query "buy onion domain" --model tfidf

# BM25 model
python main.py search --query "buy onion domain" --model bm25
```

### Assess Risk
Evaluate risk on recently crawled pages with two methods:
```bash
# Keyword only
python main.py assess --top 5 --method keywords

# Zero-shot only
python main.py assess --top 5 --method zero-shot

# Both methods
python main.py assess --top 5 --method both
```
Output is **sorted** by risk and **color‑coded** (red/yellow/green).

## Configuration

- **Tor Proxy** and **DB path** can be adjusted in `cli.py` constants.
- **Risk categories** and **keywords** defined in `risk_assessor/risk_assessor.py`.
- **Index directory** at `data/indices`.

## License
MIT License. Use at your own risk.