# MAIN APP FILE
# SINGLE WORKER CONSTRAINT: Always run with `uvicorn app:app --reload`.
# Multi-worker mode (--workers N) causes APScheduler to fire N times per trigger.
# See backend/services/map/scheduler.py for full documentation.

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.map import router as map_router
from routes.interactions import router as interactions_router
from routes.profile import router as profile_router
from routes.match import router as match_router
from services.map.scheduler import setup_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start APScheduler on FastAPI startup
    scheduler = setup_scheduler()
    scheduler.start()
    yield
    # Shutdown APScheduler cleanly on FastAPI shutdown
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)

# ─── CORS  ───
origins = [
    "http://localhost:5173",   
    "http://127.0.0.1:5173",   
    "http://localhost:5174",   
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,             
    allow_credentials=True,            
    allow_methods=["*"],               
    allow_headers=["*"],               
    expose_headers=["*"],              
)


app.include_router(map_router)
app.include_router(interactions_router)
app.include_router(profile_router)
app.include_router(match_router)
