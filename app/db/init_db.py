from app.db.database import engine, Base
import app.models  # Ensure models are imported for metadata registration

def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")

if __name__ == "__main__":
    init_db()
