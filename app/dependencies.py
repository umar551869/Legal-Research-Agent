import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client, ClientOptions
from app.config import settings
from app.models import UserProfile

logger = logging.getLogger(__name__)

# Initialize Supabase Client with supported timeout options
supabase: Client = create_client(
    settings.SUPABASE_URL, 
    settings.SUPABASE_KEY,
    options=ClientOptions(
        postgrest_client_timeout=60,
        storage_client_timeout=60
    )
)

security = HTTPBearer()

def get_supabase() -> Client:
    return supabase

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserProfile:
    token = credentials.credentials
    
    # Test bypass — only active when TESTING=True (set programmatically in tests).
    # TESTING is never read from .env, so this cannot be enabled via config files.
    if settings.TESTING and token == "test-dev-token":
        return UserProfile(
            id="d866632c-7b6c-4b68-8f81-5460a8b9e6f3",
            email="test_dev@example.com",
            role="admin"
        )
        
    try:
        # Verify token with Supabase Auth
        user_response = supabase.auth.get_user(token)
        user = user_response.user
        
        if not user:
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Fetch user profile to get role
        profile_response = supabase.table("profiles").select("*").eq("id", user.id).single().execute()
        
        if not profile_response.data:
             role = "user"
        else:
             role = profile_response.data.get("role", "user")

        return UserProfile(
            id=user.id,
            email=user.email,
            role=role,
            token=token
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_admin(user: UserProfile = Depends(get_current_user)) -> UserProfile:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return user
