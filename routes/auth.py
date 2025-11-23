from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

from db import (
    get_current_user, get_user_by_id, get_user_by_email,
    get_db_connection, require_admin, get_user_participations,
    get_hackathon_by_id
)

templates = Jinja2Templates(directory="templates")
router = APIRouter()

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    age: Optional[int] = None
    fio: Optional[str] = None
    telegram_nickname: Optional[str] = None
    basics_knowledge: Optional[str] = None
    city: Optional[str] = None
    team_name: Optional[str] = None
    looking_for_team: bool = False
    hackathons: Optional[str] = ""
    intensives: Optional[str] = ""
    role: str = "user"

# Роуты страниц
@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = get_current_user(request)
    from db import get_all_hackathons
    active_hackathons = get_all_hackathons("ongoing")
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "active_hackathons": active_hackathons
    })

@router.get("/index.html", response_class=HTMLResponse)
async def index(request: Request):
    user = get_current_user(request)
    from db import get_all_hackathons
    active_hackathons = get_all_hackathons("ongoing")
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "active_hackathons": active_hackathons
    })

@router.get("/login.html", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/registration.html", response_class=HTMLResponse)
async def registration_page(request: Request):
    return templates.TemplateResponse("registration.html", {"request": request})

@router.get("/profile.html", response_class=HTMLResponse)
async def profile_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login.html", status_code=302)

    user_participations = get_user_participations(user["id"])
    user_hackathons = []

    for participation in user_participations:
        hackathon = get_hackathon_by_id(participation["hackathon_id"])
        if hackathon:
            user_hackathons.append(hackathon)

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user,
        "user_hackathons": user_hackathons
    })

@router.get("/about.html", response_class=HTMLResponse)
async def about_page(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("about.html", {"request": request, "user": user})

# API роуты
@router.post("/api/login")
async def login(request: Request, credentials: UserLogin):
    email_lower = credentials.email.lower()
    user = get_user_by_email(email_lower)

    if not user or credentials.password != user["password"]:
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    request.session["user_id"] = user["id"]
    request.session["role"] = user["role"]
    request.session["email"] = user["email"]
    request.session["username"] = user["username"]

    user_response = {k: v for k, v in user.items() if k != "password"}
    return {"message": "Успешный вход", "user": user_response}

@router.post("/api/register")
async def register(request: Request, user_data: UserCreate):
    email_lower = user_data.email.lower()
    if get_user_by_email(email_lower):
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")

    if user_data.telegram_nickname:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE telegram_nickname = ?", (user_data.telegram_nickname,))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="Пользователь с таким Telegram nickname уже существует")
        conn.close()

    conn = get_db_connection()
    cursor = conn.cursor()

    new_user = {
        "username": user_data.username,
        "email": user_data.email.lower(),
        "password": user_data.password,
        "age": user_data.age,
        "fio": user_data.fio,
        "telegram_nickname": user_data.telegram_nickname,
        "basics_knowledge": user_data.basics_knowledge,
        "city": user_data.city,
        "team_name": user_data.team_name,
        "looking_for_team": user_data.looking_for_team,
        "hackathons": user_data.hackathons or "",
        "intensives": user_data.intensives or "",
        "role": user_data.role,
        "created_at": datetime.now().isoformat()
    }

    cursor.execute('''
        INSERT INTO Users (
            username, email, password, age, fio, telegram_nickname, 
            basics_knowledge, city, team_name, looking_for_team, 
            hackathons, intensives, role, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        new_user["username"], new_user["email"], new_user["password"],
        new_user["age"], new_user["fio"], new_user["telegram_nickname"],
        new_user["basics_knowledge"], new_user["city"], new_user["team_name"],
        new_user["looking_for_team"], new_user["hackathons"], new_user["intensives"],
        new_user["role"], new_user["created_at"]
    ))

    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    created_user = get_user_by_id(user_id)

    request.session["user_id"] = user_id
    request.session["role"] = new_user["role"]
    request.session["email"] = new_user["email"]
    request.session["username"] = new_user["username"]

    user_response = {k: v for k, v in created_user.items() if k != "password"}
    return {"message": "Регистрация успешна", "user": user_response}

@router.post("/api/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Успешный выход"}

@router.get("/api/user")
async def get_user(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")
    user_response = {k: v for k, v in user.items() if k != "password"}
    return user_response

@router.put("/api/user")
async def update_current_user(request: Request, user_data: dict):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    user_id = user["id"]
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Users WHERE id = ?", (user_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    allowed_fields = ['username', 'age', 'fio', 'telegram_nickname', 'basics_knowledge',
                      'city', 'team_name', 'looking_for_team', 'hackathons', 'intensives']

    update_fields = []
    update_values = []

    for field in allowed_fields:
        if field in user_data:
            update_fields.append(f"{field} = ?")
            update_values.append(user_data[field])

    if not update_fields:
        conn.close()
        raise HTTPException(status_code=400, detail="Нет полей для обновления")

    update_values.append(user_id)
    query = f"UPDATE Users SET {', '.join(update_fields)} WHERE id = ?"

    cursor.execute(query, update_values)
    conn.commit()
    conn.close()

    updated_user = get_user_by_id(user_id)
    user_response = {k: v for k, v in updated_user.items() if k != "password"}
    return {"message": "Профиль обновлен", "user": user_response}
