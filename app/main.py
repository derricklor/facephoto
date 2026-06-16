from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from .models import Photo, Person, FaceEmbedding
from .scanner import process_directory
import os

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FacePhoto API")

import time

# Global scan status tracking
scan_status = {
    "is_active": False,
    "current": 0,
    "total": 0,
    "status": "Idle",
    "directory": "",
    "errors": [],
    "start_time": 0,
    "elapsed_time": 0,
    "estimated_remaining": 0
}

@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("static/index.html", "r") as f:
        return f.read()

@app.get("/api/image")
def get_image(path: str):
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)

@app.get("/api/face/{embedding_id}/thumbnail")
def get_face_thumbnail(embedding_id: int, db: Session = Depends(get_db)):
    face_emb = db.query(FaceEmbedding).filter(FaceEmbedding.id == embedding_id).first()
    if not face_emb:
        raise HTTPException(status_code=404, detail="Face embedding not found")
    
    photo_path = face_emb.photo.path
    if not os.path.exists(photo_path):
        raise HTTPException(status_code=404, detail="Original photo not found")
        
    try:
        from PIL import Image
        import io
        from fastapi.responses import StreamingResponse
        
        region = face_emb.region
        x, y, w, h = region['x'], region['y'], region['w'], region['h']
        
        with Image.open(photo_path) as img:
            box = (x, y, x + w, y + h)
            cropped = img.crop(box)
            
            img_io = io.BytesIO()
            fmt = img.format if img.format else "JPEG"
            cropped.save(img_io, format=fmt)
            img_io.seek(0)
            
            media_type = f"image/{fmt.lower()}"
            if fmt.lower() == "jpg":
                media_type = "image/jpeg"
            return StreamingResponse(img_io, media_type=media_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to crop face: {str(e)}")

@app.get("/api/browse")
def browse_directory():
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        root.attributes('-topmost', True)  # Bring to front
        
        directory = filedialog.askdirectory()
        root.destroy()
        
        if directory:
            return {"path": directory}
        return {"path": ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to open folder dialog: {str(e)}")

def run_scan(directory: str, model: str):
    global scan_status
    scan_status["is_active"] = True
    scan_status["directory"] = directory
    scan_status["status"] = "Preparing..."
    scan_status["current"] = 0
    scan_status["total"] = 0
    scan_status["errors"] = []
    scan_status["start_time"] = time.time()
    scan_status["estimated_remaining"] = 0
    
    try:
        def update_progress(current, total, status_text=None, errors=None):
            scan_status["current"] = current
            scan_status["total"] = total
            if errors:
                scan_status["errors"] = errors
            if status_text:
                scan_status["status"] = status_text
            else:
                scan_status["status"] = f"Processing {current}/{total}"
            
            # Update timing
            if current > 0:
                elapsed = time.time() - scan_status["start_time"]
                scan_status["elapsed_time"] = elapsed
                avg_time_per_item = elapsed / current
                remaining_items = total - current
                scan_status["estimated_remaining"] = avg_time_per_item * remaining_items

        process_directory(directory, model=model, progress_callback=update_progress)
        scan_status["status"] = "Completed"
        scan_status["estimated_remaining"] = 0
    except Exception as e:
        scan_status["status"] = f"Error: {str(e)}"
    finally:
        scan_status["is_active"] = False

@app.post("/api/scan")
def scan_directory(directory: str, model: str, background_tasks: BackgroundTasks):
    if not os.path.exists(directory) or not os.path.isdir(directory):
        raise HTTPException(status_code=400, detail="Invalid directory path")
    
    if scan_status["is_active"]:
        raise HTTPException(status_code=400, detail="A scan is already in progress")
        
    background_tasks.add_task(run_scan, directory, model)
    return {"status": "Scanning started", "directory": directory}

@app.get("/api/scan/progress")
def get_scan_progress():
    if scan_status["is_active"] and scan_status["current"] > 0:
        elapsed = time.time() - scan_status["start_time"]
        scan_status["elapsed_time"] = elapsed
        # Recalculate just in case update_progress wasn't called recently
        avg_time_per_item = elapsed / scan_status["current"]
        remaining_items = scan_status["total"] - scan_status["current"]
        scan_status["estimated_remaining"] = avg_time_per_item * remaining_items
    return scan_status

@app.get("/api/groups")
def get_groups(db: Session = Depends(get_db)):
    people = db.query(Person).all()
    result = []
    for person in people:
        seen_photo_ids = set()
        photos = []
        for emb in person.embeddings:
            if emb.photo and emb.photo.id not in seen_photo_ids:
                seen_photo_ids.add(emb.photo.id)
                photos.append({"id": emb.photo.id, "path": emb.photo.path})
        
        thumbnail = None
        if person.embeddings:
            thumbnail = f"/api/face/{person.embeddings[0].id}/thumbnail"
        elif person.thumbnail_path:
            thumbnail = f"/api/image?path={person.thumbnail_path}"
            
        result.append({
            "id": person.id,
            "name": person.name,
            "thumbnail": thumbnail,
            "photo_count": len(photos),
            "photos": photos
        })
    return result

class BulkPhotoUpdate(BaseModel):
    photo_ids: list[int]
    source_person_id: int | None = None
    target_person_id: int | None = None

@app.patch("/api/photos/bulk")
def bulk_update_photos(update: BulkPhotoUpdate, db: Session = Depends(get_db)):
    embeddings = db.query(FaceEmbedding).filter(
        FaceEmbedding.photo_id.in_(update.photo_ids),
        FaceEmbedding.person_id == update.source_person_id
    ).all()
    
    for emb in embeddings:
        emb.person_id = update.target_person_id
    db.commit()
    return {"status": "Photos updated", "count": len(embeddings)}

class PersonUpdate(BaseModel):
    name: str

@app.patch("/api/groups/{person_id}")
def update_person(person_id: int, update: PersonUpdate, db: Session = Depends(get_db)):
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    person.name = update.name
    db.commit()
    return {"status": "Person updated", "id": person_id, "name": update.name}

@app.post("/api/groups/{person_id}/merge/{target_id}")
def merge_people(person_id: int, target_id: int, db: Session = Depends(get_db)):
    source_person = db.query(Person).filter(Person.id == person_id).first()
    target_person = db.query(Person).filter(Person.id == target_id).first()
    
    if not source_person or not target_person:
        raise HTTPException(status_code=404, detail="Person not found")
    
    if person_id == target_id:
        raise HTTPException(status_code=400, detail="Cannot merge a person with themselves")
    
    for emb in source_person.embeddings:
        emb.person_id = target_id
    
    db.commit()
    db.delete(source_person)
    db.commit()
    return {"status": "People merged", "source_id": person_id, "target_id": target_id}

@app.post("/api/groups/{person_id}/export")
def export_person(person_id: int, db: Session = Depends(get_db)):
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    
    try:
        import tkinter as tk
        from tkinter import filedialog
        import shutil
        
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        dest_root = filedialog.askdirectory(title="Select Destination Folder for Export")
        root.destroy()
        
        if not dest_root:
            return {"status": "Cancelled"}
            
        safe_name = "".join([c for c in person.name if c.isalnum() or c in (' ', '.', '_')]).strip()
        export_path = os.path.join(dest_root, safe_name)
        
        if not os.path.exists(export_path):
            os.makedirs(export_path)
            
        seen_photo_ids = set()
        unique_photos = []
        for emb in person.embeddings:
            if emb.photo and emb.photo.id not in seen_photo_ids:
                seen_photo_ids.add(emb.photo.id)
                unique_photos.append(emb.photo)
                
        count = 0
        for photo in unique_photos:
            if os.path.exists(photo.path):
                filename = os.path.basename(photo.path)
                target_file = os.path.join(export_path, filename)
                if os.path.exists(target_file):
                    name_parts = os.path.splitext(filename)
                    target_file = os.path.join(export_path, f"{name_parts[0]}_{photo.id}{name_parts[1]}")
                
                shutil.copy2(photo.path, target_file)
                count += 1
                
        return {"status": "Exported", "count": count, "destination": export_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.delete("/api/groups/{person_id}")
def delete_person(person_id: int, db: Session = Depends(get_db)):
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    for emb in person.embeddings:
        emb.person_id = None
    db.delete(person)
    db.commit()
    return {"status": "Person deleted", "id": person_id}

@app.delete("/api/clearcache")
def clear_cache(db: Session = Depends(get_db)):
    from sqlalchemy import not_
    orphaned_photos = db.query(Photo).filter(
        not_(Photo.embeddings.any(FaceEmbedding.person_id != None))
    ).all()
    photo_ids = [p.id for p in orphaned_photos]
    
    if not photo_ids:
        return {"status": "Cache already clear", "count": 0}

    db.query(FaceEmbedding).filter(FaceEmbedding.photo_id.in_(photo_ids)).delete(synchronize_session=False)
    db.query(Photo).filter(Photo.id.in_(photo_ids)).delete(synchronize_session=False)
    db.commit()
    return {"status": "Cache cleared", "count": len(photo_ids)}

@app.post("/api/resetdb")
def reset_db(db: Session = Depends(get_db)):
    try:
        from app.database import engine, Base
        # Import models to register them before drop/create
        from app.models import Photo, Person, FaceEmbedding
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        return {"status": "Database reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database reset failed: {str(e)}")

app.mount("/", StaticFiles(directory="static"), name="static")
