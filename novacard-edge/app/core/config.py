# from pydantic_settings import BaseSettings, SettingsConfigDict

# class Settings(BaseSettings):
#     # This automatically maps the .env variables to Python types
#     APP_NAME: str = "NovaCardCredit App"
#     DATABASE_URL: str
#     BAAS_API_KEY: str

#     model_config = SettingsConfigDict(env_file=".env")

# # We instantiate this once to use everywhere (Singleton pattern)
# settings = Settings()


from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(title=settings.APP_NAME)

@app.get("/health")
async def health_check():
    # Like a heartbeat check for the server
    return {"status": "healthy", "database": "pending"}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    import uvicorn
    # This starts the server on port 8000
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)