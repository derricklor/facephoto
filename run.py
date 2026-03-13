import uvicorn
import os

if __name__ == "__main__":
    # Ensure the static directory exists
    if not os.path.exists("static"):
        os.makedirs("static")
        
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
