"""Messaging system between users."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
import models
import schemas
from database import get_db
from routers.auth import get_current_user

router = APIRouter(prefix="/messages", tags=["Messaging"])

@router.post("/", response_model=schemas.MessageResponse)
def send_message(
    msg: schemas.MessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Sends a new message to another user."""

    receiver = db.query(models.User).filter(models.User.id == msg.receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver not found")

    if receiver.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot send messages to yourself")

    new_msg = models.Message(
        sender_id=current_user.id,
        receiver_id=msg.receiver_id,
        content=msg.content
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)
    return new_msg

@router.get("/inbox", response_model=List[schemas.MessageResponse])
def get_my_messages(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Retrieves the message history for the current user."""
    return db.query(models.Message).filter(
        or_(
            models.Message.receiver_id == current_user.id,
            models.Message.sender_id == current_user.id
        )
    ).order_by(models.Message.timestamp.desc()).all()

@router.get("/chat/{other_user_id}", response_model=List[schemas.MessageResponse])
def get_conversation(
    other_user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Retrieves a specific conversation between the logged-in user and another user."""
    return db.query(models.Message).filter(
        or_(
            (models.Message.sender_id == current_user.id) & (models.Message.receiver_id == other_user_id),
            (models.Message.sender_id == other_user_id) & (models.Message.receiver_id == current_user.id)
        )
    ).order_by(models.Message.timestamp.asc()).all()
