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

# Global scan status tracking
scan_status = {
    "is_active": False,
    "current": 0,
    "total": 0,
    "status": "Idle",
    "directory": "",
    "errors": []
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

        process_directory(directory, model=model, progress_callback=update_progress)
        scan_status["status"] = "Completed"
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
    return scan_status

@app.get("/api/groups")
def get_groups(db: Session = Depends(get_db)):
    people = db.query(Person).all()
    result = []
    for person in people:
        photos = [{"id": p.id, "path": p.path} for p in person.photos]
        result.append({
            "id": person.id,
            "name": person.name,
            "thumbnail": person.thumbnail_path,
            "photo_count": len(photos),
            "photos": photos
        })
    return result

class BulkPhotoUpdate(BaseModel):
    photo_ids: list[int]
    target_person_id: int | None = None

@app.patch("/api/photos/bulk")
def bulk_update_photos(update: BulkPhotoUpdate, db: Session = Depends(get_db)):
    photos = db.query(Photo).filter(Photo.id.in_(update.photo_ids)).all()
    for photo in photos:
        photo.person_id = update.target_person_id
    db.commit()
    return {"status": "Photos updated", "count": len(photos)}

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
    
    photos_to_move = list(source_person.photos)
    for photo in photos_to_move:
        photo.person_id = target_id
    
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
            
        # Clean name for filesystem
        safe_name = "".join([c for c in person.name if c.isalnum() or c in (' ', '.', '_')]).strip()
        export_path = os.path.join(dest_root, safe_name)
        
        if not os.path.exists(export_path):
            os.makedirs(export_path)
            
        count = 0
        for photo in person.photos:
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
    for photo in person.photos:
        photo.person_id = None
    db.delete(person)
    db.commit()
    return {"status": "Person deleted", "id": person_id}

@app.delete("/api/clearcache")
def clear_cache(db: Session = Depends(get_db)):
    # Query photos with no person_id
    orphaned_photos = db.query(Photo).filter(Photo.person_id == None).all()
    photo_ids = [p.id for p in orphaned_photos]
    
    if not photo_ids:
        return {"status": "Cache already clear", "count": 0}

    # Delete face embeddings for these photos
    db.query(FaceEmbedding).filter(FaceEmbedding.photo_id.in_(photo_ids)).delete(synchronize_session=False)
    
    # Delete the photos themselves
    db.query(Photo).filter(Photo.id.in_(photo_ids)).delete(synchronize_session=False)
    
    db.commit()
    return {"status": "Cache cleared", "count": len(photo_ids)}

app.mount("/", StaticFiles(directory="static"), name="static")
