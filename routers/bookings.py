"""Booking and calendar scheduling for property viewings."""
from datetime import date
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
import models
import schemas
from database import get_db
from routers.auth import get_current_user

router = APIRouter(prefix="/bookings", tags=["Bookings & Calendar"])

@router.post("/", response_model=schemas.BookingResponse)
def create_booking(
    booking_data: schemas.BookingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Creates a property viewing booking."""
    prop = db.query(models.Property).filter(models.Property.id == booking_data.property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    existing_booking = db.query(models.Booking).filter(
        models.Booking.property_id == booking_data.property_id,
        models.Booking.booking_date == booking_data.booking_date,
        models.Booking.status == "confirmed"
    ).first()

    if existing_booking:
        raise HTTPException(
            status_code=400,
            detail="This time slot is already booked."
        )

    new_booking = models.Booking(
        property_id=booking_data.property_id,
        client_id=current_user.id,
        booking_date=booking_data.booking_date,
        status="pending"
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    return new_booking

@router.get("/calendar", response_model=List[schemas.BookingResponse])
def get_daily_schedule(
    day: date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Returns the agent's schedule for a specific day."""
    if current_user.role not in ["agent", "admin"]:
        raise HTTPException(status_code=403, detail="Only agents can view schedules")

    return db.query(models.Booking).join(models.Property).filter(
        models.Property.owner_id == current_user.id,
        func.date(models.Booking.booking_date) == day
    ).order_by(models.Booking.booking_date.asc()).all()

@router.patch("/{booking_id}/status")
def update_booking_status(
    booking_id: int,
    new_status: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Allows the agent to confirm or decline a booking."""
    booking = db.query(models.Booking).join(models.Property).filter(
        models.Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.property.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You can only manage bookings for your own properties")

    if new_status not in ["confirmed", "declined"]:
        raise HTTPException(status_code=400, detail="Invalid status. Use 'confirmed' or 'declined'.")

    booking.status = new_status
    db.commit()
    return {"message": f"Booking status updated to: {new_status}"}
