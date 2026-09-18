import os
import time
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import bcrypt
import jwt

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    text,
)
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
    relationship,
    Session,
)
from sqlalchemy.exc import SQLAlchemyError, OperationalError


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("taskapi")


# ============================================================
# CONFIGURATION
# ============================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://taskuser:taskpassword@mysql:3306/taskdb",
)

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

logger.info("DATABASE_URL: %s", DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)

Base = declarative_base()


# ============================================================
# DATABASE MODELS
# ============================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password = Column(String(255), nullable=False)

    tasks = relationship(
        "Task",
        back_populates="owner",
        cascade="all, delete-orphan",
    )


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True, default="")
    completed = Column(Boolean, nullable=False, default=False)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    owner = relationship("User", back_populates="tasks")


# ============================================================
# SCHEMAS
# ============================================================

class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    message: str
    access_token: str
    token_type: str = "bearer"
    username: str


class MessageResponse(BaseModel):
    message: str


class RegisterResponse(BaseModel):
    message: str
    user_id: int


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    completed: Optional[bool] = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str] = ""
    completed: bool
    user_id: int


# ============================================================
# PASSWORD HASHING  (bcrypt used directly - no passlib)
# ============================================================

def hash_password(password: str) -> str:
    # bcrypt only reads the first 72 bytes of the password.
    pw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8")[:72],
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


# ============================================================
# JWT
# ============================================================

def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ============================================================
# DEPENDENCIES
# ============================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:

    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired, please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user


# ============================================================
# STARTUP  (wait for MySQL, then create tables)
# ============================================================

def wait_for_database(max_attempts: int = 30, delay: int = 2) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("Database connection established.")
            return
        except OperationalError as exc:
            logger.warning(
                "Database not ready (attempt %s/%s): %s",
                attempt, max_attempts, exc.__class__.__name__,
            )
            time.sleep(delay)

    raise RuntimeError("Could not connect to the database. Giving up.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting FastAPI application...")
    wait_for_database()
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified successfully.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="3-Tier Task Management API",
    description="Task Management Application Backend",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================
# CORS
# ============================================================
# Wildcard is safe here because auth uses the Authorization header,
# not cookies (allow_credentials must stay False with "*").

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HEALTH
# ============================================================

@app.get("/")
def root():
    return {"message": "3-Tier Task Management API is running"}


@app.get("/health")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as exc:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(exc),
        }


# ============================================================
# AUTH
# ============================================================

@app.post("/register", response_model=RegisterResponse, status_code=201)
def register(request: RegisterRequest, db: Session = Depends(get_db)):

    username = request.username.strip()
    email = request.email.strip().lower()

    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    try:
        if db.query(User).filter(User.email == email).first():
            raise HTTPException(status_code=400, detail="Email already registered")

        if db.query(User).filter(User.username == username).first():
            raise HTTPException(status_code=400, detail="Username already taken")

        new_user = User(
            username=username,
            email=email,
            password=hash_password(request.password),
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        logger.info("User registered: %s", new_user.username)

        return RegisterResponse(
            message="User registered successfully",
            user_id=new_user.id,
        )

    except HTTPException:
        raise
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Database error during registration")
        raise HTTPException(status_code=500, detail="Database error while registering user")
    except Exception:
        db.rollback()
        logger.exception("Registration failed")
        raise HTTPException(status_code=500, detail="Registration failed")


@app.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):

    email = request.email.strip().lower()

    try:
        user = db.query(User).filter(User.email == email).first()

        if user is None or not verify_password(request.password, user.password):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        return TokenResponse(
            message="Login successful",
            access_token=create_access_token(user.id),
            username=user.username,
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Login failed")
        raise HTTPException(status_code=500, detail="Login failed")


# ============================================================
# TASKS
# ============================================================

@app.get("/tasks", response_model=List[TaskResponse])
def get_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Task)
        .filter(Task.user_id == current_user.id)
        .order_by(Task.id.desc())
        .all()
    )


@app.post("/tasks", response_model=TaskResponse, status_code=201)
def create_task(
    request: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    title = request.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Task title is required")

    task = Task(
        title=title,
        description=(request.description or "").strip(),
        completed=False,
        user_id=current_user.id,
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return task


def _get_owned_task(task_id: int, user: User, db: Session) -> Task:
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == user.id)
        .first()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    request: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _get_owned_task(task_id, current_user, db)

    if request.title is not None:
        task.title = request.title.strip()
    if request.description is not None:
        task.description = request.description.strip()
    if request.completed is not None:
        task.completed = request.completed

    db.commit()
    db.refresh(task)

    return task


@app.patch("/tasks/{task_id}/complete", response_model=TaskResponse)
def complete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _get_owned_task(task_id, current_user, db)
    task.completed = not task.completed

    db.commit()
    db.refresh(task)

    return task


@app.delete("/tasks/{task_id}", response_model=MessageResponse)
def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _get_owned_task(task_id, current_user, db)

    db.delete(task)
    db.commit()

    return MessageResponse(message="Task deleted successfully")
