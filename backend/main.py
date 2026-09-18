from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DATABASE_URL = "mysql+pymysql://taskuser:taskpassword@localhost:3306/taskdb"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


# ============================================================
# PASSWORD HASHING
# ============================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# ============================================================
# JWT CONFIGURATION
# ============================================================

SECRET_KEY = "change-this-secret-key"
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60


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
        cascade="all, delete"
    )


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True)
    completed = Column(Boolean, default=False)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    owner = relationship(
        "User",
        back_populates="tasks"
    )


# Create database tables
Base.metadata.create_all(bind=engine)


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="3-Tier Task Management API",
    description="Task Management Application Backend",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DATABASE DEPENDENCY
# ============================================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ============================================================
# PYDANTIC MODELS
# ============================================================

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TaskCreate(BaseModel):
    title: str
    description: str = ""


class TaskUpdate(BaseModel):
    title: str
    description: str
    completed: bool


# ============================================================
# PASSWORD FUNCTIONS
# ============================================================

def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str):
    return pwd_context.verify(password, hashed_password)


# ============================================================
# JWT FUNCTIONS
# ============================================================

def create_access_token(user_id: int):

    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "user_id": user_id,
        "exp": expire
    }

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token


def get_current_user(
    token: str,
    db: Session
):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("user_id")

        if user_id is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

        user = db.query(User).filter(
            User.id == user_id
        ).first()

        if user is None:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )

        return user

    except jwt.ExpiredSignatureError:

        raise HTTPException(
            status_code=401,
            detail="Token expired"
        )

    except jwt.InvalidTokenError:

        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
def root():

    return {
        "message": "3-Tier Task Management API is running"
    }


@app.get("/health")
def health_check():

    return {
        "status": "healthy"
    }


# ============================================================
# REGISTER
# ============================================================

@app.post("/register")
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):

    existing_user = db.query(User).filter(
        (User.email == request.email) |
        (User.username == request.username)
    ).first()

    if existing_user:

        raise HTTPException(
            status_code=400,
            detail="Username or email already exists"
        )

    hashed_password = hash_password(
        request.password
    )

    new_user = User(
        username=request.username,
        email=request.email,
        password=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User registered successfully",
        "user_id": new_user.id
    }


# ============================================================
# LOGIN
# ============================================================

@app.post("/login")
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.email == request.email
    ).first()

    if not user:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(
        request.password,
        user.password
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    token = create_access_token(
        user.id
    )

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "username": user.username
    }


# ============================================================
# GET CURRENT USER TASKS
# ============================================================

@app.get("/tasks")
def get_tasks(
    token: str,
    db: Session = Depends(get_db)
):

    user = get_current_user(
        token,
        db
    )

    tasks = db.query(Task).filter(
        Task.user_id == user.id
    ).all()

    return tasks


# ============================================================
# CREATE TASK
# ============================================================

@app.post("/tasks")
def create_task(
    request: TaskCreate,
    token: str,
    db: Session = Depends(get_db)
):

    user = get_current_user(
        token,
        db
    )

    task = Task(
        title=request.title,
        description=request.description,
        completed=False,
        user_id=user.id
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return task


# ============================================================
# UPDATE TASK
# ============================================================

@app.put("/tasks/{task_id}")
def update_task(
    task_id: int,
    request: TaskUpdate,
    token: str,
    db: Session = Depends(get_db)
):

    user = get_current_user(
        token,
        db
    )

    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == user.id
    ).first()

    if not task:

        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    task.title = request.title
    task.description = request.description
    task.completed = request.completed

    db.commit()
    db.refresh(task)

    return task


# ============================================================
# DELETE TASK
# ============================================================

@app.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    token: str,
    db: Session = Depends(get_db)
):

    user = get_current_user(
        token,
        db
    )

    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == user.id
    ).first()

    if not task:

        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    db.delete(task)
    db.commit()

    return {
        "message": "Task deleted successfully"
    }


# ============================================================
# MARK TASK COMPLETE
# ============================================================

@app.patch("/tasks/{task_id}/complete")
def complete_task(
    task_id: int,
    token: str,
    db: Session = Depends(get_db)
):

    user = get_current_user(
        token,
        db
    )

    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == user.id
    ).first()

    if not task:

        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    task.completed = True

    db.commit()
    db.refresh(task)

    return task