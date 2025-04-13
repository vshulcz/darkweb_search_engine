from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class Page(Base):
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True, nullable=False)
    title = Column(String)
    content = Column(Text)
    status_code = Column(Integer)
    visited_at = Column(DateTime, default=datetime.utcnow)

    links_from = relationship(
        "Link", back_populates="source", foreign_keys="Link.from_page_id"
    )
    links_to = relationship(
        "Link", back_populates="target", foreign_keys="Link.to_page_id"
    )


class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True)
    from_page_id = Column(Integer, ForeignKey("pages.id"))
    to_page_id = Column(Integer, ForeignKey("pages.id"))

    source = relationship(
        "Page", foreign_keys=[from_page_id], back_populates="links_from"
    )
    target = relationship("Page", foreign_keys=[to_page_id], back_populates="links_to")
