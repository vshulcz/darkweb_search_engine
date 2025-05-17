import click
import asyncio

from src.darkweb_search.indexer.indexer import Indexer
from src.darkweb_search.risk_assessor.risk_assessor import RiskAssessor


PROXY = "socks5h://127.0.0.1:9050"


@click.group()
def cli():
    """Darkweb Searcher CLI"""
    pass


@cli.command()
@click.option(
    "--query",
    "-q",
    default="onion forum",
    help="Query to obtain seed URLs from the search engine",
)
@click.option("--max-depth", "-d", default=2, help="Maximum crawl depth")
@click.option("--concurrency", "-c", default=5, help="Number of parallel requests")
def crawl(query: str, max_depth: int, concurrency: int):
    click.echo(f"[*] Getting seed URLs for query: '{query}' ...")
    from src.darkweb_search.crawler.crawler import DarkWebCrawlerAsync
    from src.darkweb_search.crawler.get_seed import get_seed

    seeds = get_seed(query)
    click.echo(f"[*] Found {len(seeds)} seed URLs.")
    if not seeds:
        click.secho("[!] No seed URLs found. Check query.", fg="red")
        return

    click.echo(
        f"[*] Starting crawler (depth={max_depth}, concurrency={concurrency})..."
    )
    crawler = DarkWebCrawlerAsync(
        seeds, max_depth=max_depth, concurrency=concurrency, proxy=PROXY
    )
    asyncio.run(crawler.crawl())
    click.secho("[✓] Crawling complete.", fg="green")


@cli.command()
def index():
    click.echo("[*] Re-indexing documents...")
    idx = Indexer()
    idx.reindex_all()
    click.secho("[✓] Indexing finished. Indices stored in data/indices.", fg="green")


@cli.command()
@click.option("--query", "-q", required=True, help="Text search query")
@click.option(
    "--model",
    "-m",
    type=click.Choice(["boolean", "tfidf", "bm25"]),
    default="tfidf",
    help="Search model: boolean, tfidf or bm25",
)
def search(query: str, model: str):
    click.echo(f"[*] Searching '{query}' with model={model}")
    idx = Indexer()

    if model == "boolean":
        results = idx.search_boolean(query)
        results = [(doc_id, None) for doc_id in results]
    elif model == "tfidf":
        results = idx.search_tfidf(query)
    else:
        results = idx.search_bm25(query)

    if not results:
        click.secho("[!] No results found.", fg="yellow")
        return

    click.echo("[*] Top 5 results:")
    from src.darkweb_search.database.database import get_session
    from src.darkweb_search.database.models import Page

    session = get_session()
    for doc_id, score in results[:5]:
        page = session.query(Page).get(doc_id)
        if not page:
            continue
        line = f"• {page.title or 'No Title'} (URL: {page.url})"
        if score is not None:
            line += f" [Score: {score:.4f}]"
        click.echo(line)
    session.close()


@cli.command()
@click.option("--top", "-t", default=5, help="Number of recent pages to assess")
@click.option(
    "--method",
    "-m",
    type=click.Choice(["keywords", "zero-shot", "both"]),
    default="both",
    help="Risk assessment method",
)
def assess(top: int, method: str):
    click.echo(f"[*] Assessing last {top} pages via method={method}")
    from src.darkweb_search.database.database import get_session
    from src.darkweb_search.database.models import Base

    session = get_session()
    pages = (
        session.query(Base.metadata.tables["pages"])
        .order_by(Base.metadata.tables["pages"].c.visited_at.desc())
        .limit(top)
        .all()
    )
    session.close()

    assessor = RiskAssessor(use_cuda=False)
    scored = []
    for pg in pages:
        text = f"{pg.title or ''} {pg.content or ''}"
        res = assessor.assess(text, method=method)
        scored.append((pg, res))

    if method == "keywords":
        scored.sort(key=lambda x: x[1]["keywords"].score, reverse=True)
    elif method == "zero-shot":
        scored.sort(key=lambda x: x[1]["zero_shot"].score, reverse=True)
    else:
        scored.sort(
            key=lambda x: max(
                x[1]["keywords"].score if "keywords" in x[1] else 0,
                x[1]["zero_shot"].score if "zero_shot" in x[1] else 0,
            ),
            reverse=True,
        )

    for pg, res in scored:
        click.echo(f"\n• {pg.title or 'No Title'}\n  URL: {pg.url}")
        if "keywords" in res:
            k = res["keywords"]
            col = "red" if k.score > 0.5 else "yellow" if k.score > 0.25 else "green"
            cats = ", ".join(f"{c}:{p:.2f}" for c, p in k.category_scores.items()) or "—"
            click.secho(f"  [Keywords] Risk: {k.score:.2f} Categories: {cats}", fg=col)
        if "zero_shot" in res:
            z = res["zero_shot"]
            col = "red" if z.score > 0.5 else "yellow" if z.score > 0.25 else "green"
            cats = ", ".join(f"{c}:{p:.2f}" for c, p in z.category_scores.items())
            click.secho(f"  [Zero-shot] Risk: {z.score:.2f} Top: {cats}", fg=col)
