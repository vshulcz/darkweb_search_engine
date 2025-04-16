from logger import logger
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from database.models import Base, Page, Link
from datetime import datetime


DB_PATH = "sqlite:///darkweb.db"

engine = create_engine(DB_PATH, echo=False)
Session = sessionmaker(bind=engine)
session = Session()


def init_db():
    Base.metadata.create_all(engine)


def page_exists(url):
    return session.query(Page).filter_by(url=url).first() is not None


def save_page(url, title, content, status_code=200):
    if page_exists(url):
        logger.log(f"[~] Already exists in DB: {url}")
        return

    try:
        page = Page(
            url=url,
            title=title,
            content=content,
            status_code=status_code,
            visited_at=datetime.utcnow(),
        )
        session.add(page)
        session.commit()
        logger.log(f"[✓] Saved: {url}")
    except Exception as e:
        session.rollback()
        logger.log(f"[!] DB error on page save: {e}")


def save_link(from_url, to_url):
    try:
        from_page = session.query(Page).filter_by(url=from_url).first()
        to_page = session.query(Page).filter_by(url=to_url).first()

        if from_page and to_page:
            link = Link(from_page_id=from_page.id, to_page_id=to_page.id)
            session.add(link)
            session.commit()
    except Exception as e:
        session.rollback()
        logger.log(f"[!] DB error on link save: {e}")


def get_all_documents():
    docs = []
    doc_ids = []

    pages = session.query(Page).all()
    for page in pages:
        text = ""
        if page.title:
            text += page.title + " "
        if page.content:
            text += page.content
        docs.append(text)
        doc_ids.append(page.id)
    return docs, doc_ids


init_db()
