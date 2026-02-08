"""Property review and rating."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import models
import schemas
from database import get_db
from routers.auth import get_current_user  # Задължително за сигурност

router = APIRouter(prefix="/reviews", tags=["Reviews"])

@router.post("/", response_model=schemas.ReviewResponse)
def create_review(
    review_data: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Creates a new review. One user can write only one review under each property."""
    prop = db.query(models.Property).filter(models.Property.id == review_data.property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    existing_review = db.query(models.Review).filter(
        models.Review.property_id == review_data.property_id,
        models.Review.author_id == current_user.id
    ).first()

    if existing_review:
        raise HTTPException(
            status_code=400,
            detail="You have already reviewed this property."
        )

    if not 1 <= review_data.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5.")

    new_review = models.Review(
        property_id=review_data.property_id,
        author_id=current_user.id,
        rating=review_data.rating,
        comment=review_data.comment
    )

    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    return new_review

@router.get("/property/{property_id}", response_model=List[schemas.ReviewResponse])
def get_property_reviews(property_id: int, db: Session = Depends(get_db)):
    """Retrieves all reviews for a specific property."""
    return db.query(models.Review).filter(
        models.Review.property_id == property_id
    ).all()
