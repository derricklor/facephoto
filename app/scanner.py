import os
from deepface import DeepFace
from sqlalchemy.orm import Session
from .models import Photo, Person, FaceEmbedding
from .database import SessionLocal
import numpy as np
from sklearn.cluster import DBSCAN

def get_image_paths(directory):
    valid_extensions = ('.jpg', '.jpeg', '.png', '.webp')
    image_paths = []
    for root, _, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(valid_extensions):
                image_paths.append(os.path.join(root, f))
    return image_paths

def extract_embeddings(img_path):
    try:
        representations = DeepFace.represent(img_path=img_path, model_name="VGG-Face", enforce_detection=True)
        return representations, None
    except Exception as e:
        return [], str(e)

def process_directory(directory: str, progress_callback=None):
    db = SessionLocal()
    errors = []
    try:
        image_paths = get_image_paths(directory)
        total_photos = len(image_paths)
        all_embeddings = []
        mapping = [] # stores (photo_id, embedding_index_in_photo, region)

        if progress_callback:
            progress_callback(0, total_photos, "Scanning directory...")

        for idx, path in enumerate(image_paths):
            if progress_callback:
                progress_callback(idx, total_photos, f"Processing {os.path.basename(path)}", errors=errors)
                
            # Check if photo already exists in DB
            photo = db.query(Photo).filter(Photo.path == path).first()
            if not photo:
                photo = Photo(path=path)
                db.add(photo)
                db.commit()
                db.refresh(photo)
            
            # Extract embeddings if not already extracted
            if not photo.embeddings:
                reps, err = extract_embeddings(path)
                if err:
                    errors.append({"file": os.path.basename(path), "error": err})
                
                for i, rep in enumerate(reps):
                    embedding = rep["embedding"]
                    region = rep["facial_area"]
                    
                    face_emb = FaceEmbedding(photo_id=photo.id, embedding=embedding, region=region)
                    db.add(face_emb)
                    all_embeddings.append(embedding)
                    mapping.append((photo.id, i, region))
            else:
                for face_emb in photo.embeddings:
                    all_embeddings.append(face_emb.embedding)
                    mapping.append((photo.id, 0, face_emb.region))
        
        if all_embeddings:
            if progress_callback:
                progress_callback(total_photos, total_photos, "Clustering faces...", errors=errors)
            db.commit()
            # Run clustering
            cluster_faces(all_embeddings, mapping, db)
        
        if progress_callback:
            progress_callback(total_photos, total_photos, "Completed", errors=errors)
            
    finally:
        db.close()

def cluster_faces(embeddings, mapping, db: Session):
    if not embeddings:
        return

    # Convert to numpy array for clustering
    X = np.array(embeddings)
    
    # DBSCAN clustering
    # eps and min_samples might need tuning
    clustering = DBSCAN(eps=0.6, min_samples=3, metric="cosine").fit(X)
    labels = clustering.labels_
    
    # Map clusters to people
    unique_labels = set(labels)
    for label in unique_labels:
        if label == -1: # Noise in DBSCAN
            continue
            
        person = Person(name=f"Person {label}")
        db.add(person)
        db.commit()
        db.refresh(person)
        
        # Assign photos to this person
        indices = np.where(labels == label)[0]
        for idx in indices:
            photo_id, _, _ = mapping[idx]
            photo = db.query(Photo).filter(Photo.id == photo_id).first()
            if photo:
                photo.person_id = person.id
                # Use the first photo as a thumbnail for now
                if not person.thumbnail_path:
                    person.thumbnail_path = photo.path
        
        db.commit()
