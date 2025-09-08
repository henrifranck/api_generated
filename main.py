import os
import shutil
from typing import List

import uvicorn as uvicorn
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware  # Import CORSMiddleware

from core.delete_models import delete_files
from core.generate_apis_login import write_login
from core.generate_apis_login_deps import write_deps
from core.generate_apis_unit_test import write_test_apis
from core.generate_base_file import write_base_files
from core.generate_config import write_auth_config
from core.generate_crud import write_crud
from core.generate_crud_unit_test import write_test_crud
from core.generate_endpoints import write_endpoints
from core.generate_enum import write_enums
from core.generate_env import generate_env
from core.generate_init_file import write_init_files
from core.generate_login import generate_auth_router_module
from core.generate_models import write_models
from core.generate_schema import write_schemas
from core.reformat_file import reformate_code
from model_type import create_or_update_mysql_user, write_config, drop_mysql_database_user
from schemas import ClassModel, ProjectUpdate
from sqlalchemy.orm import Session
from fastapi import FastAPI, Depends, HTTPException

import models, schemas, crud
from core.database import engine, get_db, Base
from utils.alembic_command import run_migrations
from pathlib import Path

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (you can specify specific origins instead of "*")
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)


def set_full_permissions(directory: str):
    """Set full permissions (rwx) for all users (owner, group, others)."""
    try:
        os.chmod(directory, 0o777)  # 0o777 = rwx for owner, group, and others
        print(f"Set full permissions for directory: {directory}")
    except Exception as e:
        print(f"Failed to set permissions for directory {directory}: {e}")


def create_all_file(project, destination_dir, migration_message, class_model: List[ClassModel]):
    print("Setting permissions...")
    set_full_permissions(destination_dir)

    print("Generating project files...")

    other_config = schemas.OtherConfigSchema(**project.other_config)

    enums = None
    if project.nodes["enums"] and len(project.nodes["enums"]) > 0:
        enums = project.nodes["enums"]
        write_enums(project.nodes["enums"], destination_dir)

    write_models(class_model, destination_dir)
    write_schemas(class_model, destination_dir)

    # generate only for the new class
    write_crud(class_model, destination_dir, other_config)
    write_deps(class_model, destination_dir, other_config)
    write_login(class_model, destination_dir, other_config)
    write_endpoints(class_model, destination_dir, other_config)
    write_init_files(destination_dir)
    write_base_files(class_model, destination_dir)

    # each updated generate test
    write_test_crud(project.class_model, destination_dir, all_enums=enums)
    write_test_apis(project.class_model, destination_dir, other_config, all_enums=enums)

    if not other_config.use_authentication:
        reformate_code(destination_dir)
    write_auth_config(destination_dir, other_config)

    # Optionally force file system sync
    try:
        os.sync()
    except AttributeError:
        pass  # os.sync doesn't exist on some platforms

    print(f"All files generated. Proceeding with Alembic migration... t {migration_message}s ...")
    run_migrations(message=migration_message)


def generate_project(project, migration_message, class_model: List[ClassModel]):
    # Get current file's directory (inside 'test')
    current_dir = Path(__file__).resolve().parent
    root_dir = current_dir.parent
    template_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "fastapi_template"))
    destination_dir = os.path.normpath(os.path.join(os.path.normpath(root_dir), project.name))

    write_config(project)
    # try:
    print("mandalo tsara", template_dir, destination_dir)
    if os.path.exists(destination_dir):
        create_all_file(project, destination_dir, migration_message, class_model)
    else:
        # Copy the template directory to the destination
        shutil.copytree(template_dir, destination_dir)
        # Generate files in the new directory
        generate_env(
            project.config,
            output_file=os.path.normpath(os.path.join(destination_dir, ".env")),
            use_docker=project.other_config["use_docker"]
        )
        create_all_file(project, destination_dir, migration_message, project.class_model)

    # except FileExistsError as e:
    #     print("Error: Directory already exists.", e)
    # except Exception as e:
    #     print(f"An error occurred: {e}")


@app.post("/project/config", response_model=schemas.ProjectResponse)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    project = crud.create_project(db=db, project=project)

    create_or_update_mysql_user(
        project.config['mysql_user'],
        project.config['mysql_password'],
        project.config['mysql_database']
    )
    write_config(project)
    return project


@app.put("/project/config", response_model=schemas.ProjectResponse)
def update_project(
        project_id: int,
        project_in: schemas.ProjectCreate,
        db: Session = Depends(get_db),
):
    print(project_in)
    project = crud.update_config(db=db, project_data=project_in, project_id=project_id)

    destination_dir = os.path.join("project", project.name)
    create_or_update_mysql_user(
        project_in.config.mysql_user,
        project_in.config.mysql_password,
        project_in.config.mysql_database
    )

    write_config(project)
    if os.path.exists(destination_dir + "/.env"):
        generate_env(
            project.config,
            output_file=destination_dir + "/.env",
            use_docker=project.other_config["use_docker"])
    return project


@app.put("/project/diagram", response_model=schemas.ProjectResponse)
def update_project(
        project_id: int,
        project_in: schemas.ProjectUpdate,
        db: Session = Depends(get_db),
):
    project = crud.update_project(db=db, project_data=project_in, project_id=project_id)
    return project


@app.get("/project/", response_model=list[schemas.ProjectResponse])
def read_project(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_project(db, skip, limit)


@app.get("/project/by_id", response_model=schemas.ProjectResponse)
def read_project(project_id: int, db: Session = Depends(get_db)):
    project = crud.get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    return project


@app.delete("/project", response_model=str)
def read_project(project_id: int, db: Session = Depends(get_db)):
    project = crud.get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    folder_path = "project" + "/" + project.name
    if os.path.exists(folder_path):
        # Remove the folder and its contents recursively
        shutil.rmtree(folder_path)
        print(f"Folder '{folder_path}' and its contents have been removed.")
    drop_mysql_database_user(project.config['mysql_user'], project.config['mysql_database'])
    crud.delete_project(db, project_id)
    return "deleted"


@app.put("/project")
async def update_project(
        project_id: int,
        project_in: ProjectUpdate,
        db: Session = Depends(get_db),
        updated_class: List[str] = None
):
    project = crud.get_project_by_id(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')

    updated_class = [updated_.lower() for updated_ in updated_class] if updated_class else []
    # project = crud.update_project(db=db, project_data=project_in, project_id=project_id)

    print("updated class", updated_class)
    old_class = [old['name'] for old in project.class_model]
    new_class_model = [new_.name for new_ in project_in.class_model]

    new_class = [class_.name for class_ in project_in.class_model if class_.name not in old_class]
    deleted_class = [class_ for class_ in old_class if class_ not in new_class_model]

    class_model = [project_ for project_ in project.class_model if project_['name'].lower() in updated_class
                   and project_['name'].lower() not in new_class]

    print(jsonable_encoder(class_model))
    generate_project(project, project_in.migration_message, class_model)
    if len(deleted_class) > 0:
        destination_dir = os.path.join("project", project.name)
        for class_name in deleted_class:
            delete_files(class_name, destination_dir)
        write_init_files(destination_dir)
        write_base_files(project.class_model, destination_dir)
    return project


if __name__ == "__main__":
    config = {
        "app": "main:app",
        "host": "0.0.0.0",
        "port": 8000,
        "reload": True,
    }
    uvicorn.run(**config)
