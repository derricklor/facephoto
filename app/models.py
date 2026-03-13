from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .database import Base

class Person(Base):
    __tablename__ = "people"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, default="Unknown")
    # Representative thumbnail or image path
    thumbnail_path = Column(String, nullable=True)
    
    photos = relationship("Photo", back_populates="person")

class Photo(Base):
    __tablename__ = "photos"
    
    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, index=True)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=True)
    
    person = relationship("Person", back_populates="photos")
    embeddings = relationship("FaceEmbedding", back_populates="photo")

class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id"))
    # Embedding vector stored as JSON
    embedding = Column(JSON)
    # Location of the face in the image
    region = Column(JSON)
    
    photo = relationship("Photo", back_populates="embeddings")
