# FacePhoto - AI Photo Organizer

FacePhoto is a web-based, AI-powered photo organizer that automatically groups and organizes your local photos by the people identified in them. Using state-of-the-art facial recognition, it clusters similar faces together, allowing you to easily browse, rename, and manage your photo collection.

## Features

- **AI Face Identification**: Automatically scans directories and groups photos of the same person using `DeepFace` and `DBSCAN` clustering.
- **Web Interface**: Modern, responsive dashboard for browsing people and their associated photos.
- **Bulk Management**: Move multiple photos between groups or remove them from a group entirely.
- **Merge & Rename**: Easily consolidate misidentified groups or assign names to "Unknown" persons.
- **Photo Zoom**: Full-screen high-resolution photo viewer.
- **Native Folder Picker**: Browse and select local directories directly from your browser.
- **Persistent Storage**: Uses PostgreSQL to store embeddings and group assignments for fast subsequent loads.

## Installation

### Prerequisites

- **Python 3.10+**
- **Docker Desktop** (for running the PostgreSQL database)

### Setup Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/derricklor/facephoto.git
   cd FacePhoto
   ```

2. **Create a Virtual Environment**
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## How to Run

1. **Start the Database**
   Open a terminal in the project root and start the PostgreSQL container:
   ```bash
   docker-compose up -d
   ```

2. **Run the Application**
   ```bash
   python run.py
   ```

3. **Access the Web UI**
   Open your browser and navigate to:
   [http://localhost:8000](http://localhost:8000)

## Usage

1. **Select a Directory**: Click the **Browse...** button to select a folder on your computer containing photos.
2. **Scan**: Click **Scan Directory**. The backend will process the photos in the background (progress depends on your CPU/GPU).
3. **Organize**:
   - Select a person from the sidebar to view their photos.
   - Use the **Rename** button to assign a name.
   - Use the **Merge** button to combine two different groups of the same person.
   - Use the checkboxes on photos to perform **Bulk Moves** or **Removals**.

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL (via SQLAlchemy)
- **AI/ML**: DeepFace (VGG-Face model), Scikit-Learn (DBSCAN)
- **Frontend**: HTML5, TailwindCSS, JavaScript (Vanilla)
- **Containerization**: Docker Compose
