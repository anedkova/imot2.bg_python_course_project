"""SQLAlchemy database models for users, properties, and interactions."""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Text,
    Boolean, ForeignKey, DateTime, UniqueConstraint
)
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    hashed_password = Column(String)
    role = Column(String, default="client")
    is_verified = Column(Boolean, default=False)

    properties = relationship("Property", back_populates="owner")
    bookings = relationship("Booking", back_populates="client")
    reviews_given = relationship("Review", back_populates="author")
    favorites = relationship("Favorite", back_populates="user")


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    price = Column(Float)
    property_type = Column(String)  # "rent" или "sale"
    location = Column(String)
    status = Column(String, default="available")  # "available", "sold", "rented"
    is_active = Column(Boolean, default=True)
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="properties")
    images = relationship("PropertyImage", back_populates="property", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="property", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="property", cascade="all, delete-orphan")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"))
    client_id = Column(Integer, ForeignKey("users.id"))
    booking_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String, default="pending")

    property = relationship("Property", back_populates="bookings")
    client = relationship("User", back_populates="bookings")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"))
    author_id = Column(Integer, ForeignKey("users.id"))
    rating = Column(Integer)  # 1 до 5
    comment = Column(Text)

    property = relationship("Property", back_populates="reviews")
    author = relationship("User", back_populates="reviews_given")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])


class PropertyImage(Base):
    __tablename__ = "property_images"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"))
    url = Column(String)  # Път: static/uploads/image.jpg

    property = relationship("Property", back_populates="images")


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    property_id = Column(Integer, ForeignKey("properties.id"))

    user = relationship("User", back_populates="favorites")
    property = relationship("Property")

    __table_args__ = (
        UniqueConstraint('user_id', 'property_id', name='_user_property_favorite_uc'),
    )
