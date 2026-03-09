import string
import random
from datetime import datetime, timedelta
import asyncio
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from . import models, schemas, auth, database
from .database import engine, get_db, redis_client

# создание таблиц
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="URL Shortener API")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# утилиты
def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# фоновые задачи
async def clean_expired_links():
    """ помечает просроченные ссылки как неактивные"""
    while True:
        db = database.SessionLocal()
        try:
            now = datetime.utcnow()
            expired = db.query(models.Link).filter(
                models.Link.expires_at < now,
                models.Link.is_active == True
            ).all()
            
            for link in expired:
                link.is_active = False
                if redis_client:
                    redis_client.delete(link.short_code)
            
            if expired:
                db.commit()
                print(f"Cleaned up {len(expired)} expired links.")
        finally:
            db.close()
        await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(clean_expired_links())

# страницы HTML

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# api endpoints (auth, logic)

@app.post("/register", response_model=schemas.Token)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = auth.create_access_token(data={"sub": new_user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/token", response_model=schemas.Token)
def login(form_data: schemas.UserCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/links/shorten", response_model=schemas.LinkResponse)
def shorten_link(
    link: schemas.LinkCreate, 
    db: Session = Depends(get_db),
    request: Request = None 
):
    user = None
    auth_header = request.headers.get('Authorization')
    if auth_header:
        try:
            token = auth_header.split(" ")[1]
            user = asyncio.run(auth.get_current_user(token, db))
        except:
            pass

    if link.custom_alias:
        if db.query(models.Link).filter(models.Link.short_code == link.custom_alias).first():
            raise HTTPException(status_code=400, detail="Alias already exists")
        short_code = link.custom_alias
    else:
        for _ in range(10):
            code = generate_short_code()
            if not db.query(models.Link).filter(models.Link.short_code == code).first():
                short_code = code
                break
        else:
            raise HTTPException(status_code=500, detail="Could not generate unique code")

    db_link = models.Link(
        original_url=str(link.original_url),
        short_code=short_code,
        expires_at=link.expires_at,
        user_id=user.id if user else None
    )
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    
    if redis_client:
        redis_client.setex(short_code, timedelta(hours=24), str(link.original_url))
        
    return db_link

@app.get("/links/search")
def search_links(original_url: str, db: Session = Depends(get_db)):
    links = db.query(models.Link).filter(models.Link.original_url == original_url).all()
    return links

@app.get("/links/history/expired", response_model=List[schemas.LinkResponse])
def get_expired_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    links = db.query(models.Link).filter(
        models.Link.user_id == current_user.id,
        models.Link.is_active == False
    ).all()
    return links

@app.get("/links/my", response_model=List[schemas.LinkResponse])
def get_my_links(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    links = db.query(models.Link).filter(models.Link.user_id == current_user.id).all()
    return links

@app.get("/links/{short_code}/stats", response_model=schemas.LinkStats)
def get_link_stats(short_code: str, db: Session = Depends(get_db)):
    link = db.query(models.Link).filter(models.Link.short_code == short_code).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    return link

@app.delete("/links/{short_code}")
def delete_link(
    short_code: str, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    link = db.query(models.Link).filter(models.Link.short_code == short_code).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    if link.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this link")
    
    if redis_client:
        redis_client.delete(short_code)
    
    db.delete(link)
    db.commit()
    return {"detail": "Link deleted"}

@app.put("/links/{short_code}", response_model=schemas.LinkResponse)
def update_link(
    short_code: str, 
    link_update: schemas.LinkUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    link = db.query(models.Link).filter(models.Link.short_code == short_code).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    if link.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this link")
    
    link.original_url = str(link_update.original_url)
    db.commit()
    db.refresh(link)

    if redis_client:
        redis_client.delete(short_code)
        redis_client.setex(short_code, timedelta(hours=24), link.original_url)
        
    return link

# редирект

@app.get("/{short_code}")
def redirect_to_original(short_code: str, db: Session = Depends(get_db)):

    if redis_client is not None:
        cached_url = redis_client.get(short_code)
        if cached_url:
            db_link = db.query(models.Link).filter(models.Link.short_code == short_code).first()
            if db_link:
                 db_link.click_count += 1
                 db_link.last_accessed_at = datetime.utcnow()
                 db.commit()
            return RedirectResponse(url=cached_url)
            
    link = db.query(models.Link).filter(models.Link.short_code == short_code).first()
    
    if not link or not link.is_active:
        raise HTTPException(status_code=404, detail="Link not found or expired")
    
    if link.expires_at and link.expires_at < datetime.utcnow():
        link.is_active = False
        db.commit()
        raise HTTPException(status_code=404, detail="Link expired")

    link.click_count += 1
    link.last_accessed_at = datetime.utcnow()
    db.commit()

    if redis_client is not None:
        redis_client.setex(short_code, timedelta(hours=24), link.original_url)

    return RedirectResponse(url=link.original_url)
