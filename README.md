# 3-Tier Task Management Application

A task-management application that runs in Docker. It has a React screen, a FastAPI server, and a MySQL database. Users can create an account, log in, create tasks, complete tasks, undo completion, and delete their own tasks.

This README is a project guide and an interview study guide. It explains what each part does, how the parts talk to each other, how Docker starts them, and what could be improved for real production use.

## Simple Explanation First

Think of the project as three workers:

1. **The frontend** is the screen the user sees. It shows forms and tasks.
2. **The backend** is the rule keeper. It checks logins, checks task data, and talks to the database.
3. **The database** saves users and tasks.

Docker puts these three workers into separate containers and connects them. A container is a small, separate environment that runs one part of the application. A Docker image is the package used to create a container.

The basic path is:

```text
User -> React screen -> FastAPI server -> MySQL database
```

When a user logs in, the server gives the browser a signed login token. The browser sends this token with later task requests. The server uses it to know which user is making each request.

## Table of Contents

1. [What the Application Does](#what-the-application-does)
2. [Architecture](#architecture)
3. [Repository Structure](#repository-structure)
4. [Technology Choices](#technology-choices)
5. [Prerequisites](#prerequisites)
6. [Run with Docker Compose](#run-with-docker-compose)
7. [Run Locally Without Docker](#run-locally-without-docker)
8. [Configuration](#configuration)
9. [Docker Compose Explained](#docker-compose-explained)
10. [Dockerfiles Explained](#dockerfiles-explained)
11. [Backend Explained](#backend-explained)
12. [Frontend Explained](#frontend-explained)
13. [Database Explained](#database-explained)
14. [End-to-End Request Flows](#end-to-end-request-flows)
15. [API Reference](#api-reference)
16. [Authentication and Authorization](#authentication-and-authorization)
17. [Validation and Error Handling](#validation-and-error-handling)
18. [Saved Data and Startup](#saved-data-and-startup)
19. [Testing and Troubleshooting](#testing-and-troubleshooting)
20. [Production Readiness](#production-readiness)
21. [Interview Questions and Answers](#interview-questions-and-answers)
22. [Possible Improvements](#possible-improvements)

## What the Application Does

The application implements a user-scoped task list:

- A new user registers with a username, email, and password.
- The password is hashed with bcrypt before it is stored.
- The user logs in with email and password.
- The backend returns a signed JWT access token.
- The frontend stores the token in browser `localStorage` and sends it as a Bearer token.
- Authenticated users can read, create, update, complete, and delete only their own tasks.
- MySQL stores users and tasks, and a named Docker volume preserves the data across container recreation.

## Architecture

```text
Browser
  |
  | HTTP :80
  v
React application built by Vite and served by Nginx
  |
  | JSON API requests to http://localhost:8000
  | Authorization: Bearer <JWT>
  v
FastAPI backend running with Uvicorn
  |
  | SQLAlchemy + PyMySQL over the Docker network
  v
MySQL 8.0 database
  |
  v
Named volume: mysql_data
```

The three logical tiers are:

1. **Screen tier:** React displays the login screen and task dashboard.
2. **Logic tier:** FastAPI checks input, checks users, applies task rules, and reads or changes data.
3. **Data tier:** MySQL saves users and tasks and links each task to its owner.

The containers communicate differently depending on the caller:

- A browser on the host reaches the frontend at `http://localhost` and the backend at `http://localhost:8000`.
- The backend reaches MySQL at the Compose service name `mysql`, not `localhost`. Inside a container, `localhost` means that same container.
- The frontend is compiled into static files, so its Nginx container does not need Node.js at runtime.

## Repository Structure

```text
.
├── docker-compose.yml          # Starts and connects the containers
├── README.md                   # Project and interview documentation
├── backend/
│   ├── Dockerfile              # Backend image definition
│   ├── main.py                 # Models, schemas, auth, startup, and API routes
│   └── requirements.txt        # Pinned Python dependencies
├── database/
│   └── init.sql                # First-initialization schema and grants
└── frontend/
    ├── Dockerfile              # Multi-stage React build and Nginx runtime image
    ├── index.html              # Browser entry document
    ├── nginx.conf              # Static-file and SPA routing configuration
    ├── package.json             # Frontend dependencies and scripts
    ├── vite.config.js           # Vite development configuration
    └── src/
        ├── app.jsx             # Main React component and API behavior
        ├── main.jsx            # React entry point
        └── style.css            # Application styles
```

## Technology Choices

| Layer | Technology | Purpose |
|---|---|---|
| UI | React 18 | Component rendering and client-side state |
| Frontend build | Vite 5 | Fast development server and production bundling |
| Static server | Nginx Alpine | Serves the compiled frontend efficiently |
| API | FastAPI | Typed Python HTTP API and automatic OpenAPI documentation |
| API server | Uvicorn | ASGI server for FastAPI |
| ORM | SQLAlchemy 2 | Models, queries, sessions, and transactions |
| Database driver | PyMySQL | MySQL connectivity from Python |
| Database | MySQL 8.0 | Durable relational storage |
| Authentication | bcrypt and PyJWT | Password hashing and signed access tokens |
| Containers | Docker Compose | Starts the containers and connects them |

## Prerequisites

For the containerized workflow, install:

- Docker Desktop with Docker Compose support
- A browser
- Git, if cloning the project

For the non-containerized workflow, additionally install:

- Python 3.11+
- Node.js 20+
- A running MySQL 8.0 instance

## Run with Docker Compose

From the repository root:

```bash
docker compose up --build
```

Open:

- Frontend: `http://localhost`
- API root: `http://localhost:8000/`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health endpoint: `http://localhost:8000/health`

Run detached:

```bash
docker compose up --build -d
```

View service logs:

```bash
docker compose logs -f
# Or one service:
docker compose logs -f backend
```

Stop containers but preserve database data:

```bash
docker compose down
```

Stop containers and delete the database volume. This permanently removes stored users and tasks:

```bash
docker compose down -v
```

Rebuild one service:

```bash
docker compose build backend
```

The first database startup runs `database/init.sql`. MySQL runs files in `/docker-entrypoint-initdb.d` only when the database folder is empty. If the database already has data, changing `init.sql` later will not change the old database automatically.

## Run Locally Without Docker

The local workflow still needs MySQL. Set the database address to your computer instead of the Docker name `mysql`.

### Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL = "mysql+pymysql://taskuser:taskpassword@localhost:3306/taskdb"
$env:SECRET_KEY = "development-only-secret"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Vite normally displays the development URL, commonly `http://localhost:5173`. The frontend uses `VITE_API_URL` when it is defined; otherwise it defaults to `http://localhost:8000`.

PowerShell example:

```powershell
$env:VITE_API_URL = "http://localhost:8000"
npm run dev
```

## Configuration

The Compose file currently supplies these values:

| Variable | Used by | Current purpose |
|---|---|---|
| `DATABASE_URL` | Backend | SQLAlchemy connection URL; uses host `mysql` inside Compose |
| `SECRET_KEY` | Backend | Signs and verifies JWTs |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Backend | JWT lifetime, currently 60 minutes |
| `MYSQL_ROOT_PASSWORD` | MySQL | Administrative password |
| `MYSQL_DATABASE` | MySQL | Initial database, `taskdb` |
| `MYSQL_USER` | MySQL | Application user, `taskuser` |
| `MYSQL_PASSWORD` | MySQL | Application password |
| `VITE_API_URL` | Frontend build | Optional API base URL; not currently set in Compose |

The values in `docker-compose.yml` are for learning and local testing only. Real passwords should come from a private `.env` file, a secret manager, or the deployment system. Never commit real passwords to Git.

## Docker Compose Explained

### `mysql` service

- `image: mysql:8.0` selects the MySQL image.
- `container_name: mysql_db` gives the container a predictable name.
- `restart: unless-stopped` restarts the service after failures or daemon restarts unless explicitly stopped.
- The environment variables configure the root account, application database, and application user on first initialization.
- `3306:3306` publishes MySQL to the host. This is useful for local debugging, but production deployments should usually keep the database private.
- `mysql_data:/var/lib/mysql` mounts durable database storage.
- `./database/init.sql:/docker-entrypoint-initdb.d/init.sql:ro` mounts the schema script read-only.
- The health check uses `mysqladmin ping` so Compose can distinguish a running process from a ready database.

### `backend` service

- `build: ./backend` builds from `backend/Dockerfile`.
- `8000:8000` publishes the API to the host.
- `depends_on` with `condition: service_healthy` delays backend startup until MySQL passes its health check.
- The database hostname is `mysql`, because Compose provides service-name DNS on its default network.
- `restart: unless-stopped` improves local resilience.

`depends_on` controls the startup order. The health condition waits for MySQL to answer. It does not guarantee that MySQL will always stay available, so the backend also tries to connect several times.

### `frontend` service

- `build: ./frontend` runs the multi-stage frontend Dockerfile.
- `80:80` exposes Nginx on the host's port 80.
- It depends on the backend at startup, but the browser still calls the backend using the host URL `localhost:8000`.
- It does not proxy API requests through Nginx; the frontend and API are separate origins in the current design.

### Named volume

`mysql_data` is a named storage area managed by Docker. It stays after `docker compose down`. It is deleted by `docker compose down -v` or by deleting the volume yourself.

## Dockerfiles Explained

### `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim
```

Uses a small Python 3.11 base image. It contains what the API needs without extra tools.

```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
```

Prevents `.pyc` files from being written and makes Python logs appear immediately in container logs. All later commands run from `/app`.

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt
```

Copies the dependency list before the application code. Docker can then reuse this step when only Python code changes. `--no-cache-dir` keeps pip's temporary download files out of the image.

```dockerfile
COPY . .
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
 && chown -R appuser:appuser /app
USER appuser
```

Copies the backend, creates a user that cannot log in, and runs the API as that user instead of as root. This reduces damage if the container is attacked.

```dockerfile
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Documents the internal port and starts Uvicorn. `0.0.0.0` lets other containers and the host reach the API.

### `frontend/Dockerfile`

The frontend uses two build steps. The first step uses Node 20 to install packages and create the website files. The second step uses Nginx to serve those files. The final image does not contain Node or the source code, so it is smaller.

The build uses `npm ci`, which requires a `package-lock.json` (or compatible npm lock file). This repository includes `frontend/package-lock.json`, so the dependency installation is reproducible:

```bash
cd frontend
npm ci
```

In a team or CI environment, keep the lock file synchronized with `package.json` and prefer `npm ci` for deterministic builds.

## Backend Explained

The backend is mainly in `backend/main.py`. That file contains the database models, input rules, login code, startup code, and API routes.

### Configuration and SQLAlchemy setup

The backend reads `DATABASE_URL`, `SECRET_KEY`, and `ACCESS_TOKEN_EXPIRE_MINUTES` from environment variables. It has local defaults if they are missing. SQLAlchemy creates:

- An `Engine`, which manages database connections.
- `SessionLocal`, which creates a short-lived database session for a request.
- `Base`, the starting point for the database models.

`pool_pre_ping=True` checks a connection before using it. `pool_recycle=3600` replaces old connections so MySQL connections do not stay open too long.

### ORM models

`User` represents a row in the `users` table. One user can have many tasks.

`Task` represents a row in the `tasks` table. Its `user_id` field says who owns it. If a user is deleted, MySQL also deletes that user's tasks because of `ON DELETE CASCADE`.

### Pydantic schemas

Request schemas check incoming JSON before the route code runs. A schema is simply a list of rules for the data:

- `RegisterRequest`: username, valid email, and password length 6-128.
- `LoginRequest`: valid email and password.
- `TaskCreate`: title length 1-200 and description up to 1000 characters.
- `TaskUpdate`: optional fields for partial update behavior.

Response schemas define what the API sends back. `from_attributes=True` lets FastAPI turn a database object into JSON.

### Password handling

`hash_password` changes the password into a one-way bcrypt hash. The database stores the hash, not the real password. `verify_password` checks a login password against that hash. The original password cannot be recovered from the hash.

The code limits the password sent to bcrypt to 72 bytes because bcrypt has that limit. A real application should clearly explain this limit or use a password policy that counts bytes correctly.

### JWT handling

`create_access_token` creates a signed JWT login token. It contains:

- `user_id`: the authenticated user's database ID
- `iat`: issued-at timestamp
- `exp`: expiration timestamp

JWTs are signed, not hidden. Anyone who has a token can read its contents, so private information must not be put inside it. The server checks the signature and expiration on every protected request.

### Dependency injection

`get_db` creates one database session for each request and closes it afterward. This prevents unused connections from staying open.

`get_current_user` is used by protected routes. It:

1. Reads the Bearer token from the `Authorization` header.
2. Rejects a missing token with HTTP 401.
3. Verifies the JWT signature and expiration.
4. Reads `user_id` from the claims.
5. Loads the user from MySQL.
6. Rejects deleted or unknown users.

This keeps the login check in one place. Task routes do not need to repeat the same code.

### What happens when the backend starts

FastAPI's startup handler runs before the server accepts requests:

1. `wait_for_database` attempts `SELECT 1` up to 30 times.
2. It waits two seconds between failed attempts.
3. `Base.metadata.create_all` verifies/creates ORM tables.
4. The application begins serving requests.

The health route also checks the database and returns a simple status message.

### CORS

The backend currently allows requests from any website and does not allow cookies. This works because login uses an `Authorization` header. In production, `allow_origins` should list only the real frontend address.

### API routes

The task routes call `_get_owned_task`. It checks both the task ID and the current user's ID. This stops one user from opening or changing another user's task by guessing its ID.

## Frontend Explained

### Application entry point

`frontend/src/main.jsx` finds the `root` element in `index.html`, displays the `App` component, and loads the CSS file. `React.StrictMode` helps find common problems during development.

### Vite and environment variables

`vite.config.js` turns on React support and makes the development server available on port 5173. `VITE_API_URL` is added when the website is built, so changing it requires a new build.

### React state

The `App` component remembers:

- JWT and username
- Whether the registration screen is visible
- Registration/login form values
- Task-create form values
- Loaded tasks
- Error, success, and loading messages

The first token and username are read from `localStorage`, so a page refresh keeps the user logged in until the token expires or the server returns 401.

### Central API helper

`apiFetch` builds logged-in requests in one place. It adds the JSON header and token, reads the response, shows FastAPI errors as text, and logs out when the server returns 401.

Login and registration use plain `fetch` because they do not yet have a token. Authenticated task operations use `apiFetch`.

### How tasks are loaded

When a token is present, `useEffect` calls `loadTasks`, which requests `GET /tasks`. After a task is created, completed, or deleted, React updates the list on the screen without reloading the whole page.

### Error normalization

FastAPI sends a simple `detail` message for many errors, but input errors use a list of objects. `extractErrorMessage` changes both formats into readable text so React can show them safely.

### Nginx production image

The frontend Dockerfile uses two stages:

1. **Builder stage:** Node 20 Alpine installs dependencies with `npm ci`, copies source files, and runs `npm run build`.
2. **Runtime stage:** Nginx Alpine receives only the generated `dist` files and the custom Nginx configuration.

This makes the final image smaller and removes the Node toolchain from the runtime container.

`nginx.conf` returns `index.html` when a browser asks for an unknown page. This is needed by a single-page React application. It also lets browsers keep static files for 30 days.

## Database Explained

### Schema

```text
users
-----
id          INT primary key, auto increment
username    VARCHAR(100), unique, required
email       VARCHAR(150), unique, required
password    VARCHAR(255), required

 tasks
 -----
 id          INT primary key, auto increment
 title       VARCHAR(200), required
 description VARCHAR(1000), nullable
 completed   BOOLEAN, required, default false
 user_id     INT, required, indexed foreign key to users.id
```

The relationship is one user to many tasks. `idx_tasks_user_id` supports the common query that loads a user's tasks. Unique constraints prevent duplicate usernames and emails.

`init.sql` creates the database and tables, gives the application user access, and reloads MySQL permissions. The backend's `create_all` is a second check when it starts. Neither one replaces proper database migration files for a real production system.

### Transactions

Registration, task creation, updates, completion changes, and deletion save their changes with a database transaction. If registration fails because of a database error, its changes are rolled back. Database sessions are closed after each request.

## End-to-End Request Flows

### Registration

1. The user submits the registration form in React.
2. The browser sends `POST /register` with JSON.
3. FastAPI and Pydantic validate the email and field lengths.
4. The route normalizes username/email and checks uniqueness.
5. bcrypt hashes the password.
6. SQLAlchemy inserts the user and commits.
7. The API returns HTTP 201 and the new user ID.
8. The frontend switches back to login and displays a success message.

### Login

1. React sends `POST /login` with email and password.
2. The backend normalizes the email and finds the user.
3. bcrypt verifies the supplied password.
4. The backend creates a signed JWT.
5. React stores `access_token` and username in `localStorage`.
6. React sets the token state, which triggers `GET /tasks`.

### Create task

1. React validates that the title is not blank after trimming.
2. `apiFetch` sends `POST /tasks` with the Bearer token.
3. `get_current_user` authenticates the token.
4. The route sets `user_id` from the authenticated user, never from client input.
5. SQLAlchemy inserts and commits the task.
6. The returned task is added to the beginning of the local list.

### Complete or delete task

1. The browser sends either `PATCH /tasks/{id}/complete` or `DELETE /tasks/{id}`.
2. Authentication identifies the current user.
3. `_get_owned_task` requires both the task ID and matching owner ID.
4. The backend changes or deletes the row and commits.
5. React updates or filters its local task list.

## API Reference

All request and response bodies are JSON unless stated otherwise.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/` | No | API welcome message |
| `GET` | `/health` | No | Database connectivity check |
| `POST` | `/register` | No | Create a user; returns 201 |
| `POST` | `/login` | No | Verify credentials and return JWT |
| `GET` | `/tasks` | Bearer | List current user's tasks |
| `POST` | `/tasks` | Bearer | Create a task; returns 201 |
| `PUT` | `/tasks/{task_id}` | Bearer | Update provided task fields |
| `PATCH` | `/tasks/{task_id}/complete` | Bearer | Toggle completion state |
| `DELETE` | `/tasks/{task_id}` | Bearer | Delete an owned task |

Example registration:

```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"secret123"}'
```

Example login:

```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"secret123"}'
```

Use the returned token in protected requests:

```bash
curl http://localhost:8000/tasks \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Status code behavior

- `200`: successful read, update, toggle, delete, or login
- `201`: successful registration or task creation
- `400`: business validation such as duplicate email or blank task title
- `401`: missing, invalid, or expired authentication
- `404`: task does not exist for the current user
- `422`: Pydantic request validation failure
- `500`: unexpected server or database failure

## Authentication and Authorization

**Authentication** means checking who the user is. This project does that by checking the JWT token.

**Authorization** means checking what the user is allowed to access. The task queries do this with `Task.user_id == current_user.id`. A valid token alone is not enough; the server must also check task ownership.

The token is stored in `localStorage`. This is simple for a demo, but JavaScript can read it. An XSS bug could expose it. A stronger design usually uses secure `HttpOnly` and `SameSite` cookies with CSRF protection, or uses short-lived access tokens and refresh tokens.

## Validation and Error Handling

The project checks data in several places:

- HTML inputs provide basic browser checks.
- React checks blank task titles and minimum registration password length.
- Pydantic checks data types, email format, and length limits.
- Route logic trims strings and enforces business rules.
- Database rules enforce unique values, required values, indexes, and links between tables.

The frontend safely reads responses with `safeJson`, changes validation errors into readable messages, and clears the login state when it receives HTTP 401.

## Saved Data and Startup

There are two table-creation mechanisms:

1. MySQL runs `init.sql` only for a brand-new data directory.
2. The backend runs SQLAlchemy `create_all` whenever it starts.

This is useful for a small demonstration. For a real system, use Alembic or another migration tool when tables change. `create_all` can create missing tables, but it does not safely handle renamed columns, moved data, or large table changes.

The database volume is the durability boundary. Removing it removes the application data. Container images are disposable; the named volume is where state lives.

## Testing and Troubleshooting

### Basic verification

```bash
docker compose ps
docker compose logs backend
docker compose logs mysql
curl http://localhost:8000/health
```

Expected health output includes:

```json
{"status":"healthy","database":"connected"}
```

The API's interactive contract can be inspected at `http://localhost:8000/docs`.

### Common problems

**Port 80, 3306, or 8000 is already in use**

Change the host side of the mapping, for example `8080:80` for the frontend, then open the new host port. The container port remains unchanged.

**Backend cannot connect to MySQL**

Check `docker compose logs mysql`. Confirm the backend uses host `mysql`, not `localhost`, and wait for the health check/startup retry loop to complete.

**Database changes do not appear**

The named volume may contain an already-initialized database. Use a proper migration, or in disposable development data run `docker compose down -v` and recreate the stack.

**Frontend cannot reach the API**

Confirm the backend is running on port 8000 and that the built frontend has the correct `VITE_API_URL`. Vite variables are build-time values, not runtime browser environment variables.

**Frontend image build fails at `npm ci`**

Confirm that `frontend/package-lock.json` is present and synchronized with `package.json`. Regenerate it with `npm install` only when dependencies change, then rebuild the image.

**Login suddenly stops working after changing `SECRET_KEY`**

Existing JWTs were signed with the old key and are intentionally invalid after the key changes. Users must log in again.

## Production Readiness

This project is good for learning and local testing. Before using it for real users, make these changes:

- Move all passwords and `SECRET_KEY` out of source-controlled Compose configuration.
- Use a strong randomly generated secret and rotate it with a planned key strategy.
- Restrict CORS to known frontend origins.
- Put the application behind HTTPS and a reverse proxy/load balancer.
- Avoid publishing MySQL directly to the host unless operationally required.
- Use Alembic migrations instead of relying on `create_all`.
- Add automatic tests for the backend, API, database, and frontend.
- Add structured logs, metrics, tracing, and centralized error reporting.
- Add rate limiting and account lockout or abuse protection for login.
- Consider short-lived access tokens with refresh-token rotation.
- Review whether `localStorage` is acceptable for the threat model.
- Add database backups, restore testing, and a recovery plan.
- Pin base image digests and scan images/dependencies for vulnerabilities.
- Add a Docker build context `.dockerignore` file to avoid copying unnecessary files.
- Run containers as non-root users and set CPU and memory limits.
- Use a production process model appropriate for the deployment size, such as multiple Uvicorn workers behind a proxy.
- Add pagination and filtering before task volume becomes large.

## Interview Questions and Answers

### Why is this called a three-tier application?

The screen, the application rules, and the saved data are in three separate parts: frontend, backend, and database. Each part can be changed or scaled separately, even though Compose starts them together on one computer.

### Why does the backend connect to `mysql` instead of `localhost`?

Compose gives each service a name on its private network. The name `mysql` points to the MySQL container. Inside the backend container, `localhost` means the backend container, not the MySQL container.

### What does the MySQL health check solve?

MySQL can have a running container but still be starting up. The health check waits until MySQL can answer. The backend also retries with `wait_for_database`, so it can recover while MySQL is starting.

### Why use both `init.sql` and SQLAlchemy models?

`init.sql` prepares a new MySQL database and gives the app user access. The SQLAlchemy models describe the same tables in Python, and `create_all` checks or creates missing tables when the backend starts. For production, use one migration tool to manage table changes.

### How is a password protected?

The password is changed into a bcrypt hash before it is saved. The database stores only that hash. At login, bcrypt compares the new password with the hash. The server never decrypts or stores the real password.

### What is inside the JWT?

The token contains the user ID, the time it was made, and its expiration time. It is signed with HS256 and `SECRET_KEY`. It is not encrypted, so it must not contain private information.

### How does the application stop one user seeing another user's task?

Every protected task lookup checks both the task ID and the logged-in user's ID. If a user guesses someone else's task ID, the API returns 404 instead of showing the task.

### Why use `PATCH` for completion?

Completion changes only one part of a task: the `completed` field. That is why the endpoint uses `PATCH`. `PUT /tasks/{task_id}` can change the other task fields too.

### Why does the frontend use a central `apiFetch` helper?

It keeps the headers, token, response reading, and 401 logout code in one place. Each task request can then use the same helper.

### Why use a multi-stage frontend Docker build?

Node is needed to build the website, but it is not needed to serve the finished files. The final Nginx image contains only the website files and Nginx, so it is smaller and has fewer tools that could be attacked.

### What happens if the database container is deleted?

If only the MySQL container is deleted, the named volume keeps the data. A new container can use that volume. If the volume is deleted too, the old data is lost and MySQL starts again from `init.sql`.

### What is the difference between `depends_on` and application readiness?

`depends_on` controls the order in which Compose starts services. Here it also uses the MySQL health result. It does not guarantee that a service will never fail, so the application still needs retries and health checks.

### What are the main weaknesses of the current authentication design?

The demo stores JWTs in `localStorage`, has a default secret in the code, cannot cancel a token before it expires, and allows requests from any website. These choices are easy for learning but should be changed before production.

### How would you scale this system?

The frontend could be served by a CDN or several Nginx containers. Several backend containers could run behind a load balancer because the API does not keep user data in its own memory. MySQL would need backups, good indexes, connection settings, and possibly read-only copies. All backend containers would need the same login-token settings.

### How would you test it?

Test password hashing and token checks by themselves. Test every API route, including attempts to access another user's task. Test the API with a temporary MySQL container. Test the frontend forms and error messages. Finally, run one full test from registration through task deletion.

## Possible Improvements

A natural next iteration would:

1. Add Alembic migrations.
2. Add automated tests and CI.
3. Replace hard-coded Compose secrets with environment or secret-manager inputs.
4. Restrict CORS and add HTTPS deployment.
5. Add task editing in the frontend to expose the existing `PUT` endpoint.
6. Add pagination, search, and task filters.
7. Add a reverse proxy path such as `/api` so the browser can use one origin.
8. Add observability and operational health/readiness endpoints.
9. Add a `.dockerignore` and image vulnerability scanning.
10. Add a production deployment manifest or Helm chart if Kubernetes is required.
