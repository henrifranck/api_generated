
## Requirements

* [Docker](https://www.docker.com/).
* [Docker Compose](https://docs.docker.com/compose/install/).

## Api local development

* Start the stack with Docker Compose:

```bash
docker-compose up -d
```

* Now you can open your browser and interact with these URLs:

Api, JSON based web API based on OpenAPI: http://localhost:8080/api/

Automatic interactive documentation with Swagger UI (from the OpenAPI api): http://localhost:8080/docs

Alternative automatic documentation with ReDoc (from the OpenAPI api): http://localhost:8080/redoc


**Note**: The first time you start your stack, it might take a minute for it to be ready. While the api waits for
the database to be ready and configures everything. You can check the logs to monitor it.

To check the logs, run:

```bash
docker-compose logs
```

To check the logs of a specific service, add the name of the service, e.g.:

```bash
docker-compose logs api
```

If your Docker is not running in `localhost` (the URLs above wouldn't work) check the sections below on **Development
with Docker Toolbox** and **Development with a custom IP**.

### Migrations

As during local development your app directory is mounted as a volume inside the container, you can also run the
migrations with `alembic` commands inside the container and the migration code will be in your app directory (instead of
being only inside the container). So you can add it to your git repository.

Make sure you create a "revision" of your models and that you "upgrade" your database with that revision every time you
change them. As this is what will update the tables in your database. Otherwise, your application will have errors.

* Start an interactive session in the api container:

```console
$ docker-compose exec api bash
```

* If you created a new model in `./api/app/app/models/`, make sure to import it in `./api/app/app/db/base.py`,
  that Python module (`base.py`) that imports all the models will be used by Alembic.

* After changing a model (for example, adding a column), inside the container, create a revision, e.g.:

```console
$ alembic revision --autogenerate -m "Add column last_name to User model"
```

* Commit to the git repository the files generated in the alembic directory.

* After creating the revision, run the migration in the database (this is what will actually change the database):

```console
$ alembic upgrade head
```

If you don't want to use migrations at all, uncomment the line in the file at `./api/app/app/db/init_db.py` with:

```python
Base.metadata.create_all(bind=engine)
```

and comment the line in the file `prestart.sh` that contains:

```console
$ alembic upgrade head
```

If you don't want to start with the default models and want to remove them / modify them, from the beginning, without
having any previous revision, you can remove the revision files (`.py` Python files)
under `./api/app/alembic/versions/`. And then create a first migration as described above.
