"""
RH-OTP Auto-Connect FastAPI Application.

Main entry point for the Red Hat OTP Auto-Connect service.
Provides API endpoints for VPN management, credential retrieval,
and ephemeral environment management.
"""
import logging

from fastapi import FastAPI

# Import auth dependencies
from api.dependencies.auth import get_or_create_auth_token

# Import all routers
from api.routes import ephemeral, legacy, vpn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="RH-OTP Auto-Connect API",
    description="Red Hat OTP Auto-Connect Service with VPN and Ephemeral Namespace Management",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Include routers
app.include_router(vpn.router)
app.include_router(ephemeral.router)
app.include_router(legacy.router)  # Legacy endpoints for backward compatibility


# Initialize auth token on startup
@app.on_event("startup")
async def startup_event():
    """Initialize authentication token and other startup tasks."""
    token = get_or_create_auth_token()
    logger.info("=" * 60)
    logger.info("RH-OTP Auto-Connect Service started")
    logger.info(f"Version: 2.0.0")
    logger.info(f"Authentication token: {token[:8]}...")
    logger.info(f"API Documentation: http://localhost:8009/docs")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup tasks on shutdown."""
    logger.info("RH-OTP Auto-Connect Service shutting down")


@app.get("/", tags=["health"])
def health_check():
    """
    Health check endpoint.

    Returns:
        Simple message indicating service is running
    """
    return {
        "status": "healthy",
        "service": "RH-OTP Auto-Connect",
        "version": "2.0.0"
    }


@app.get("/ping", tags=["health"])
def ping():
    """
    Ping endpoint for quick health checks.

    Returns:
        pong
    """
    return "pong"
