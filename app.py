from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, energy, appliances, control, forecast
from sqlite_db import init_db_with_sample_data

app = FastAPI(title="SmartEnergy AI Backend", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize SQLite and sample data on startup
@app.on_event("startup")
async def startup_event():
    init_db_with_sample_data()

# Register routers
app.include_router(auth.router)
app.include_router(appliances.router)
app.include_router(energy.router)
app.include_router(control.router)
app.include_router(forecast.router)

@app.get("/")
def root():
    return {"message": "SmartEnergy AI Backend is running"}

# If executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
