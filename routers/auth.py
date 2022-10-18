import sys

sys.path.append("..")

from fastapi import Depends, HTTPException, status, APIRouter, Request
from pydantic import BaseModel
from typing import Optional
import models
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from datetime import datetime, timedelta
from jose import jwt, JWTError

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

SECRET_KEY = 'kajdkldjfandfmnwmwr21q23r1qr56q46'
ALGORYTHM = 'HS256'

templates = Jinja2Templates(directory="templates")


class CreateUser(BaseModel):
    username: str
    email: Optional[str]
    first_name: str
    last_name: str
    password: str
    phone_number: Optional[str]


bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated="auto")

models.Base.metadata.create_all(bind=engine)

oauth2_bearer = OAuth2PasswordBearer(tokenUrl='token')

router = APIRouter(
    prefix="/auth",
    tags=['auth'],
    responses={401: {"user": "Not Authorized"}}
)


def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


def get_password_hash(password: str) -> str:
    """
        hash a password for security reasons
        :param password: a string as password
        :return: hashed password by bcrypt_context
    """
    return bcrypt_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
        verify that password match with hashed password
        :param plain_password: a string as plain password
        :param hashed_password: a string as hashed_password
        :return: true if passwords match else false
    """
    return bcrypt_context.verify(plain_password, hashed_password)


def authenticate_user(username: str, password: str, db):
    """
        authenticate a user in database with provided username and password
        :param username: a string as a username
        :param password: a string as password
        :param db: database session
        :return: false if provided username or password do not match with existing in db
        else return user instance

    """
    user = db.query(models.Users) \
        .filter(models.Users.username == username) \
        .first()

    if not user:
        return False

    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(username: str, user_id: int, expires_delta: Optional[timedelta] = None):
    encode = {"sub": username, "id": user_id}
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    encode.update({'exp': expire})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORYTHM)


async def get_current_user(token: str = Depends(oauth2_bearer)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORYTHM])
        username: str = payload.get('sub')
        user_id: int = payload.get("id")
        if username is None or user_id is None:
            raise get_user_exception()
        return {
            "username": username, "id": user_id
        }
    except JWTError:
        raise get_user_exception()


@router.post('/create/user')
async def create_new_user(create_user: CreateUser, db: Session = Depends(get_db)):
    """
        create a user with credential username and password
    """
    create_user_model = models.Users()
    create_user_model.email = create_user.email
    create_user_model.username = create_user.username
    create_user_model.first_name = create_user.first_name
    create_user_model.last_name = create_user.last_name
    create_user_model.phone_number = create_user.phone_number

    hash_password = get_password_hash(create_user.password)

    create_user_model.hashed_password = hash_password
    create_user_model.is_active = True

    db.add(create_user_model)
    db.commit()
    return {
        "status": 201,
        "msg": "user created successfully"
    }


@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(),
                                 db: Session = Depends(get_db)):
    """
        authenticate a user with provided username and password
        :param db: db session
    """
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise get_user_exception()
    token_expires = timedelta(minutes=20)
    token = create_access_token(user.username, user.id, expires_delta=token_expires)
    return {"token": token}


@router.get("/", response_class=HTMLResponse)
async def authentication_page(request: Request):
    return templates.TemplateResponse('login.html', {'request': request})


@router.get("/register", response_class=HTMLResponse)
async def register(request: Request):
    return templates.TemplateResponse('register.html', {'request': request})


# Exceptions
def get_user_exception():
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": 'Bearer'}
    )
    return credentials_exception


def token_exception():
    token_exception_response = HTTPException(
        status=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": 'Bearer'}
    )
    return token_exception_response
