import os
from typing import List

import schemas
from schemas import ClassModel
from sqlalchemy.orm import DeclarativeMeta

from model_type import snake_to_camel, camel_to_snake

OUTPUT_DIR = "/app/api/api_v1/endpoints"


def generate_router_file(table_name, other_config):
    """Generate a FastAPI router file for CRUD operations."""
    schema_name = snake_to_camel(table_name)
    router_name = table_name
    crud_name = table_name
    response_model_name = f"Response{schema_name}"

    # Common imports
    imports = [
        "from typing import Any",
        "from fastapi import APIRouter, Depends, HTTPException",
        "from fastapi.encoders import jsonable_encoder",
        "from sqlalchemy.orm import Session",
        "from app.api import deps",
        "from app import crud, models, schemas",
        "import ast",
        "",
        f"router = APIRouter()",
    ]

    # Conditional imports and dependencies
    auth_dependency = "current_user: models.User = Depends(deps.get_current_active_user)," if other_config.use_authentication else ""
    auth_import = "from app.api import deps" if other_config.use_authentication else ""

    data = f"{router_name}_id"
    value = f"{{{data}}}"

    # Route definitions
    routes = [
        f"@router.get('/', response_model=schemas.{response_model_name})",
        f"def read_{router_name}s(",
        "        *,",
        "        offset: int = 0,",
        "        limit: int = 20,",
        "        relation: str = \"[]\",",
        "        where: str = \"[]\",",
        "        db: Session = Depends(deps.get_db),",
        f"        {auth_dependency}",
        ") -> Any:",
        f"    \"\"\"",
        f"    Retrieve {router_name}s.",
        f"    \"\"\"",
        ""
        "    relations = []",
        "    if relation is not None and relation != \"\" and relation != []:",
        "       relations += ast.literal_eval(relation)",
        "",
        "    wheres = []",
        "    if where is not None and where != \"\" and where != []:",
        "       wheres += ast.literal_eval(where)",
        "",
        f"    {router_name}s = crud.{crud_name}.get_multi_where_array(",
        f"      db=db, relations=relations, skip=offset, limit=limit, where=wheres)",
        f"    count = crud.{crud_name}.get_count_where_array(db=db, where=wheres)",
        f"    response = schemas.{response_model_name}(**{{'count': count, 'data': jsonable_encoder({router_name}s)}})",
        "    return response",
        "",
        "",
        f"@router.post('/', response_model=schemas.{schema_name})",
        f"def create_{router_name}(",
        "        *,",
        "        db: Session = Depends(deps.get_db),",
        f"        {router_name}_in: schemas.{schema_name}Create,",
        f"        {auth_dependency}",
        ") -> Any:",
        f"    \"\"\"",
        f"    Create new {router_name}.",
        f"    \"\"\"",
        f"    {router_name} = crud.{crud_name}.create(db=db, obj_in={router_name}_in)",
        f"    return {router_name}",
        "",
        "",
        f"@router.put('/{value}', response_model=schemas.{schema_name})",
        f"def update_{router_name}(",
        "        *,",
        "        db: Session = Depends(deps.get_db),",
        f"        {router_name}_id: int,",
        f"        {router_name}_in: schemas.{schema_name}Update,",
        f"        {auth_dependency}",
        ") -> Any:",
        f"    \"\"\"",
        f"    Update an {router_name}.",
        f"    \"\"\"",
        f"    {router_name} = crud.{crud_name}.get(db=db, id={router_name}_id)",
        f"    if not {router_name}:",
        f"        raise HTTPException(status_code=404, detail='{schema_name} not found')",
        f"    {router_name} = crud.{crud_name}.update(db=db, db_obj={router_name}, obj_in={router_name}_in)",
        f"    return {router_name}",
        "",
        "",
        f"@router.get('/{value}', response_model=schemas.{schema_name})",
        f"def read_{router_name}(",
        "        *,",
        "        relation: str = \"[]\",",
        "        where: str = \"[]\",",
        "        db: Session = Depends(deps.get_db),",
        f"        {router_name}_id: int,",
        f"        {auth_dependency}",
        ") -> Any:",
        f"    \"\"\"",
        f"    Get {router_name} by ID.",
        f"    \"\"\"",
        ""
        "    relations = []",
        "    if relation is not None and relation != \"\" and relation != [] and relation != \"[]\":",
        "       relations += ast.literal_eval(relation)",
        "",
        "    wheres = []",
        "    if where is not None and where != \"\" and where != []:",
        "       wheres += ast.literal_eval(where)",
        "",
        f"    {router_name} = crud.{crud_name}.get(db=db, id={router_name}_id, relations=relations, where=wheres)",
        f"    if not {router_name}:",
        f"        raise HTTPException(status_code=404, detail='{schema_name} not found')",
        f"    return {router_name}",
        "",
        "",
        f"@router.delete('/{value}', response_model=schemas.Msg)",
        f"def delete_{router_name}(",
        "        *,",
        "        db: Session = Depends(deps.get_db),",
        f"        {router_name}_id: int,",
        f"        {auth_dependency}",
        ") -> Any:",
        f"    \"\"\"",
        f"    Delete an {router_name}.",
        f"    \"\"\"",
        f"    {router_name} = crud.{crud_name}.get(db=db, id={router_name}_id)",
        f"    if not {router_name}:",
        f"        raise HTTPException(status_code=404, detail='{schema_name} not found')",
        f"    {router_name} = crud.{crud_name}.remove(db=db, id={router_name}_id)",
        f"    return schemas.Msg(msg='{schema_name} deleted successfully')",
        "",
    ]

    # Combine imports and routes
    router_lines = imports + ([auth_import] if auth_import else []) + routes

    # Filter out empty strings and join with newlines
    return "\n".join(line for line in router_lines if line.strip() != "" or line == "")


