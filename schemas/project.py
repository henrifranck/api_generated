from typing import Any, Optional, List

from pydantic import BaseModel, EmailStr


class AttributesModel(BaseModel):
    """Represents a column in a database table using Pydantic."""
    name: str
    type: str
    length: Optional[int] = None
    is_primary: bool = False
    is_indexed: bool = False
    is_auto_increment: bool = False
    is_required: bool = True
    is_unique: bool = False
    is_foreign: bool = False
    foreign_key_class: Optional[str] = None
    foreign_key: Optional[str] = None
    relation_name: Optional[str] = None

    @property
    def sqlalchemy_type(self) -> str:
        """Convert string-based DB type into a SQLAlchemy type."""
        t = self.type.upper()

        if "VARCHAR" in t:
            return f"String"
        elif t == "TEXT":
            return "Text"
        elif t == "INT" or t == "INTEGER":
            return "Integer"
        elif t == "BOOLEAN":
            return "Boolean"
        elif t == "DATETIME":
            return "DateTime"
        elif t == "TIMESTAMP":
            return "Time"
        elif t.startswith("DECIMAL") or t.startswith("NUMERIC"):
            return "Float"
        elif t == "Json":
            return "JSON"
        # Add other mappings as needed
        return t  # fallback


class ClassModel(BaseModel):
    """Represents a database table model using Pydantic."""

    name: str
    attributes: List[AttributesModel]

    @property
    def column_type_list(self) -> str:
        """Get unique SQLAlchemy column types used in the model."""
        types = set()
        for attr in self.attributes:
            types.add(attr.sqlalchemy_type)
        return ", ".join(types)


class OtherConfigSchema(BaseModel):
    use_docker: bool = True
    use_authentication: bool = True
    use_socket: bool = False


class ConfigSchema(BaseModel):
    docker_image_backend: str = "backend"
    host_port: str = "8081"
    container_port: str = "8081"

    backend_cors_origins: List[str] = []
    project_name: str = ""
    secret_key: str = ""
    first_superuser: Any = None
    first_name_superuser: str = ""
    last_name_superuser: str = ""
    first_superuser_password: Any = None

    mysql_host: str = "localhost"
    mysql_port: Any = 3306
    mysql_user: str
    mysql_password: str
    mysql_database: str

    @classmethod
    def from_body(cls, body, config):
        # Helper function to get a value from config or use a default
        def get_or_default(key, default):
            if config.get(key) == "" or config.get(key) == []:
                return default
            return config.get(key, default)

        # Dynamically generate default values based on body.name
        default_project_name = f"{body.name.title()}"
        default_secret_key = "tzrctxhgdc876guyguv6v"

        return cls(
            docker_image_backend=get_or_default("docker_image_backend", "backend"),
            container_port=get_or_default("container_port", "8081"),
            host_port=get_or_default("host_port", "8081"),
            backend_cors_origins=get_or_default("backend_cors_origins", [
                "http://localhost",
                "http://localhost:4200",
            ]),
            project_name=get_or_default("project_name", default_project_name),
            secret_key=get_or_default("secret_key", default_secret_key),

            first_superuser=get_or_default("first_superuser", ""),
            first_name_superuser=get_or_default("first_name_superuser", "string"),
            last_name_superuser=get_or_default("last_name_superuser", "string"),
            first_superuser_password=get_or_default("first_superuser_password", ""),

            mysql_host=get_or_default("mysql_host", "localhost"),
            mysql_port=get_or_default("mysql_port", 3306),
            mysql_user=get_or_default("mysql_user", ""),
            mysql_password=get_or_default("mysql_password", ""),
            mysql_database=get_or_default("mysql_database", ""),
        )


class ProjectBase(BaseModel):
    name: str
    config: ConfigSchema = None
    other_config: OtherConfigSchema = None


class ProjectCreate(BaseModel):
    name: str
    config: ConfigSchema = None
    other_config: OtherConfigSchema = None


class ProjectUpdate(BaseModel):
    class_model: List[ClassModel] = None
    migration_message: str = ""
    nodes: Any = {}


class ProjectResponse(ProjectBase):
    class_model: Any = None
    nodes: Any = {}
    id: int

    class Config:
        from_attributes = True


class Body(BaseModel):
    name: str
