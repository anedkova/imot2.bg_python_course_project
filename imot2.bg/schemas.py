"""Pydantic schemas for data validation and serialization."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr, ConfigDict


class UserBase(BaseModel):
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    role: str = "client"


class UserCreate(UserBase):
    password: str = Field(..., max_length=72)


class UserResponse(UserBase):
    id: int
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)

class UserLogin(BaseModel   ):
    username: str
    password: str

class ReviewCreate(BaseModel):
    property_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class ReviewResponse(ReviewCreate):
    id: int
    author_id: int

    model_config = ConfigDict(from_attributes=True)


class BookingCreate(BaseModel):
    property_id: int
    booking_date: datetime


class BookingResponse(BookingCreate):
    id: int
    client_id: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    receiver_id: int
    content: str


class MessageResponse(MessageCreate):
    id: int
    sender_id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class ImageResponse(BaseModel):
    url: str

    model_config = ConfigDict(from_attributes=True)


class PropertyCreate(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    property_type: str
    location: str


class PropertyResponse(PropertyCreate):
    id: int
    owner_id: int
    status: str
    images: List[ImageResponse] = []

    model_config = ConfigDict(from_attributes=True)


class FavoriteBase(BaseModel):
    property_id: int


class FavoriteResponse(FavoriteBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)
