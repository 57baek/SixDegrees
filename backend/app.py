# MAIN APP FILE
# TODO: Import auth router and include it so /auth/login and /auth/register work
#TODO: Add CORS middleware so frontend (localhost:5173) can talk to us



from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# add cors middleware
origins = [
    "http://localhost:5173"  
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)