from sqlalchemy import Column, Integer, String, BigInteger, DateTime, Text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from datetime import datetime
from config import DATABASE_URL

# Use psycopg for PostgreSQL (compatible with Python 3.13)
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)

class Movie(Base):
    __tablename__ = "movies"
    id = Column(Integer, primary_key=True)
    movie_number = Column(Integer, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    file_id = Column(String, nullable=False)               # Video file_id (for sending)
    preview_file_id = Column(String, nullable=True)        # Optional preview image file_id
    channel_post_id = Column(BigInteger, nullable=False)   # Announcement post ID in channel
    channel_chat_id = Column(String, nullable=False)       # Channel ID
    added_by = Column(BigInteger, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    views_count = Column(Integer, default=0)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)