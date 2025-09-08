def replace_cote(value: str):
    if type(value) == type([]):
        return str(value).replace("'", '"')
    return value


def generate_env(config: dict, output_file: str = ".env", use_docker=False):
    """
    Generate a .env file with structured comments and the provided configuration values.
    """
    content = f"""\
# --- Project Metadata ---
PROJECT_NAME='{replace_cote(config["project_name"])}'
IMAGE_NAME='{replace_cote(config["docker_image_backend"])}'

# --- Networking Configuration ---
HOST_PORT='{replace_cote(config["host_port"])}'
CONTAINER_PORT='{replace_cote(config["container_port"])}'

# --- CORS Settings ---
# Comma-separated list of frontend origins allowed to access the backend
# Example for local development with React/Vue/Angular default ports
BACKEND_CORS_ORIGINS={replace_cote(config["backend_cors_origins"])}

# --- MySQL Database Configuration ---
MYSQL_HOST='{replace_cote(config["mysql_host"]) if not use_docker else 'host.docker.internal'}'  # Or the Docker service name (e.g., db, host.docker.internal) or external host IP
MYSQL_PORT={replace_cote(config["mysql_port"])}
MYSQL_USER='{replace_cote(config["mysql_user"])}'
MYSQL_PASSWORD='{replace_cote(config["mysql_password"])}'
MYSQL_DATABASE='{replace_cote(config["mysql_database"])}'

# --- Superuser Credentials ---
FIRST_SUPERUSER='{replace_cote(config["first_superuser"])}'
LAST_NAME_SUPERUSER='{replace_cote(config["last_name_superuser"])}'
FIRST_NAME_SUPERUSER='{replace_cote(config["first_name_superuser"])}'
FIRST_SUPERUSER_PASSWORD='{replace_cote(config["first_superuser_password"])}'  # Change this for production!

# --- App Configuration ---
API_V1_STR='/api/v1'
SECRET_KEY='{replace_cote(config["secret_key"])}'  # Generate a strong key, e.g. openssl rand -hex 32
ENVIRONMENT='development'

# --- MongoDB Settings ---
MONGO_DB_HOST='host.docker.internal'
MONGO_DB_PORT=27017
MONGO_DB_USER='root'
MONGO_DB_PASSWORD='password'
MONGO_DB_CLIENT='admin'
MONGO_DB_COLLECTION='investissement'

# -- Test ---
TESTING=1
"""
    with open(output_file, "w") as f:
        f.write(content)

    print(f"Generated structured .env file at: {output_file}")
