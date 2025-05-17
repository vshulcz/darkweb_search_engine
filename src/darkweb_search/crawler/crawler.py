import asyncio
import re
import httpx
from bs4 import BeautifulSoup
from src.darkweb_search.utils import logger
from src.darkweb_search.database.database import get_session, save_page, page_exists, save_link
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
    def __init__(
        self,
        seeds: list[str],
        max_depth: int = 2,
        concurrency: int = 5,
        proxy: str = PROXY,
    ):
        self.max_depth = max_depth
        self.concurrency = concurrency
        self.proxy = proxy
        self.visited: set[str] = set()
        self.current_level: set[str] = set(seeds)

    def extract_links(self, html: str) -> set[str]:
        matches = ONION_REGEX.findall(html)
        urls: set[str] = set()
        for grp in matches:
            url = grp[0] + grp[1] if isinstance(grp, tuple) else grp
            url = url if url.startswith("http") else f"http://{url}"
            urls.add(url)
        return urls

    def parse(self, html: str) -> tuple[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        text = soup.get_text(separator=" ", strip=True)
        return title, text

    async def fetch_and_process(
        self,
        url: str,
        client: httpx.AsyncClient,
        sem: asyncio.Semaphore,
        new_links: set[str],
        progress: Progress,
        task_id: int,
    ):
        async with sem:
            session = get_session()
            try:
                if url in self.visited or page_exists(session, url):
                    return
                response = await client.get(url, timeout=20.0)
                if response.status_code == 200:
                    html = response.text
                    title, text = self.parse(html)
                    save_page(session, url, title, text, response.status_code)
                    links = self.extract_links(html)
                    for link in links:
                        save_link(session, url, link)
                        if link not in self.visited and link not in new_links:
                            new_links.add(link)
                            progress.update(task_id, total=progress.tasks[0].total + 1)

                self.visited.add(url)
            except Exception as e:
                logger.log(f"[!] Error fetching {url}: {e}")
            finally:
                session.close()
                progress.update(task_id, advance=1)

    async def crawl(self):
        transport = httpx.AsyncHTTPTransport(proxy=self.proxy)
        async with httpx.AsyncClient(
            transport=transport,
            headers=HEADERS,
            follow_redirects=True,
        ) as client:
            sem = asyncio.Semaphore(self.concurrency)
            depth = 0
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TextColumn("{task.completed}/{task.total}"),
                BarColumn(),
                TimeElapsedColumn(),
            ) as progress:
                while depth < self.max_depth and self.current_level:
                    level_urls = self.current_level - self.visited
                    if not level_urls:
                        break
                    logger.log(f"[*] Depth {depth}: {len(level_urls)} URLs to visit")
                    task_id = progress.add_task(f"Depth {depth}", total=len(level_urls))

                    new_links: set[str] = set()
                    tasks = [
                        self.fetch_and_process(
                            url, client, sem, new_links, progress, task_id
                        )
                        for url in level_urls
                    ]
                    await asyncio.gather(*tasks)
                    progress.remove_task(task_id)
                    self.current_level = new_links
                    depth += 1
