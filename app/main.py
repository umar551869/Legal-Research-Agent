import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.config import settings
from app.routers import auth, chat, admin
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialize Rate Limiter
limiter = Limiter(key_func=get_remote_address)

# =============================================================================
# Logging Configuration
# =============================================================================
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# Application Lifecycle Events
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME}...")
    logger.info(f"Ollama URL: {settings.OLLAMA_BASE_URL}")
    logger.info(f"CORS Origins: {settings.cors_origins_list}")
    yield
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}...")

# =============================================================================
# FastAPI Application
# =============================================================================
app = FastAPI(
    title=settings.APP_NAME,
    description="Production-ready backend for Legal Research AI with hallucination mitigation",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.DEBUG
)

# Add Limiter to App State
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# =============================================================================
# CORS Middleware
# =============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Request Logging Middleware
# =============================================================================
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Status: {response.status_code}")
    return response

# =============================================================================
# Exception Handlers
# =============================================================================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages"""
    # exc.body may be bytes, which is not JSON serializable
    body = exc.body
    if isinstance(body, bytes):
        try:
            body = body.decode()
        except Exception:
            body = str(body)
            
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": body
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected error occurred. Please try again later."
        }
    )

# =============================================================================
# Include Routers
# =============================================================================
# Routers already have their specific prefixes (e.g., /auth, /chat)
# Nginx handles the /api mapping by stripping it before forwarding.
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(admin.router)

# =============================================================================
# Core Endpoints
# =============================================================================
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and Docker"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "1.0.0"
    }

@app.get("/info")
async def api_info():
    """API information and configuration"""
    return {
        "app_name": settings.APP_NAME,
        "version": "1.0.0",
        "debug_mode": settings.DEBUG,
        "ollama_url": settings.OLLAMA_BASE_URL,
        "ollama_model": settings.OLLAMA_MODEL,
        "openai_enabled": settings.OPENAI_API_KEY is not None
    }

