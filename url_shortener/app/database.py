from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import redis
from .config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

redis_client = None
if settings.REDIS_URL:
    try:
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        if r.ping():
            redis_client = r
            print("Redis connected!")
    except Exception as e:
        print(f"Redis connection failed: {e}. Working without cache.")
else:
    print("No REDIS_URL found. Working without cache.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
