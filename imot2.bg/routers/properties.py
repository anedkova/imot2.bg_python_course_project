"""Search, creation, and image uploads for properties."""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Request
from sqlalchemy.orm import Session
import shutil
from typing import List, Optional
import models
import schemas
from database import get_db
from .auth import get_current_user
import os, uuid

router = APIRouter(prefix="/properties", tags=["Properties"])


@router.get("/", response_model=List[schemas.PropertyResponse])
def get_properties(
        title: Optional[str] = None,
        prop_type: Optional[str] = None,
        location: Optional[str] = None,
        db: Session = Depends(get_db)
):
    """Retrieves a list of properties. Supports filtering by title, category, and location."""
    query = db.query(models.Property).join(models.User).filter(
        models.User.is_verified
    )

    if title:
        query = query.filter(models.Property.title.ilike(f"%{title}%"))

    if prop_type:
        query = query.filter(models.Property.property_type == prop_type)

    if location:
        query = query.filter(models.Property.location.ilike(f"%{location}%"))

    return query.all()


@router.post("/{property_id}/upload-image")
async def upload_image(
        property_id: int,
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """Uploads a single image for a specific property."""
    property_item = db.query(models.Property).filter(models.Property.id == property_id).first()

    if not property_item:
        raise HTTPException(status_code=404, detail="Property not found")

    if property_item.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied: You do not own this property")

    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    upload_dir = "static/uploads"

    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, unique_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception:
        raise HTTPException(status_code=500, detail="Could not save file")

    new_image = models.PropertyImage(property_id=property_id, url=f"/{file_path}")
    db.add(new_image)
    db.commit()
    db.refresh(new_image)

    return {"message": "Image uploaded successfully", "url": new_image.url}


@router.post("/", response_model=schemas.PropertyResponse)
def create_property(
        property_data: schemas.PropertyCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """Creates a new property listing linked to an agent."""
    if current_user.role not in ["agent", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="Permission denied: Only agents can create listings"
        )

    if not current_user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Account not verified: Please wait for admin approval"
        )

    new_prop = models.Property(
        title=property_data.title,
        price=property_data.price,
        property_type=property_data.property_type,
        location=property_data.location,
        description=property_data.description,
        owner_id=current_user.id
    )

    try:
        db.add(new_prop)
        db.commit()
        db.refresh(new_prop)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error during creation")

    return new_prop


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property(
        property_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """Deletes a property listing and its details(pictures)."""
    db_property = db.query(models.Property).filter(models.Property.id == property_id).first()

    if not db_property:
        raise HTTPException(status_code=404, detail="Property listing not found")

    if db_property.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Permission denied: You are not the owner of this listing"
        )

    for image in db_property.images:
        try:
            file_path = image.url.lstrip('/')
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file {image.url}: {e}")

    db.delete(db_property)
    db.commit()

    return None


@router.get("/{property_id}", response_model=schemas.PropertyResponse)
def get_property_details(
        property_id: int,
        db: Session = Depends(get_db),):
    """Detailed view for a specific property."""
    db_property = db.query(models.Property).filter(models.Property.id == property_id).first()
    if not db_property:
        raise HTTPException(status_code=404, detail="Property not found")

    return db_property
