import asyncio
import re
import httpx
from logger import logger
from bs4 import BeautifulSoup
from database.database import save_page, page_exists, save_link
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
)

PROXY = "socks5h://127.0.0.1:9050"

HEADERS = {"User-Agent": "DarkWebCrawler/1.0"}

ONION_REGEX = re.compile(r"(http[s]?://)?[a-zA-Z0-9]{16,56}\.onion")


class DarkWebCrawlerAsync:
    def __init__(self, seeds, max_depth=2, concurrency=5, proxy=PROXY):
        self.queue = set(seeds)
        self.visited = set()
        self.max_depth = max_depth
        self.proxy = proxy
        self.concurrency = concurrency

    def extract_links(self, html):
        found = set(ONION_REGEX.findall(html))
        links = set()
        for match in found:
            url = "".join(match) if isinstance(match, tuple) else match
            if not url.startswith("http"):
                url = "http://" + url
            links.add(url)
        return links

    def parse(self, html):
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title else ""
        text = soup.get_text(separator=" ", strip=True)
        return title, text

    async def fetch_and_process(self, url, client, sem, new_links, progress, task_id):
        async with sem:
            try:
                if url in self.visited:
                    return
                response = await client.get(url, timeout=20.0)
                if response.status_code == 200:
                    html = response.text
                    title, text = self.parse(html)
                    save_page(url, title, text)
                    links = self.extract_links(html)
                    for link in links:
                        if (
                            not page_exists(link)
                            and link not in self.visited
                            and link not in new_links
                        ):
                            new_links.add(link)
                            current_total = progress.get_task(task_id).total
                            progress.update(task_id, total=current_total + 1)
                        save_link(url, link)
                self.visited.add(url)
            except Exception as e:
                logger.log(f"[!] Error fetching {url}: {e}")
            finally:
                progress.update(task_id, advance=1)

    async def crawl(self):
        proxy_transport = httpx.AsyncHTTPTransport(proxy=self.proxy)
        async with httpx.AsyncClient(
            transport=proxy_transport, headers=HEADERS
        ) as client:
            sem = asyncio.Semaphore(self.concurrency)
            current_level = set(self.queue)
            depth = 0

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TextColumn("{task.completed}/{task.total}"),
                BarColumn(),
                TimeElapsedColumn(),
                transient=False,
            ) as progress:
                while depth < self.max_depth and current_level:
                    logger.log(
                        f"[*] Depth {depth} — {len(current_level)} URLs to visit"
                    )
                    new_links = set()

                    task_id = progress.add_task(
                        f"[green]Depth {depth} Crawling", total=len(current_level)
                    )

                    tasks = [
                        self.fetch_and_process(
                            url, client, sem, new_links, progress, task_id
                        )
                        for url in current_level
                        if url not in self.visited
                    ]
                    await asyncio.gather(*tasks)

                    progress.remove_task(task_id)
                    current_level = new_links - self.visited
                    depth += 1
