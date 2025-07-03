from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


engine = create_engine(settings.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True, pool_size=10,  # Increase the pool size
                       max_overflow=20,  # Allow more overflow connections
                       pool_timeout=30,  # Increase the timeout duration
                       pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
