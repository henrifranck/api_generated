from datetime import date, datetime, time
import uuid
from typing import Any, Dict, List
import random
import string

from schemas import AttributesModel


def generate_random_text(length):
    # Generate a random string of letters and digits
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))


def generate_random_integer(max_value):
    # Generate a random integer between 0 and max_value (exclusive)
    return random.randint(0, max_value)


def generate_random_float():
    a = 1.5
    b = 5.5
    # Generate a random float between a and b
    return random.uniform(a, b)


def generate_random_boolean():
    return random.choice([True, False])


def generate_random_json():
    # Generate a random JSON object
    return {
        "id": random.randint(1, 100),  # Random integer
        "is_active": random.choice([True, False]),  # Random boolean
        "score": round(random.uniform(0, 100), 2),  # Random float
        "metadata": {  # Nested JSON object
            "created_at": f"2023-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",  # Random date
            "updated_at": f"2023-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",  # Random date
        }
    }


def generate_column(data: List[AttributesModel]) -> Dict[str, Any]:
    """Generate realistic test data based on model attributes."""
    result = {}
    for attr in data:
        if attr.name == "id":
            continue
        elif attr.name == "email":
            result[attr.name] = f"{generate_data('Email', 5)}@{generate_data('Email', 5).lower()}.com"
        elif attr.name == "hashed_password":
            result['password'] = "securepassword123"
        elif attr.type.lower() == "str":
            result[attr.name] = f"test_{attr.name}"
        elif attr.type.lower() == "int":
            result[attr.name] = 123
        elif attr.type.lower() == "bool":
            result[attr.name] = True
        elif attr.type.lower() == "float":
            result[attr.name] = 1.23
        else:
            value = generate_data(attr.type, attr.length)
            if isinstance(value, str):
                result[attr.name] = repr(value)  # adds quotes & escapes
            if isinstance(value, (bool, int, float)):
                result[attr.name] = repr(value)
            if isinstance(value, (datetime, date, time)):
                result[attr.name] = str(value.isoformat())
            if isinstance(value, uuid.UUID):
                result[attr.name] = f"'{str(value)}'"

    return result


def generate_data(type_: Any, length: int = 5):
    type_ = type_.upper()
    limit = 10 if length and length >= 10 else length
    if type_ == "STRING(255)":
        return generate_random_text(generate_random_integer(limit))
    elif type_ == "INTEGER" or type_ == "INT":
        return generate_random_integer(20)
    elif type_ == "TEXT":
        return generate_random_text(generate_random_integer(100))
    elif type_ == "BOOLEAN":
        return generate_random_boolean()
    elif type_ == "FLOAT":
        return generate_random_float()
    elif type_ == "DATETIME":
        return datetime.now()
    elif type_ == "DATE":
        return date.today()
    elif type_ == "TIME" or type_ == "TIMESTAMP":
        return time(
            hour=generate_random_integer(23),
            minute=generate_random_integer(59),
            second=generate_random_integer(59)
        )
    elif type_ == "JSON":
        return generate_random_json()
    elif type_ == "UUID":
        return uuid.uuid4()
    else:
        return generate_random_text(5)


def get_column_type(column_type: str) -> str:
    """Map SQLAlchemy column type strings to Pydantic types."""
    column_type = get_comumn_type_msql(column_type).lower()  # Normalize the type string

    if column_type == "integer":
        return "int"
    elif column_type == "string(255)" or column_type == "text":
        return "str"
    elif column_type == "boolean":
        return "bool"
    elif column_type == "float":
        return "float"
    elif column_type == "datetime":
        return "datetime"
    elif column_type == "timestamp":
        return 'time'
    elif column_type == "date":
        return "date"
    elif column_type == "uuid":
        return "UUID"
    elif column_type == "json":
        return "dict"
    else:
        return "Any"


def get_comumn_type_msql(column_type: str) -> str:
    """Map MYSQL column type strings to SQLAlchemy types."""
    column_type = column_type.upper()  # Normalize the type string
    if column_type == "INT":
        return "Integer"
    elif column_type == "VARCHAR(255)":
        return "String(255)"
    elif column_type == "TEXT":
        return "Text"
    elif column_type == "DECIMAL(10,2)":
        return "Float"
    elif column_type == "DATETIME":
        return "DateTime"
    elif column_type == "DATE":
        return "Date"
    elif column_type == "BOOLEAN":
        return "Boolean"
    elif column_type == "TIMESTAMP":
        return "Time"
    elif column_type == "JSON":
        return "JSON"
    else:
        return "Any"


def generate_comumn_name(column_name, optional: bool = False):
    if column_name == "hashed_password":
        return {"name": "password", "optional": True}
    return {"name": column_name, "optional": optional}


def generate_relation_name(default_relations: str, relation_name: str) -> str:
    if relation_name and len(relation_name) > 0:
        return relation_name
    return default_relations
