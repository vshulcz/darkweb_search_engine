import asyncio
from crawler.crawler import DarkWebCrawlerAsync
from crawler.get_seed import get_seed


PROXY = "socks5h://127.0.0.1:9050"

SEARCH_ENGINE = "http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion/"

if __name__ == "__main__":
    query = "onion forum"
    seeds = get_seed(query)
    print(f"[*] Found {len(seeds)} .onion seeds")

    if seeds:
        print("[*] Starting crawl...\n")
        crawler = DarkWebCrawlerAsync(seeds, max_depth=2, concurrency=5, proxy=PROXY)
        asyncio.run(crawler.crawl())
