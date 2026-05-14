import logging
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse
from app.models import UserSignup, UserLogin, Token, UserProfile, AuthMeResponse
from app.dependencies import get_supabase, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/signup")
async def signup(user_data: UserSignup, background_tasks: BackgroundTasks):
    """Register a new user via Supabase Auth.
    
    Returns a Token if the session is created immediately, or a JSON message
    if email confirmation is required.
    """
    supabase = get_supabase()
    try:
        response = supabase.auth.sign_up({
            "email": user_data.email, 
            "password": user_data.password
        })
        
        if response.session:
            # Session was created immediately (email confirmation disabled or auto-confirmed)
            from app.services.research import research_service
            background_tasks.add_task(research_service._ensure_embedding_model)
            background_tasks.add_task(research_service._ensure_summarizer_loaded)
            return Token(
                access_token=response.session.access_token,
                token_type=response.session.token_type
            )
        else:
            # Email confirmation required — no session yet
            return JSONResponse(
                status_code=201,
                content={
                    "detail": "Registration successful. Please check your email to confirm your account.",
                    "requires_confirmation": True,
                }
            )

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Signup error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, background_tasks: BackgroundTasks):
    """Authenticate and return a Supabase access token."""
    supabase = get_supabase()
    try:
        response = supabase.auth.sign_in_with_password({
            "email": user_data.email,
            "password": user_data.password
        })
        
        if response.session:
            from app.services.research import research_service
            background_tasks.add_task(research_service._ensure_embedding_model)
            background_tasks.add_task(research_service._ensure_summarizer_loaded)
            return Token(
                access_token=response.session.access_token,
                token_type=response.session.token_type
            )
        else:
            raise HTTPException(status_code=400, detail="Login failed — no session returned")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid credentials")

@router.get("/me", response_model=AuthMeResponse)
async def get_me(current_user: UserProfile = Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    return AuthMeResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
    )

@router.post("/logout")
async def logout():
    """Logout endpoint. 
    
    Supabase tokens are stateless JWTs — the frontend clears local storage.
    This endpoint exists for API contract symmetry.
    """
    return {"detail": "Logged out successfully"}
