from sqlalchemy import Column, Integer, String
from app.infrastructure.database import Base

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    difficulty = Column(String)
    description = Column(String)