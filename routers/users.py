import sys

sys.path.append("..")

from starlette import status
from starlette.responses import RedirectResponse
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from passlib.context import CryptContext

import models
from database import engine, SessionLocal
from .auth import get_current_user, verify_password, get_password_hash
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "not found"}}
)

models.Base.metadata.create_all(bind=engine)
templates = Jinja2Templates(directory="templates")


def get_db():
    db = None
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


@router.get("/change-password", response_class=HTMLResponse)
async def change_password(request: Request):
    user = await get_current_user(request)

    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    context = {
        'request': request,
        'user': user
    }

    return templates.TemplateResponse('change_password.html', context)


@router.post("/change-password")
async def change_password_commit(request: Request,
                                 username: str = Form(...),
                                 old_password: str = Form(...),
                                 new_password: str = Form(...),
                                 db: Session = Depends(get_db)
                                 ):
    user = await get_current_user(request)

    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    fetched_user = db.query(models.Users).filter(models.Users.id == user.get('id')).first()

    msg = 'Invalid Username or Password!'

    if fetched_user is not None:
        if fetched_user.username == username and verify_password(old_password, fetched_user.hashed_password):
            fetched_user.hashed_password = get_password_hash(new_password)
            db.commit()
            msg = 'Password Updated!'

    context = {
        'request': request,
        'user': user,
        'msg': msg
    }

    return templates.TemplateResponse("change_password.html", context)
