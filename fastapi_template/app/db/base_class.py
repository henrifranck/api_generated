from typing import Any

from sqlalchemy.orm import as_declarative, declared_attr


from app.utils import camel_to_snake


@as_declarative()
class Base:
    id: Any
    __name__: str

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return camel_to_snake(cls)
