"""Authentication routes for user registration, login, and logout."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from starlette.responses import JSONResponse
import models
import schemas
from database import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])
templates = Jinja2Templates(directory="templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    db_user = db.query(models.User).filter(
        (models.User.email == user.email) | (models.User.username == user.username)
    ).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email or Username already exists")

    if user.role not in ["client", "agent"]:
        raise HTTPException(status_code=400, detail="Invalid role selection")

    hashed_pass = pwd_context.hash(user.password)

    new_user = models.User(
        email=user.email,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        hashed_password=hashed_pass,
        role=user.role,
        is_verified=False
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Dependency function to retrieve the currently logged-in user from the session cookie."""
    username = request.cookies.get("username")
    if not username:
        raise HTTPException(
            status_code=401,
            detail="User not authenticated"
        )

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


@router.post("/login")
def login(
        login_data: schemas.UserLogin,
        db: Session = Depends(get_db)
):
    """Authenticates a user by username and password, sets a secure HTTP-only cookie to maintain the session."""
    user = db.query(models.User).filter(models.User.username == login_data.username).first()

    if not user or not pwd_context.verify(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    response = JSONResponse(content={"message": "Login successful"})
    response.set_cookie(key="username", value=user.username, httponly=True)
    return response


@router.get("/logout")
def logout():
    """Terminates the user session by deleting the 'username' cookie."""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="username")
    return response
