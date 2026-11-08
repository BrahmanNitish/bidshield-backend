from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.evidence import router as evidence_router
from app.api.tenders import router as tender_router
from app.database import init_db
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="BidShield AI Engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(evidence_router)
app.include_router(tender_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "BidShield AI"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="BidShield AI API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tender_router, prefix="/tenders", tags=["Tenders"])
app.include_router(evidence_router, prefix="/evidence", tags=["Evidence"])

from app.api.procurement_demo import router as demo_router

app.include_router(demo_router, prefix="/demo", tags=["SIH Procurement Demo"])