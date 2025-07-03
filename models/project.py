from sqlalchemy import Column, Integer, String, JSON
from core.database import Base


class Project(Base):
    __tablename__ = "project"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    path = Column(String(100), nullable=False)
    config = Column(JSON)
    other_config = Column(JSON)
    class_model = Column(JSON)
    nodes = Column(JSON)
