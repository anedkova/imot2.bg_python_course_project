"""Main application entry point and route definitions for Imot2.bg."""
from typing import Optional
from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models
from database import engine, get_db
from routers import auth, properties, bookings, reviews, messages, admin
from routers.auth import get_current_user
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Imot2.bg API")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(auth.router)
app.include_router(properties.router)
app.include_router(bookings.router)
app.include_router(reviews.router)
app.include_router(messages.router)
app.include_router(admin.router)

@app.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    """Home page with a personalized greeting for logged-in users."""
    username = request.cookies.get("username")
    current_user = None

    if username:
        current_user = db.query(models.User).filter(models.User.username == username).first()

    return templates.TemplateResponse(request, "index.html", {"user": current_user})


@app.get("/login")
def get_login_page(request: Request):
    """Displays the login page."""
    return templates.TemplateResponse(request, "login.html")

@app.get("/register")
def get_register_page(request: Request):
    """Displays the registration page."""
    return templates.TemplateResponse(request, "register.html")

@app.get("/add-property")
def get_add_property_page(request: Request, current_user: models.User = Depends(get_current_user)):
    """Displays the property creation form. Restricted to logged-in users."""
    return templates.TemplateResponse("create_property.html", {"request": request, "user": current_user})

@app.get("/properties/manage")
def manage_properties_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Dashboard for agents to manage their own property listings."""
    my_properties = db.query(models.Property).filter(
        models.Property.owner_id == current_user.id
    ).all()

    return templates.TemplateResponse(request, "manage_properties.html", {
        "properties": my_properties,
        "user": current_user
    })

@app.get("/properties-page")
def search_properties_page(
        request: Request,
        p_type: Optional[str] = None,
        city: Optional[str] = None,
        max_price: Optional[float] = None,
        db: Session = Depends(get_db)
):
    """Search page with dynamic filtering of properties."""
    query = db.query(models.Property).join(models.User).filter(models.User.is_verified)

    if p_type:
        query = query.filter(models.Property.property_type == str(p_type))
    if city:
        query = query.filter(models.Property.location.ilike(f"%{city}%"))
    if max_price:
        query = query.filter(models.Property.price <= max_price)

    properties_list = query.all()

    username = request.cookies.get("username")
    current_user = db.query(models.User).filter(models.User.username == username).first() if username else None

    return templates.TemplateResponse(request, "search_properties.html", {
        "properties": properties_list,
        "user": current_user
    })
