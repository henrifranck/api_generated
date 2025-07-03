from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

import models
import schemas


def create_project(db: Session, project: schemas.ProjectCreate):
    config = jsonable_encoder(schemas.ConfigSchema.from_body(project, jsonable_encoder(project.config)))
    other_config = jsonable_encoder(project.other_config)
    db_project = models.Project(name=project.name, config=config, path="project", nodes={}, other_config=other_config)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def delete_project(db: Session, project_id: int):
    # Fetch the project from the database
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    # Delete the project
    db.delete(db_project)
    db.commit()


def update_project(db: Session, project_id: int, project_data: schemas.ProjectUpdate):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    nodes = jsonable_encoder(project_data.nodes)
    if db_project:
        db_project.class_model = jsonable_encoder(project_data.class_model)
        db_project.nodes = nodes
        db.commit()
        db.refresh(db_project)
    return db_project


def update_config(db: Session, project_id: int, project_data: schemas.ProjectCreate):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()

    config = jsonable_encoder(
        schemas.ConfigSchema.from_body(
            project_data, jsonable_encoder(project_data.config)
        ),
    )

    other_config = jsonable_encoder(project_data.other_config)
    if db_project:
        db_project.name = jsonable_encoder(project_data.name)
        db_project.config = jsonable_encoder(config)
        db_project.other_config = other_config
        db.commit()
        db.refresh(db_project)
    return db_project


def get_project(db: Session, skip: int = 0, limit: int = 10):
    return db.query(models.Project).offset(skip).limit(limit).all()


def get_project_by_id(db: Session, id: int) -> models.Project | None:
    return db.query(models.Project).filter(models.Project.id == id).first()
