import click
import asyncio
from crawler.crawler import DarkWebCrawlerAsync
from crawler.get_seed import get_seed
from indexer.indexer import main_indexing, search_tfidf, search_boolean, search_bm25


PROXY = "socks5h://127.0.0.1:9050"


@click.group()
def cli():
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
def crawl(query, max_depth, concurrency):
    click.echo(f"[*] Getting seed URLs for query: '{query}' ...")
    seeds = get_seed(query)
    click.echo(f"[*] Found {len(seeds)} seed URLs.")

    if seeds:
        click.echo("[*] Starting crawler...\n")
        crawler = DarkWebCrawlerAsync(
            seeds, max_depth=max_depth, concurrency=concurrency, proxy=PROXY
        )
        asyncio.run(crawler.crawl())
    else:
        click.echo("[!] Could not find any seed URLs. Try a different query.")


@cli.command()
def index():
    click.echo("[*] Starting indexing process using data from the database...")
    main_indexing()
    click.echo("[✓] Indexing complete. Indexes are saved in pickle files.")


@cli.command()
@click.option("--query", "-q", required=True, help="Search query")
@click.option(
    "--model",
    "-m",
    type=click.Choice(["tfidf", "bm25", "boolean"]),
    default="tfidf",
    help="Search model to use: tfidf, bm25, or boolean",
)
def search(query, model):
    click.echo(f"[*] Searching for: '{query}' using the {model.upper()} model...")

    results = []
    if model == "tfidf":
        results = search_tfidf(query)
    elif model == "bm25":
        results = search_bm25(query)
    elif model == "boolean":
        results = search_boolean(query)

    if not results:
        click.echo("[!] No results found for your query.")
    else:
        click.echo("[*] Found pages:")
        from database.models import Page
        from database.database import session

        top_results = results[:5]
        for item in top_results:
            if isinstance(item, tuple):
                doc_id, score = item
            else:
                doc_id = item
                score = None
            page = session.query(Page).filter_by(id=doc_id).first()
            if page:
                click.echo(
                    f"• {page.title or 'No Title'} (URL: {page.url})"
                    + (f" [Score: {score:.4f}]" if score is not None else "")
                )
        session.close()


if __name__ == "__main__":
    cli()
