import httpx
from src.darkweb_search.utils import logger
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs


SEARCH_ENGINE = "http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Referer": SEARCH_ENGINE,
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
}

PROXY = "socks5h://127.0.0.1:9050"


def get_seed(query, proxy=PROXY):
    params = {"q": query}
    proxy_transport = httpx.HTTPTransport(proxy=proxy)
    try:
        with httpx.Client(
            transport=proxy_transport, headers=HEADERS, timeout=30.0
        ) as client:
            response = client.get(f"{SEARCH_ENGINE}search/", params=params)
            soup = BeautifulSoup(response.text, "html.parser")

            onion_links = set()
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/redirect?" in href and "redirect_url=" in href:
                    parsed = urlparse(href)
                    query_params = parse_qs(parsed.query)
                    url = query_params.get("redirect_url", [None])[0]
                    if url and ".onion" in url:
                        onion_links.add(url)

            return list(onion_links)

    except Exception as e:
        logger.log(f"[!] Failed to get seeds from search engine: {e}")
        return []
