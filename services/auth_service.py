from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
import bcrypt
import os
import secrets
from dotenv import load_dotenv

load_dotenv()

class AuthService:
    def __init__(self):
        self.secret_key = os.getenv('JWT_SECRET_KEY', 'your_secret_key_here_change_in_production')
        self.algorithm = 'HS256'
        self.access_token_expire_minutes = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '1440'))  # 24 hours default
        
        # Warn if using default secret key
        if self.secret_key == 'your_secret_key_here_change_in_production':
            print("⚠️  WARNING: Using default JWT secret key. Please set JWT_SECRET_KEY in .env file for production!")
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt with salt"""
        # Generate salt and hash the password
        salt = bcrypt.gensalt(rounds=12)  # 12 rounds is good balance of security and performance
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception as e:
            print(f"Password verification error: {e}")
            return False
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token with user data"""
        to_encode = data.copy()
        
        # Set expiration time
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        # Add standard JWT claims
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),  # Issued at
            "sub": str(data.get("user_id", "")),  # Subject (user ID)
            "type": "access_token"
        })
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            print(f"Token creation error: {e}")
            raise ValueError("Failed to create access token")
    
    def create_refresh_token(self, user_id: int) -> str:
        """Create JWT refresh token for extended authentication"""
        data = {
            "user_id": user_id,
            "type": "refresh_token",
            "exp": datetime.utcnow() + timedelta(days=30),  # Refresh tokens last 30 days
            "iat": datetime.utcnow(),
            "sub": str(user_id)
        }
        
        try:
            encoded_jwt = jwt.encode(data, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            print(f"Refresh token creation error: {e}")
            raise ValueError("Failed to create refresh token")
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token is expired (jwt.decode already does this, but let's be explicit)
            exp_timestamp = payload.get("exp")
            if exp_timestamp and datetime.utcnow().timestamp() > exp_timestamp:
                return None
            
            return payload
        except jwt.ExpiredSignatureError:
            print("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            print(f"Invalid token: {e}")
            return None
        except Exception as e:
            print(f"Token verification error: {e}")
            return None
    
    def get_user_id_from_token(self, token: str) -> Optional[int]:
        """Extract user ID from JWT token"""
        payload = self.verify_token(token)
        if payload:
            user_id = payload.get("user_id")
            if user_id:
                try:
                    return int(user_id)
                except (ValueError, TypeError):
                    return None
        return None
    
    def get_token_type(self, token: str) -> Optional[str]:
        """Get the type of token (access_token or refresh_token)"""
        payload = self.verify_token(token)
        if payload:
            return payload.get("type")
        return None
    
    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired without verifying signature"""
        try:
            # Decode without verification to check expiration
            payload = jwt.decode(token, options={"verify_signature": False})
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                return datetime.utcnow().timestamp() > exp_timestamp
            return True  # No expiration means invalid token
        except Exception:
            return True
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Generate new access token using refresh token"""
        payload = self.verify_token(refresh_token)
        
        if not payload:
            return None
        
        # Verify it's a refresh token
        if payload.get("type") != "refresh_token":
            return None
        
        user_id = payload.get("user_id")
        if not user_id:
            return None
        
        # Create new access token
        new_access_token = self.create_access_token({"user_id": user_id})
        return new_access_token
    
    def generate_password_reset_token(self, user_id: int) -> str:
        """Generate password reset token (short-lived)"""
        data = {
            "user_id": user_id,
            "type": "password_reset",
            "exp": datetime.utcnow() + timedelta(hours=1),  # 1 hour expiry
            "iat": datetime.utcnow(),
            "sub": str(user_id),
            "reset_token": secrets.token_urlsafe(16)  # Additional security
        }
        
        encoded_jwt = jwt.encode(data, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_password_reset_token(self, token: str) -> Optional[int]:
        """Verify password reset token and return user ID"""
        payload = self.verify_token(token)
        
        if not payload:
            return None
        
        # Verify it's a password reset token
        if payload.get("type") != "password_reset":
            return None
        
        user_id = payload.get("user_id")
        if user_id:
            try:
                return int(user_id)
            except (ValueError, TypeError):
                return None
        
        return None
    
    def create_session_token(self, user_id: int, device_info: Dict[str, str] = None) -> str:
        """Create session token with device information"""
        data = {
            "user_id": user_id,
            "type": "session_token",
            "session_id": secrets.token_urlsafe(16),
            "device_info": device_info or {},
            "exp": datetime.utcnow() + timedelta(hours=8),  # 8 hour sessions
            "iat": datetime.utcnow(),
            "sub": str(user_id)
        }
        
        encoded_jwt = jwt.encode(data, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """Validate password strength and return requirements check"""
        requirements = {
            "min_length": len(password) >= 8,
            "has_uppercase": any(c.isupper() for c in password),
            "has_lowercase": any(c.islower() for c in password),
            "has_digit": any(c.isdigit() for c in password),
            "has_special": any(c in "!@#$%^&*(),.?\":{}|<>" for c in password),
            "no_common_words": password.lower() not in ["password", "123456", "qwerty", "admin", "user"]
        }
        
        strength_score = sum(requirements.values())
        is_valid = strength_score >= 4  # Require at least 4 out of 6 criteria
        
        return {
            "is_valid": is_valid,
            "strength_score": strength_score,
            "max_score": len(requirements),
            "requirements": requirements,
            "suggestions": self._get_password_suggestions(requirements)
        }
    
    def _get_password_suggestions(self, requirements: Dict[str, bool]) -> list:
        """Get password improvement suggestions"""
        suggestions = []
        
        if not requirements["min_length"]:
            suggestions.append("Use at least 8 characters")
        if not requirements["has_uppercase"]:
            suggestions.append("Include at least one uppercase letter")
        if not requirements["has_lowercase"]:
            suggestions.append("Include at least one lowercase letter")
        if not requirements["has_digit"]:
            suggestions.append("Include at least one number")
        if not requirements["has_special"]:
            suggestions.append("Include at least one special character (!@#$%^&*)")
        if not requirements["no_common_words"]:
            suggestions.append("Avoid common passwords like 'password' or '123456'")
        
        return suggestions
    
    def get_token_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive token information"""
        payload = self.verify_token(token)
        
        if not payload:
            return None
        
        return {
            "user_id": payload.get("user_id"),
            "token_type": payload.get("type"),
            "issued_at": datetime.fromtimestamp(payload.get("iat", 0)),
            "expires_at": datetime.fromtimestamp(payload.get("exp", 0)),
            "subject": payload.get("sub"),
            "is_expired": self.is_token_expired(token),
            "session_id": payload.get("session_id"),
            "device_info": payload.get("device_info")
        }
    
    def generate_api_key(self, user_id: int, name: str = "API Key") -> Dict[str, str]:
        """Generate API key for programmatic access"""
        api_key = f"dlv_{secrets.token_urlsafe(32)}"  # dlv = delivery prefix
        
        # Create a long-lived token for API access
        token_data = {
            "user_id": user_id,
            "type": "api_key",
            "api_key_name": name,
            "exp": datetime.utcnow() + timedelta(days=365),  # 1 year
            "iat": datetime.utcnow(),
            "sub": str(user_id)
        }
        
        token = jwt.encode(token_data, self.secret_key, algorithm=self.algorithm)
        
        return {
            "api_key": api_key,
            "token": token,
            "expires_at": (datetime.utcnow() + timedelta(days=365)).isoformat(),
            "name": name
        }