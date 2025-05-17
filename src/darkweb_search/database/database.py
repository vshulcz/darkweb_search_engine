import datetime
from pathlib import Path
from src.darkweb_search.utils import logger
from src.darkweb_search.database.models import Base, Page, Link
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine


DB_PATH = Path(__file__).parent.parent.parent / "data" / "darkweb.db"
DB_URL = f"sqlite:///{DB_PATH}"


def get_engine(echo: bool = False):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(DB_URL, echo=echo, future=True)
    return engine


def get_session(echo: bool = False) -> Session:
    engine = get_engine(echo=echo)
    Session = sessionmaker(bind=engine, autoflush=False, future=True)
    return Session()


def init_db(echo: bool = False):
    engine = get_engine(echo=echo)
    Base.metadata.create_all(engine)


def page_exists(session: Session, url: str) -> bool:
    return session.query(Page).filter_by(url=url).first() is not None


def save_page(
    session: Session,
    url: str,
    title: str,
    content: str,
    status_code: int = 200,
    visited_at: datetime.datetime | None = None,
):
    if page_exists(session, url):
        logger.log(f"[~] Already exists in DB: {url}")
        return

    visited_at = visited_at or datetime.datetime.now(datetime.timezone.utc)
    page = Page(
        url=url,
        title=title,
        content=content,
        status_code=status_code,
        visited_at=visited_at,
    )
    session.add(page)
    session.commit()
    logger.log(f"[✓] Saved: {url}")


def save_link(session: Session, from_url: str, to_url: str):
    src = session.query(Page).filter_by(url=from_url).first()
    dst = session.query(Page).filter_by(url=to_url).first()
    if not src or not dst:
        return

    link = Link(from_page_id=src.id, to_page_id=dst.id)
    session.add(link)
    session.commit()


def get_all_documents(session: Session) -> tuple[list[str], list[int]]:
    pages = session.query(Page).all()
    texts, ids = [], []
    for p in pages:
        text = (p.title or "") + " " + (p.content or "")
        texts.append(text)
        ids.append(p.id)
    return texts, ids


init_db()
