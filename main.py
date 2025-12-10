"""
Authentication Service API - Main Application Entry Point
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.core.logger import setup_logging
from app.api.v1.routes import auth, keys
from app.api.db.database import init_db
from app.api.utils.exceptions import WalletServiceException
from app.api.utils.handlers import wallet_service_exception_handler
from config import settings

setup_logging()
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan - startup and shutdown events.
    
    Args:
        app (FastAPI): FastAPI application instance
        
    Yields:
        None
    """
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    try:
        await init_db()
        logger.info("Database initialization completed")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}", exc_info=True)
        raise
    
    yield
    
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Authentication Service API with Google OAuth, JWT & API Keys",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, settings.DEV_URL, settings.APP_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(WalletServiceException, wallet_service_exception_handler)


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for service monitoring.
    
    Returns:
        dict: Service status and version information
    """
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint providing API information.
    
    Returns:
        dict: API name and documentation links
    """
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
    }

app.include_router(auth.router, prefix="/api/v1")
app.include_router(keys.router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on 0.0.0.0:{settings.APP_PORT}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        log_config=None,
    )
