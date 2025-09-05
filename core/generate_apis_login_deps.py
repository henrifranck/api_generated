# -*- coding: utf-8 -*-
"""test_api_generator.py – v2 (modified)

Generate FastAPI integration tests (CRUD via HTTP) for every SQLAlchemy
ClassModel. FK‑aware, supports optional JWT auth. Now generates dict-based test data for the main model.
"""
from __future__ import annotations

import logging
import os
from typing import List, Dict

import schemas
from core.generate_deps import generate_deps_module
from model_type import preserve_custom_sections
from schemas import ClassModel

# ---------------------------------------------------------------------------
# Configuration & logging
# ---------------------------------------------------------------------------
OUTPUT_DIR = "/app/api"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def write_deps(models: List[ClassModel], output_dir: str, other_cfg: schemas.OtherConfigSchema) -> None:
    out_dir = os.path.join(output_dir, OUTPUT_DIR.lstrip("/"))
    os.makedirs(out_dir, exist_ok=True)

    normalised = [m if isinstance(m, ClassModel) else ClassModel(**m) for m in models]
    all_models: Dict[str, ClassModel] = {m.name: m for m in normalised}

    # Trouver le modèle utilisateur pour le test de login
    user_model_name = None

    for model_name, model in all_models.items():
        has_email = any(attr.name.lower() == "email" for attr in model.attributes)
        has_password = any(attr.name.lower() in ["password", "hashed_password"] for attr in model.attributes)

        if has_email and has_password:
            user_model_name = model_name
            break

    if user_model_name and other_cfg.use_authentication:
        f_deps_name = f"deps.py"
        f_deps_path = os.path.join(out_dir, f_deps_name)
        content_deps = generate_deps_module(user_model_name)
        final_deps = preserve_custom_sections(f_deps_path, content_deps)
        with open(f_deps_path, "w", encoding="utf-8") as fp:
            fp.write(final_deps)