def write_endpoints(models: List[ClassModel], output_dir, other_config: schemas.OtherConfigSchema):
    """Write the generated schemas to files."""
    endpoints_directory = output_dir + OUTPUT_DIR
    os.makedirs(endpoints_directory, exist_ok=True)
    for model in models:
        model = ClassModel(**model)
        table_name = camel_to_snake(model.name)
        endpoints = generate_router_file(table_name, other_config)
        file_name = f"{table_name}s.py"
        file_path = os.path.join(endpoints_directory, file_name)

        if not os.path.exists(file_path):
            with open(file_path, "w") as f:
                f.write(endpoints)
            print(f"Generated endpoints for: {table_name}")
        else:
            print(f"endpoints for {table_name} already exist")

    apis_directory = output_dir + "/app/api/api_v1"  # Path to endpoints directory
    output_file_path = os.path.join(apis_directory, "api.py")  # Output file path

    print(endpoints_directory)
    generate_endpoints_file(endpoints_directory, output_file_path)


def generate_endpoints_file(endpoints_dir, output_file):
    """
    Generate an `endpoints.py` file that includes all FastAPI routers from the endpoints directory.

    Args:
        endpoints_dir (str): Path to the directory containing the endpoint files.
        output_file (str): Path to the output `endpoints.py` file.
    """
    # List all Python files in the endpoints directory
    endpoint_files = [
        f[:-3] for f in os.listdir(endpoints_dir)
        if f.endswith(".py") and f != "__init__.py"
    ]

    # Generate import statements
    import_lines = [
        f"from app.api.api_v1.endpoints import {endpoint}"
        for endpoint in endpoint_files
    ]

    # Generate include_router lines
    include_router_lines = [
        f'api_router.include_router({endpoint}.router, prefix="/{endpoint}", tags=["{endpoint}"])'
        for endpoint in endpoint_files
    ]

    # Combine everything into the final script
    lines = [
        "from fastapi import APIRouter",
        "",
        *import_lines,
        "",
        "api_router = APIRouter()",
        *include_router_lines,
        "",
    ]

    # Write to the output file
    with open(output_file, "w") as f:
        f.write("\n".join(lines))

    print(f"Generated {output_file} successfully!")
