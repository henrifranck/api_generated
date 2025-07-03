import ast
import json
from datetime import datetime, timedelta, date
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
import re
import regex
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import and_, asc, delete, desc, extract, func, inspect, or_, case
from sqlalchemy.orm import (
    Session,
    joinedload,
    load_only,
)
from app.db.base_class import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).

        **Parameters**

        * `model`: A SQLAlchemy model class
        * `schema`: A Pydantic model (schema) class
        """
        self.model = model

    def get(
            self,
            db: Session,
            id: Any,
            where: Any = "",
            relations=None,
            include_deleted=False,
    ) -> Optional[ModelType]:
        query = db.query(self.model).filter(self.model.id == id)

        if where is not None and where != "":
            where = ast.literal_eval(where)
            conditions = self.get_full_condition(
                where=where,
                include_deleted=include_deleted,
            )
            if conditions is not None:
                query = query.filter(conditions)

        if relations is not None and len(relations) > 0:
            query = query.options(*(self.get_all_relations(relations)))

        return query.first()

    def get_all_relations(self, relations: List):
        return [self.get_joined_load(x) for x in relations]

    def get_joined_load(self, relations):
        def process_relation(relation):
            parts = relation.split(".")
            previous_model = self.model
            result = None

            for i in range(len(parts)):
                part = parts[i]

                if "{" in part and "}" in part:
                    relationship, columns = part.split("{")
                    columns = columns.rstrip("}").split(",")
                else:
                    relationship = part
                    columns = []

                attr = getattr(previous_model, relationship)

                if result:
                    result = result.joinedload(attr)
                else:
                    result = joinedload(attr)

                # Use current model BEFORE updating previous_model
                current_model = attr.property.mapper.class_

                if columns:
                    result = result.load_only(*[getattr(current_model, col) for col in columns])
                else:
                    result = result.load_only(getattr(current_model, "id"))

                previous_model = current_model

            return result

        options = []
        for relation in relations:
            options.append(process_relation(relation))

        return options

    def get_key_parts(self, key):
        subpart_start_idx = key.find(".[")
        last_index_of_parts1 = len(key)
        if subpart_start_idx >= 0:
            last_index_of_parts1 = subpart_start_idx
        result = key[:last_index_of_parts1].split(".")
        if subpart_start_idx >= 0:
            subpart_keys = regex.sub(
                r"(?<=\[[^\]]*),(?=[^\[]*\])",
                ";",
                key[subpart_start_idx + 2: len(key) - 1],
            ).split(",")
            all_sub_parts = []

            for i in range(0, len(subpart_keys)):
                subpart = self.get_key_parts(regex.sub(";", ",", subpart_keys[i]))
                all_sub_parts.append(subpart)

            if len(all_sub_parts) > 0:
                result.append(all_sub_parts)

        return result

    def get_cond_reccur(self, attrs, condition_operator: Any = and_):
        attrs.reverse()
        cond = None
        for i in range(0, len(attrs)):
            if isinstance(attrs[i], list):
                conditions = []
                for sub in attrs[i]:
                    conditions.append(self.get_cond_reccur(sub))
                cond = condition_operator(*conditions)
            else:
                attr, all = attrs[i]
                if i == 0:
                    cond = attr
                else:
                    try:
                        cond = attr.has(cond)
                    except:
                        cond = attr.any(cond)
                        if all:
                            cond = ~cond
        return cond

    def get_condition_deep_multiple(self, condition):
        key = condition.get("key", None)
        value = condition.get("value", None)
        operator = condition.get("operator", None)
        # key, value, operator must be an array and with same length
        cond_arr_sql = []
        if isinstance(key, list):
            for i in range(len(key)):
                current_cond = {
                    "key": key[i],
                    "operator": operator[i],
                    "value": value[i] if value else None,
                }
                cond_sql = self.sub_get_condition_deep_multiple(
                     condition=current_cond
                )
                cond_arr_sql.append(cond_sql)
            return or_(*cond_arr_sql)
        else:
            return self.sub_get_condition_deep_multiple(
                condition=condition
            )

    def sub_get_condition_deep_multiple(self, condition):
        keys = self.get_key_parts(condition["key"])
        operators = condition["operator"].split(",")
        values = [condition.get("value", None)]
        match = condition.get("match", "and")
        if len(operators) > 1 and values[0]:
            if "[[" in values[0]:
                values = json.loads(values[0])
            else:
                values = str(values[0]).split(",")
        condition_operator = or_ if match == "or" else and_
        current_idx = {"value": 0}
        attrs = self.get_attrs(self.model, current_idx, keys, operators, values)
        cond = self.get_cond_reccur(attrs=attrs, condition_operator=condition_operator)
        return cond

    def getStringDateTimeFormat(self, date_string):
        if len(date_string.split(" ")) >= 2:
            return date_string
        else:
            parsed_date = datetime.strptime(date_string, "%Y-%m-%d")
            formatted_string = parsed_date.strftime("%Y-%m-%d %H:%M")
        return formatted_string

    def get_attrs(self, parent_model, current_idx, keys, operators, values):
        previous_model = parent_model
        attrs = []
        for i in range(0, len(keys)):
            if i < len(keys) - 1:
                key_temp = keys[i]
                all = False
                if key_temp.startswith("~"):
                    key_temp = key_temp[1:]
                    all = True
                attr = getattr(previous_model, key_temp)
                previous_model = attr.property.mapper.class_
                attrs.append((attr, all))
            else:
                if isinstance(keys[i], str):
                    idx = current_idx["value"]
                    operator = operators[idx]
                    value = values[idx]
                    filter_condition = None
                    if keys[i].startswith("@"):
                        method_name = keys[i]
                        args = value["args"]
                        value = value["operator_value"]
                        method = getattr(previous_model, method_name.replace("@", ""))
                        attribute = method(*args)
                    else:
                        attribute = getattr(previous_model, keys[i])

                    if operator == "==":
                        filter_condition = attribute == value
                    elif operator == "!=":
                        filter_condition = attribute != value
                    elif operator == ">":
                        filter_condition = attribute > value
                    elif operator == "<":
                        filter_condition = attribute < value
                    elif operator == "like":
                        filter_condition = attribute.like("%" + value + "%")
                    elif operator == "month":
                        if value is None:
                            filter_condition = extract("month", attribute).is_(None)
                        else:
                            filter_condition = extract("month", attribute) == value
                    elif operator == "date":
                        date_value = datetime.strptime(value, "%Y-%m-%d").date()
                        filter_condition = func.date(attribute) == date_value
                    elif operator == "last_24h":
                        now = datetime.now()
                        twenty_four_hours_ago = now - timedelta(hours=24)

                        filter_condition = attribute.between(twenty_four_hours_ago, now)

                    elif operator == "between_date":
                        date_split = value.split(",")
                        date_1 = datetime.strptime(
                            self.getStringDateTimeFormat(date_split[0]),
                            "%Y-%m-%d %H:%M",
                        ).date()
                        date_2 = datetime.strptime(
                            self.getStringDateTimeFormat(date_split[1]),
                            "%Y-%m-%d %H:%M",
                        ).date()
                        filter_condition = attribute.between(date_1, date_2)
                    elif operator == "year":
                        if value is None:
                            filter_condition = extract("year", attribute).is_(None)
                        else:
                            filter_condition = extract("year", attribute) == value
                    elif operator == "lower_or_equal_year":
                        if value is None:
                            filter_condition = extract("year", attribute).is_(None)
                        else:
                            filter_condition = extract("year", attribute) <= value
                    elif operator == "greater_or_equal_year":
                        if value is None:
                            filter_condition = extract("year", attribute).is_(None)
                        else:
                            filter_condition = extract("year", attribute) >= value
                    elif operator == "week":
                        if value is None:
                            filter_condition = extract("week", attribute).is_(None)
                        else:
                            filter_condition = extract("week", attribute) == value
                    elif operator == "isNull":
                        filter_condition = attribute.is_(None)
                    elif operator == "isNotNull":
                        filter_condition = attribute.isnot(None)
                    elif operator == "isTrue":
                        filter_condition = attribute.is_(True)
                    elif operator == "isFalse":
                        filter_condition = attribute.is_(False)
                    elif operator == "notIn":
                        filter_condition = attribute.notin_(value)
                    elif operator == "in":
                        filter_condition = attribute.in_(value)
                    elif operator == "in_date_range":
                        filter_condition = self.get_date_filter_by_range(
                            date_column=attribute, date_list=value
                        )
                    elif operator.startswith("json."):
                        json_key = "$." + operator.split(".")[1]
                        col_value = func.json_extract(
                            func.json_unquote(attribute), json_key
                        )
                        if value == "isNull":
                            filter_condition = or_(
                                col_value.is_(None),
                                col_value.is_(False),
                                col_value.like("false"),
                            )
                        elif value == "isNotNull":
                            filter_condition = col_value.isnot(None)
                        else:
                            filter_condition = col_value.like(value)
                    elif operator == "ratio":
                        filter_condition = func.levenshtein_ratio(
                            func.upper(attribute), func.upper(value[0])
                        ) > (value[1] / 100)
                    idx += 1
                    current_idx["value"] = idx
                    attrs.append((filter_condition, False))
                else:
                    same_level = []
                    for key in keys[i]:
                        same_level.append(
                            self.get_attrs(
                                previous_model, current_idx, key, operators, values
                            )
                        )
                    attrs.append(same_level)

        return attrs

    def get_first_where_array(
            self, db: Session, *, where: Any = None, relations=None
    ) -> List[ModelType]:
        query = db.query(self.model)
        if where is not None:
            conditions = []
            for condition in where:
                filter_condition = self.get_condition_deep_multiple(
                   condition=condition
                )
                if filter_condition is not None:
                    conditions.append(filter_condition)
            query = query.filter(and_(*conditions))
            if relations is not None and len(relations) > 0:
                query = query.options(*(self.get_all_relations(relations)))

        result = query.first()

        return result

    def get_multi_where_array(
            self,
            db: Session,
            *,
            skip: int = 0,
            limit: int = 100,
            order_by: str = "id",
            where: Any = None,
            order: str = "DESC",
            base_columns=None,
            relations=None,
            include_deleted: bool = False,
            order_by_subquery=None,
            today_first: bool = False,
    ) -> List[ModelType]:
        query = db.query(self.model)
        conditions = self.get_full_condition(
            where=where,
            include_deleted=include_deleted,
        )
        if conditions is not None:
            query = query.filter(conditions)

        order_function = asc
        if order == "DESC":
            order_function = desc

        if order_by_subquery is not None:
            query = query.order_by(order_function(order_by_subquery))
        else:
            today = date.today()
            if len(order_by.split(".")) > 1:
                if today_first:
                    order_by_subquery = self.get_order_by_subquery(
                        db=db, order_by_key=order_by
                    )
                    query = query.order_by(
                        case([(func.date(order_by_subquery) == today, 0)], else_=1),
                        order_function(order_by_subquery),
                    )
                else:
                    order_by_subquery = self.get_order_by_subquery(
                        db=db, order_by_key=order_by
                    )
                    query = query.order_by(order_function(order_by_subquery))
            else:
                if today_first:
                    order_by_attribute = getattr(self.model, order_by)

                    query = query.order_by(
                        case([(func.date(order_by_attribute) == today, 0)], else_=1),
                        order_function(order_by_attribute),
                    )
                else:
                    order_by_attribute = getattr(self.model, order_by)
                    query = query.order_by(order_function(order_by_attribute))

        query = (
            query.order_by(
                desc(getattr(self.model, "id")),
            )
            .offset(skip)
            .limit(limit)
        )
        if base_columns is not None and len(base_columns) > 0:
            query = query.options(load_only(*base_columns))

        if relations is not None and len(relations) > 0:
            load_options = self.get_joined_load(relations)
            query = query.options(*load_options)

        result = query.all()
        return result

    def get_order_by_subquery(self, db: Session, *, order_by_key):
        key_segments = order_by_key.split(".")
        subquery_filter = True
        attribute = getattr(self.model, key_segments[0])
        joins = []
        last_attribut = self.model
        first_attribut = attribute.property.mapper.class_
        if len(key_segments) > 1:
            for segment in key_segments[1:]:
                last_attribut = attribute.property.mapper.class_

                if segment.startswith("@"):
                    pattern = r"@(\w+)(\(.*\))"
                    match = re.search(pattern, segment)
                    method_name = match.group(1)
                    argument = match.group(2)
                    attribute = eval("method" + argument)
                else:
                    attribute = getattr(attribute.property.mapper.class_, segment)

                if segment != key_segments[-1]:
                    joins.insert(0, attribute)

        model_mapper = inspect(first_attribut)

        for relationship in model_mapper.relationships:

            if relationship.mapper.class_ == self.model:
                foreign_key_column = list(relationship.local_columns)[0]
                subquery_filter = foreign_key_column == self.model.id
                break

        subquery_query = db.query(attribute).select_from(last_attribut)
        for relation in joins:
            subquery_query = subquery_query.join(relation)
        subquery = subquery_query.filter(subquery_filter).limit(1).as_scalar()
        return subquery

    def create(
            self,
            db: Session,
            *,
            obj_in: CreateSchemaType,
            user_id: int = None,
            commit: bool = True,
            refresh: bool = True,
    ) -> ModelType:
        # Convert to dict and ensure datetime objects are properly handled
        obj_in_data = obj_in.model_dump()

        # Create the database object
        db_obj = (
            self.model(**obj_in_data)
            if not user_id
            else self.model(**obj_in_data, last_user_to_interact=user_id)
        )

        db.add(db_obj)
        if commit:
            db.commit()
        if refresh:
            db.refresh(db_obj)
        return db_obj

    def create_multi(
            self,
            db: Session,
            *,
            objs_in: List[CreateSchemaType],
            user_id: int = None,
            commit: bool = True,
    ) -> List[ModelType]:
        objs_to_add = []
        for obj_in in objs_in:
            obj_in_data = jsonable_encoder(obj_in)
            db_obj = (
                self.model(**obj_in_data)
                if not user_id
                else self.model(**obj_in_data, last_user_to_interact=user_id)
            )  # type: ignore
            objs_to_add.append(db_obj)
        db.add_all(objs_to_add)
        if commit:
            db.commit()
        return objs_to_add

    def add_model(
            self,
            db: Session,
            *,
            db_obj: ModelType,
            user_id: Optional[int] = None,
            commit: bool = True,
    ) -> ModelType:
        if user_id:
            db_obj.last_user_to_interact = user_id
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
        user_id: int = None,
        commit: bool = True,
    ) -> ModelType:
        obj_data = jsonable_encoder(db_obj)

        # 🔁 Pydantic v2 compliant way to extract data
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        update_data["updated_at"] = func.now()

        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])

        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        return db_obj


    def remove(self, db: Session, *, id: int, commit: bool = True) -> ModelType:
        obj = db.get(self.model, id)
        db.delete(obj)
        if commit:
            db.commit()
        return obj


    def remove_or_soft(
            self,
            db: Session,
            *,
            id: int,
            user_id: int = None,
            commit: bool = True,
            soft: bool = True,
    ) -> Any:
        if soft:
            self.soft_delete(db=db, id=id, commit=commit, user_id=user_id)
        else:
            self.remove(db=db, id=id, commit=commit)
        if commit:
            db.commit()

    def remove_or_soft_or_restore(
            self,
            db: Session,
            *,
            id: int,
            user_id: int = None,
            commit: bool = True,
            operation: str = "soft_delete",
    ) -> Any:
        if operation == "soft_delete":
            self.soft_delete(db=db, id=id, commit=commit, user_id=user_id)
        elif operation == "restore_deleted":
            self.restore_deleted(db=db, id=id, commit=commit, user_id=user_id)
        elif operation == "remove":
            self.remove(db=db, id=id, commit=commit)
        else:
            raise ValueError(f"Invalid operation {operation}")
        if commit:
            db.commit()

    def bulk_remove(
            self, db: Session, *, ids_to_delete: str, commit: bool = True, keys: str = "id"
    ) -> ModelType:
        ids_to_select = [int(x) for x in ast.literal_eval(ids_to_delete)]
        query = (
            db.query(getattr(self.model, keys))
            .filter(getattr(self.model, keys).in_(ids_to_select))
            .all()
        )
        ids_found = [result[0] for result in query]
        # to delete only the IDs that exist in the database
        query = delete(self.model).where(getattr(self.model, keys).in_(ids_found))
        db.execute(query)
        if commit:
            db.commit()

    def soft_delete(
            self, db: Session, *, id: int, commit: bool = True, user_id: int = None
    ) -> ModelType:
        db_obj = db.query(self.model).get(id)
        obj_data = jsonable_encoder(db_obj)
        update_data = {"deleted_at": func.now()}

        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        return db_obj

    def restore_deleted(
            self, db: Session, *, id: int, commit: bool = True, user_id: int = None
    ) -> ModelType:
        db_obj = db.query(self.model).get(id)
        obj_data = jsonable_encoder(db_obj)
        update_data = (
            {
                "deleted_at": None,
                "last_user_to_interact": user_id,
            }
            if user_id
            else {"deleted_at": None}
        )

        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        return db_obj

    def get_count_where_array(
            self,
            db: Session,
            where: Any = None,
            include_deleted=False,
    ) -> int:
        query = db.query(self.model.id)

        conditions = self.get_full_condition(
            where=where,
            include_deleted=include_deleted,
        )
        if conditions is not None:
            query = query.filter(conditions)

        # print("count ito ah",str(query.statement.compile(compile_kwargs={"literal_binds": True})))
        result = query.count()
        return result

    def get_full_condition(
            self, where: Any = None, include_deleted=False
    ) -> Any:
        if not include_deleted:
            if not where:
                where = []
            where.append(
                {
                    "key": "deleted_at",
                    "operator": "isNull",
                }
            )
        if where is not None:
            conditions = []
            for parent_condition in where:
                if isinstance(parent_condition, list):
                    # This is an OR condition - any of the conditions in the list should be true
                    temp_conditions = []
                    for condition in parent_condition:
                        filter_condition = self.get_condition_deep_multiple(
                            condition=condition
                        )
                        if filter_condition is not None:
                            temp_conditions.append(filter_condition)
                    if temp_conditions:
                        conditions.append(or_(*temp_conditions))
                else:
                    # This is a normal AND condition
                    filter_condition = self.get_condition_deep_multiple(
                        condition=parent_condition
                    )
                    if filter_condition is not None:
                        conditions.append(filter_condition)

            if conditions:
                return and_(*conditions)
        return None

    def remove_where_array(
            self, db: Session, where: Any = None, commit: bool = True
    ) -> int:
        query = db.query(self.model)
        if where is not None:
            conditions = []
            for condition in where:
                filter_condition = self.get_condition_deep_multiple(
                    db=db, condition=condition
                )
                if filter_condition is not None:
                    conditions.append(filter_condition)

            query = query.filter(and_(*conditions))
        query.delete()
        if commit:
            db.commit()

    def get_date_filter_by_range(self, date_column, date_list):
        filters = []
        for date_value in date_list:
            parts = date_value.split("-")
            if len(parts) == 1:
                year = int(parts[0])
                filters.append(extract("year", date_column) == year)
            elif len(parts) == 2:
                year = int(parts[0])
                month = int(parts[1])
                filters.append(
                    and_(
                        extract("year", date_column) == year,
                        extract("month", date_column) == month,
                    )
                )
        return or_(*filters)
