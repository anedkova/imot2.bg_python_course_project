"""Administrative dashboard routes for system statistics and user verification."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List
import models
import schemas
from database import get_db
from .auth import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin Panel"])


@router.get("/stats")
def get_admin_stats(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """Returns statistics for properties, bookings and reviews count."""

    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access denied: Administrative privileges required"
        )

    stats = {
        "user_stats": {
            "total_users": db.query(models.User).count(),
            "verified_agents": db.query(models.User).filter(
                models.User.role == "agent",
                models.User.is_verified
            ).count(),
            "pending_verifications": db.query(models.User).filter(
                models.User.role == "agent",
                models.User.is_verified == False
            ).count()
        },
        "content_stats": {
            "total_properties": db.query(models.Property).count(),
            "total_bookings": db.query(models.Booking).count(),
            "total_reviews": db.query(models.Review).count()
        },
        "system_info": {
            "report_generated_at": datetime.now(timezone.utc).isoformat(),
            "admin_user": current_user.username
        }
    }

    return stats


@router.patch("/verify/{user_id}", response_model=schemas.UserResponse)
def verify_user(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """Allows administrative users to verify (approve) a user or agent profile."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Permission denied: Insufficient privileges"
        )

    user_to_verify = db.query(models.User).filter(models.User.id == user_id).first()

    if not user_to_verify:
        raise HTTPException(status_code=404, detail="Target user not found")

    if user_to_verify.is_verified:
        raise HTTPException(status_code=400, detail="User is already verified")

    user_to_verify.is_verified = True
    db.commit()
    db.refresh(user_to_verify)
    return user_to_verify


@router.get("/reviews", response_model=List[schemas.ReviewResponse])
def get_all_reviews(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """Retrieves all reviews."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    return db.query(models.Review).all()


@router.delete("/reviews/{review_id}")
def delete_review(
        review_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """Allows administrative users to delete a review."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    db.delete(review)
    db.commit()
    return {"message": f"Review {review_id} has been deleted by admin"}


@router.get("/bookings", response_model=List[schemas.BookingResponse])
def get_all_bookings(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """Retrieves all bookings."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    return db.query(models.Booking).all()
