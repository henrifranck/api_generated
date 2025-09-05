from typing import Dict
from schemas import ClassModel


def get_auth_model(models):
    normalised = [m if isinstance(m, ClassModel) else ClassModel(**m) for m in models]
    all_models: Dict[str, ClassModel] = {m.name: m for m in normalised}

    # Trouver le modèle utilisateur pour le test de login
    user_model_name = None
    user_model = None

    for model_name, model in all_models.items():
        has_email = any(attr.name.lower() == "email" for attr in model.attributes)
        has_password = any(attr.name.lower() in ["password", "hashed_password"] for attr in model.attributes)

        if has_email and has_password:
            user_model_name = model_name
            user_model = model
            break
    return user_model_name, user_model
