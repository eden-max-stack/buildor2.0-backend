from app.infrastructure.database import SessionLocal
from .models import User

class UserRepository:

    def create(self, user_data):
        db = SessionLocal()
        user = User(**user_data.dict())
        db.add(user)
        db.commit()
        db.refresh(user)
        db.close()
        return user

    def get_all(self):
        db = SessionLocal()
        users = db.query(User).all()
        db.close()
        return users
