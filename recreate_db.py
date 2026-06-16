from app.database import engine, Base
# Import models to ensure they are registered on Base
from app.models import Photo, Person, FaceEmbedding

def reset_db():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Database schema reset successfully!")

if __name__ == "__main__":
    reset_db()
