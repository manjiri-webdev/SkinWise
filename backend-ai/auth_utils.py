import os
import jwt
from jwt import PyJWKClient, PyJWKClientError
from dotenv import load_dotenv
from fastapi import HTTPException, Header
from typing import Optional, Dict, Any

# Load environment variables from .env file
load_dotenv()

# In-memory cached PyJWKClient instance for Supabase JWKS verification
_jwks_client: Optional[PyJWKClient] = None
_jwks_url: Optional[str] = None


def get_jwks_client() -> Optional[PyJWKClient]:
    """
    Get or initialize cached PyJWKClient for Supabase JWKS verification.
    Fetches public keys from Supabase's .well-known/jwks.json endpoint.
    """
    global _jwks_client, _jwks_url
    supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    if not supabase_url:
        return None
    
    expected_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
    if _jwks_client is None or _jwks_url != expected_url:
        _jwks_url = expected_url
        _jwks_client = PyJWKClient(_jwks_url, cache_keys=True, cache_jwk_set=True, lifespan=3600)
    
    return _jwks_client


def get_jwt_secret() -> str:
    """
    Get the shared JWT secret from environment variables for HS256 verification.
    """
    secret = os.getenv("SUPABASE_JWT_SECRET", "").strip()
    if not secret or secret == "your_jwt_secret_here":
        return ""
    return secret


def verify_supabase_jwt(token: str) -> Dict[str, Any]:
    """
    Cryptographically verify a Supabase JWT token.
    
    Supports:
    - Asymmetric signing (ES256, RS256) via Supabase JWKS endpoint
    - Symmetric signing (HS256) via SUPABASE_JWT_SECRET
    
    Never falls back to verify_signature=False.
    Raises HTTPException(status_code=401) on any failure.
    """
    try:
        header = jwt.get_unverified_header(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token format: {str(e)}")
    
    alg = header.get("alg")
    if not alg or alg.lower() == "none":
        raise HTTPException(status_code=401, detail="Invalid token: algorithm 'none' is not allowed")
    
    decoded: Optional[Dict[str, Any]] = None
    
    # Asymmetric verification (ES256, RS256) via JWKS
    if alg in ["ES256", "RS256"]:
        jwks_client = get_jwks_client()
        if not jwks_client:
            raise HTTPException(
                status_code=401,
                detail="Authentication failed: SUPABASE_URL not configured for JWKS verification"
            )
        try:
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            decoded = jwt.decode(
                token,
                signing_key.key,
                algorithms=[alg],
                options={"verify_signature": True, "verify_exp": True, "verify_aud": False}
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidSignatureError:
            raise HTTPException(status_code=401, detail="Invalid token signature")
        except PyJWKClientError as e:
            raise HTTPException(status_code=401, detail=f"JWKS key lookup failed: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")
            
    # Symmetric verification (HS256) via SUPABASE_JWT_SECRET
    elif alg == "HS256":
        secret = get_jwt_secret()
        if not secret:
            raise HTTPException(
                status_code=401,
                detail="Authentication failed: SUPABASE_JWT_SECRET not configured for HS256 verification"
            )
        try:
            decoded = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options={"verify_signature": True, "verify_exp": True, "verify_aud": False}
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidSignatureError:
            raise HTTPException(status_code=401, detail="Invalid token signature")
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")
            
    else:
        raise HTTPException(status_code=401, detail=f"Unsupported token algorithm: {alg}")
    
    if not decoded:
        raise HTTPException(status_code=401, detail="Token validation failed")
        
    return decoded


async def get_current_user(authorization: str = Header(...)) -> str:
    """
    Validate Supabase JWT token and extract user ID.
    
    This function:
    - Validates the Bearer token format
    - Cryptographically verifies the token signature and expiration
    - Extracts the user ID (sub claim)
    - Returns the user ID if valid
    
    Never accepts unverified tokens.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty bearer token")
    
    decoded = verify_supabase_jwt(token)
    user_id = decoded.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: no user ID found")
    
    return str(user_id)
