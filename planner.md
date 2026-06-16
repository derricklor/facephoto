# FacePhoto - Project Planner & Todo List

This document outlines the roadmap, features, and implementation plan for FacePhoto.

## Active Task: Multi-Face Extraction and Association
Support extracting multiple faces from a single photo and clustering them independently, so that one photo can belong to multiple people.

- [x] Modify database models (`models.py`) to move the `person_id` relationship from `Photo` to `FaceEmbedding`.
- [x] Create database reset utility (`recreate_db.py`) to drop/recreate database tables for the new schema. (Skipped/Assumed clean DB)
- [x] Update background scanning & clustering (`scanner.py`) to map embeddings to `FaceEmbedding` records, run DBSCAN, and assign people to individual embeddings. Add cleanup for orphaned people.
- [x] Implement a cropped face thumbnail endpoint (`/api/face/{id}/thumbnail`) in the API (`main.py`) to serve face crops.
- [x] Update frontend rendering (`main.js`) to support direct cropped face thumbnail URLs in the sidebar and merge modals.
- [x] Update bulk actions, merges, deletes, and clear cache APIs in `main.py` to handle the face embedding-based ownership model.

---

## Future Features & Improvements

### 1. Enhanced UI / UX & Visual Polish
- [ ] **Face Highlighting overlay**: In the photo zoom view, draw bounding boxes around recognized faces with tooltips showing the person's name.
- [ ] **Interactive manual face tagging**: Allow users to draw bounding boxes and manually tag unrecognized or misidentified faces.
- [ ] **Search functionality**: Add a search bar at the top of the sidebar to quickly filter people by name.
- [ ] **Loading skeletons & smooth transitions**: Add subtle micro-animations and loading states when scanning or fetching galleries.

### 2. Scanner & Clustering Enhancements
- [ ] **Incremental scanning**: Only scan new/modified files rather than re-scanning the entire directory.
- [ ] **Configurable clustering parameters**: Allow adjusting DBSCAN distance metric and epsilon threshold from the settings UI.
- [ ] **Model selection enhancements**: Allow changing facial recognition models (e.g., Facenet, ArcFace) with automatic database partitioning.

### 3. Performance & Scaling
- [ ] **Batched database operations**: Optimize database writes during scanning using bulk inserts.
- [ ] **GPU Acceleration**: Add checks and setup instructions for CUDA/GPU-enabled TensorFlow to accelerate Face representation extraction.
