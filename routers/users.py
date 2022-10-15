import sys

sys.path.append("..")

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from passlib.context import CryptContext

import models
from database import engine, SessionLocal
from .auth import get_current_user, get_user_exception, verify_password, get_password_hash

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "not found"}}
)

models.Base.metadata.create_all(bind=engine)


def get_db():
    db = None
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


class UserVerification(BaseModel):
    username: str
    password: str
    new_password: str


@router.get("/")
async def get_all_users(db: Session = Depends(get_db)):
    """
    returns all users
    """
    return db.query(models.Users).all()


@router.get("/{user_id}")
async def get_user_by_path(user_id: int, db: Session = Depends(get_db)):
    fetched_user = db.query(models.Users) \
        .filter(models.Users.id == user_id) \
        .first()
    if fetched_user is not None:
        return fetched_user

    return "Invalid User ID"


@router.get("/user/")
async def get_user_by_query(user_id: int, db: Session = Depends(get_db)):
    fetched_user = db.query(models.Users) \
        .filter(models.Users.id == user_id) \
        .first()

    if fetched_user is not None:
        return fetched_user
    return "Invalid User ID"


@router.put("/user/password")
async def user_password_change(user_verification: UserVerification,
                               user: dict = Depends(get_current_user),
                               db: Session = Depends(get_db)):
    if user is None:
        raise get_user_exception()

    fetched_user = db.query(models.Users) \
        .filter(models.Users.id == user.get('id')) \
        .first()

    if fetched_user is not None:
        if user_verification.username == fetched_user.username and verify_password(
                user_verification.password, fetched_user.hashed_password):
            fetched_user.hashed_password = get_password_hash(user_verification.new_password)
            db.commit()
            return "Password changed successfully"

    return "Invalid user or request"


@router.delete("/user")
async def delete_user(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        raise get_user_exception()

    fetched_user = db.query(models.Users) \
        .filter(models.Users.id == user.get('id')) \
        .first()

    if not fetched_user:
        return "Invalid user or request"

    db.delete(fetched_user)
    db.commit()
    return {"message": f"User with id {fetched_user.id} successfully deleted!"}
