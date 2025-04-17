# DarkWeb Search Engine

A modular dark web crawler and search engine that collects, indexes, and searches hidden service pages using Boolean, TF-IDF, and BM25 models. This project is designed for research and demonstration purposes.

## ⚠️ Disclaimer

This project is intended for educational and research purposes only.
Accessing the dark web may involve legal, ethical, and security risks.
Use responsibly, stay anonymous, and always comply with your local laws.

## Features
* Asynchronous Crawling
* Automated Seed Discovery
* Multi-Model Indexing
* CLI Application

## Requirements
Python 3.11+
uv 
Tor for crawling (running locally on port 9050)

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
The project provides a CLI application with three main commands:

* Crawl - get seed URLs for a query and start crawling the dark web:
```bash
python main.py crawl --query "onion forum" --max-depth 2 --concurrency 5
```
* Index - re-index pages from the database using all three models. Indexes are saved in pickle files:
```bash
python main.py index
```
* Search - search the indexed database with a query using the chosen model (tfidf, bm25, or boolean). Only the top 5 results are displayed.
```bash
python main.py search --query "buy onion domain" --model tfidf
```