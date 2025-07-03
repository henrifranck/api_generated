import os
import re
from typing import List

import schemas
from model_type import preserve_custom_sections, \
    snake_to_camel, camel_to_snake  # Import your model definitions
from schemas import ClassModel

OUTPUT_DIR = "/app/crud"


def generate_crud_imports(table_name: str, model_name: str) -> str:
    """Generate the necessary imports for the CRUD class."""
    schema_create = f"{snake_to_camel(table_name)}Create"
    schema_update = f"{snake_to_camel(table_name)}Update"

    imports = [
        "from typing import Optional, List, Dict, Any",
        "from sqlalchemy.orm import Session",
        "",
        f"from app.crud.base import CRUDBase",
        f"from app.models.{table_name} import {model_name}",
        f"from app.schemas.{table_name} import {schema_create}, {schema_update}",
        "",
    ]

    import_user = [
        "from app.core.security import get_password_hash, verify_password",
        "from fastapi.encoders import jsonable_encoder",
    ]
    if model_name == "User":
        imports += import_user
    return "\n".join(imports)


def generate_crud_class(table_name: str, model_name: str) -> str:
    """Generate the CRUD class definition."""
    crud_class_name = f"CRUD{snake_to_camel(table_name)}"
    schema_create = f"{snake_to_camel(table_name)}Create"
    schema_update = f"{snake_to_camel(table_name)}Update"

    class_definition = [
        f"\nclass {crud_class_name}(CRUDBase[{model_name}, {schema_create}, {schema_update}]):",
    ]
    return "\n".join(class_definition)


def generate_crud_functions(table_name: str, model_name: str, other_config: schemas.OtherConfigSchema) -> str:
    """Generate common CRUD functions."""
    functions = [
        f"    def get_by_id(self, db: Session, *, id: int) -> Optional[{model_name}]:",
        f"        return db.query({model_name}).filter({model_name}.id == id).first()",
        "",
        f"    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[{model_name}]:",
        f"        return db.query({model_name}).offset(skip).limit(limit).all()",
        "",
        f"    def get_by_field(self, db: Session, *, field: str, value: Any) -> Optional[{model_name}]:",
        f"        return db.query({model_name}).filter(getattr({model_name}, field) == value).first()",
        "",
        f"    def delete(self, db: Session, *, id: int) -> {model_name}:",
        f"        obj = db.query({model_name}).filter({model_name}.id == id).first()",
        f"        db.delete(obj)",
        f"        db.commit()",
        f"        return obj",
        "",
    ]

    if other_config.use_authentication and model_name.upper() == "USER":
        user_functions = [
            f"    def get_by_email(self, db: Session, *, email: str) -> Optional[{model_name}]:",
            f"        return db.query({model_name}).filter({model_name}.email == email).first()",
            "",
            f"    def is_superuser(self, user: User) -> {model_name}:",
            f"        return user.is_superuser",
            "",
            f"    def is_active(self, user: User) -> {model_name}:",
            f"        return user.is_active",
            "",
            f"    def authenticate(self, db: Session, *, email: str, password: str) -> {model_name}:",
            f"        user = self.get_by_email(db, email=email)",
            f"        if not user:",
            f"            return None",
            f"        if not verify_password(password, user.hashed_password):",
            f"            return None",
            f"        return user",
            "",
            f"    def create(self, db: Session, *, obj_in: UserCreate) -> User:",
            f"        obj_data = jsonable_encoder(obj_in)",
            f"        pass_value = obj_data.pop('password')",
            f"        db_obj = User(hashed_password=get_password_hash(pass_value), **obj_data)",
            f"        db.add(db_obj)",
            f"        db.commit()",
            f"        db.refresh(db_obj)",
            f"        return db_obj",
            f"",
            f"",
        ]

        functions += user_functions
    return "\n".join(functions)


def generate_crud_instance(table_name: str, model_name: str) -> str:
    """Generate the CRUD instance."""
    crud_class_name = f"CRUD{snake_to_camel(table_name)}"
    instance = [
        f"{table_name} = {crud_class_name}({model_name})",
        "",
    ]
    return "\n".join(instance)


def generate_crud(table_name: str, model_name: str, other_config: schemas.OtherConfigSchema) -> str:
    """Generate the full CRUD class for a given model."""
    crud_lines = [
        generate_crud_imports(table_name, model_name),
        generate_crud_class(table_name, model_name),
        generate_crud_functions(table_name, model_name, other_config),
        generate_crud_instance(table_name, model_name),
    ]
    return "\n".join(crud_lines)


def write_crud(models: List[ClassModel], output_dir, other_config: schemas.OtherConfigSchema):
    """Write the generated CRUD classes to files, preserving custom sections."""
    output_dir += OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)
    for model in models:
        model = ClassModel(**model)
        table_name = camel_to_snake(model.name)
        model_name = model.name
        crud_content = generate_crud(table_name, model_name, other_config)
        file_name = f"crud_{table_name}.py"
        file_path = os.path.join(output_dir, file_name)

        # Preserve custom sections in the file
        final_content = preserve_custom_sections(file_path, crud_content)

        with open(file_path, "w") as f:
            f.write(final_content)
        print(f"Generated CRUD for: {table_name}")
