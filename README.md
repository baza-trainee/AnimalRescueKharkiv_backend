# Animal Rescue Kharkiv

Description

## Features

- **Full async operation**  
- **Modular structure** for API endpoints  
- **Asynchronous SQLAlchemy** for database operations  
- **Alembic** support for database migrations  
- **Easy local setup** (instructions in `README.md`)  
- **Automated loading** of routes and SQLAlchemy models  
- **Docker Compose** for deployment and local setup  
  - Runs the core application, database, and Redis  
  - Includes health checks to ensure stability and prevent crashes  
- **Caching of GET requests** until module data changes via PUT/POST/PATCH  
- **Pydantic schemas and settings** for request/response serialization, validation, and project configuration (including `.env` files)  
- **OAuth2** for authorization

## Getting Started

1. Clone the repository:

```bash
git clone https://github.com/baza-trainee/AnimalRescueKharkiv_backend.git
cd AnimalRescueKharkiv_backend
```

2. Install the dependencies:

```bash
pip install poetry
poetry shell
poetry update
```

3. Please rename `.env.example` file to `.env` and set up the environment variables in it.

4. Populate database schema:

```bash
alembic upgrade head
```

5. Run the application:

```bash
python main.py
```

6. Access the API documentation at `http://localhost:8000/docs`.

## API Endpoints

### Authentication

## Developed by:

- [Yuliia Chorna](https://github.com/YuliiaChorna1)
- [Mykhailo Rozhkov](https://github.com/DaTrEvTeR)
- [Paul Kravchenko](https://github.com/PaulKravchenko)

&#xa0;
