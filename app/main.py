from fastapi import FastAPI
from app.routes import merchant, payment
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Payvora")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routes
app.include_router(merchant.router, prefix="/api/v1", tags=["Merchant"])
app.include_router(payment.router, prefix="/api/v1", tags=["Payments"])



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)