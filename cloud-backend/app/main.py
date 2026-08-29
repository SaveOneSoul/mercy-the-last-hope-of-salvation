import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from .db import Base, engine, get_db
from .models import PrayerIntention, ContactMessage
Base.metadata.create_all(bind=engine)
app=FastAPI(title="Mercy API",version="2.0.0",docs_url="/docs" if os.getenv("ENABLE_DOCS","true").lower()=="true" else None)
origins=[x.strip() for x in os.getenv("CORS_ORIGINS","http://localhost:5500").split(',') if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,allow_methods=["GET","POST"],allow_headers=["Content-Type"])
class PrayerIn(BaseModel):
    name:str|None=Field(default=None,max_length=80)
    intention:str=Field(min_length=2,max_length=2000)
    website:str|None=Field(default=None,max_length=200)
class ContactIn(BaseModel):
    name:str=Field(min_length=1,max_length=80)
    email:EmailStr
    subject:str=Field(min_length=1,max_length=160)
    message:str=Field(min_length=2,max_length=5000)
    website:str|None=Field(default=None,max_length=200)
@app.get('/health')
def health(): return {'status':'ok','service':'mercy-api','version':'2.0.0'}
@app.get('/api/content/version')
def version(): return {'content_version':'2026.08.29','frontend':'github-pages-ready'}
@app.post('/api/prayer-intentions',status_code=201)
def create_prayer(payload:PrayerIn,db:Session=Depends(get_db)):
    if payload.website: return {'status':'accepted'}
    row=PrayerIntention(name=(payload.name or '').strip() or None,intention=payload.intention.strip())
    db.add(row); db.commit(); db.refresh(row)
    return {'status':'received','id':row.id}
@app.post('/api/contact',status_code=201)
def create_contact(payload:ContactIn,db:Session=Depends(get_db)):
    if payload.website: return {'status':'accepted'}
    row=ContactMessage(name=payload.name.strip(),email=str(payload.email),subject=payload.subject.strip(),message=payload.message.strip())
    db.add(row); db.commit(); db.refresh(row)
    return {'status':'received','id':row.id}
