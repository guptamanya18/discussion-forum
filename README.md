# Advanced Real-Time Discussion Forum

## Project Overview

This project implements a scalable discussion forum that allows users to communicate, collaborate, and participate in structured conversations. The system supports user authentication, threaded discussions, notifications, and role‑based access control.

The backend is built using FastAPI and the project will later include a React frontend that consumes REST APIs provided by the backend.

The system is designed with three main user roles:

* **Admin** – manages platform level settings and users
* **Moderator** – manages communities and discussions
* **Member/User** – participates in communities and discussions

---

# Tech Stack

## Backend

* FastAPI
* Uvicorn
* SQLAlchemy
* Passlib (for password hashing)
* bcrypt
* python-jose (JWT authentication)

## Package Manager

* uv

## Database

* SQLite (development database)

## Future Frontend

* React
* REST API integration

---

# Project Features

The discussion forum will include the following major features:

## User Management

Users can:

* Register an account
* Login securely
* Maintain a profile
* Have roles (admin / moderator / member)

User profile information includes:

* username
* email
* bio
* avatar

Role-based dashboards will be implemented for different user types.

---

# Backend Architecture

The backend follows a modular structure to keep the project organized and scalable.

```
app/
 ├── main.py
 ├── database.py
 ├── models.py
 ├── schemas.py
 ├── auth.py
 └── routers/
      └── users.py
```

### main.py

Entry point of the FastAPI application.

Responsible for:

* creating the FastAPI app
* registering routers
* initializing database tables

---

### database.py

Handles database configuration using SQLAlchemy.

Responsibilities:

* creating the database engine
* creating database sessions
* providing database dependency to APIs

Example:

```
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
```

A dependency function is used to provide database sessions to API routes:

```
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

This ensures that:

* each API request gets a fresh database session
* the session closes automatically after the request finishes

---

# Database Model

The user table is defined in `models.py`.

Fields include:

* id
* username
* email
* hashed_password
* role

Example model:

```
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    hashed_password = Column(String)
    role = Column(String, default="member")
```

Supported roles:

* admin
* moderator
* member

---

# API Schemas

Schemas define how request and response data should look.

Defined in `schemas.py` using Pydantic.

Example:

```
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
```

FastAPI automatically validates incoming request data using these schemas.

---

# Password Security

User passwords are **never stored directly in the database**.

Passwords are hashed using **Passlib with bcrypt**.

Example:

```
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    return pwd_context.hash(password)
```

Password processing flow:

```
User password
      ↓
Hash function
      ↓
Bcrypt encryption
      ↓
Stored as hashed password in database
```

This protects user accounts even if the database is compromised.

---

# User Registration API

Endpoint:

```
POST /register
```

Example request:

```
{
  "username": "manya",
  "email": "manya@gmail.com",
  "password": "123456"
}
```

Implementation example:

```
def register(user: UserCreate, db: Session = Depends(get_db)):

    hashed_password = hash_password(user.password)

    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User registered successfully"}
```

---

# Dependency Injection

FastAPI provides dependencies automatically using `Depends()`.

Example:

```
db: Session = Depends(get_db)
```

Flow:

1. FastAPI calls `get_db()`
2. A database session is created
3. The session is passed to the route function
4. After the request finishes the session is closed

This prevents connection leaks and keeps the code clean.

---

# API Testing

FastAPI automatically provides API documentation using Swagger UI.

Access it at:

```
http://127.0.0.1:8000/docs
```

From this interface we can:

* test API endpoints
* send requests
* view request and response formats

---

# Compatibility Fix Applied

A compatibility issue occurred between **Passlib** and newer versions of **bcrypt**.

This caused password hashing errors during user registration.

The issue was resolved by installing a compatible bcrypt version:

```
uv remove bcrypt
uv add bcrypt==4.0.1
```

---

# Current Implemented Capabilities

The system currently supports:

* FastAPI backend setup
* Database connection with SQLAlchemy
* User database model
* Password hashing
* User registration API
* API testing through Swagger UI

---

# Planned Features

Upcoming functionality will expand the forum into a full discussion platform.

Planned features include:

## Authentication

* User login
* JWT token generation
* Protected routes
* Current user identification

## Communities

Users will be able to:

* create communities
* join communities
* manage community discussions

## Threaded Discussions

The forum will support nested discussions where users can:

* create posts
* reply to posts
* reply to replies

This creates threaded conversations.

## Real-Time Messaging

Using WebSockets, the system will support:

* live discussions
* instant updates

## Notifications

Users will receive notifications for:

* replies to their posts
* mentions
* new messages

## Role-Based Dashboards

Different dashboards will exist for:

* admins
* moderators
* members

Each role will have different permissions and capabilities.
