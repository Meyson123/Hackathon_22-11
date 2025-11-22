from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
from db import (
    init_database, get_current_user, get_user_by_id, get_user_by_email,
    get_db_connection, require_admin, require_expert_in_hackathon,
    get_hackathon_by_id, get_all_hackathons, get_participation,
    get_user_participations, get_hackathon_participants, create_participation,
    update_participation_role, update_reputation, get_reputation_history,
    delete_participation, create_team, get_team_by_id, get_team_by_code,
    get_team_members, get_user_team_in_hackathon, add_member_to_team,
    remove_member_from_team, update_team_name, get_available_teams
)
import sqlite3
import os
from datetime import datetime

app = FastAPI(title="Hackathon Hub")

# Middleware для сессий
app.add_middleware(
    SessionMiddleware,
    secret_key="hackathon-hub-secret-key-2024-change-in-production",
    max_age=86400
)

# Статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# Шаблоны
templates = Jinja2Templates(directory="templates")

# Модели
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


class HackathonCreate(BaseModel):
    name: str
    description: Optional[str] = None
    organizer: Optional[str] = None
    start_date: str
    end_date: str
    duration_hours: Optional[int] = None
    prize_fund: Optional[str] = None
    max_team_size: Optional[int] = None
    status: str = "upcoming"


class ParticipationCreate(BaseModel):
    hackathon_id: int
    role: str  # captain, team_member, free_participant, expert
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    team_description: Optional[str] = None
    team_code: Optional[str] = None


class ReputationUpdate(BaseModel):
    participation_id: int
    new_reputation: int
    reason: Optional[str] = None


class TeamCreate(BaseModel):
    hackathon_id: int
    name: str


class TeamUpdate(BaseModel):
    name: str


# Инициализация БД
init_database()

# ТВОЯ база данных мероприятий для обратной совместимости
HACKATHONS_DB = {
    1: {
        "id": 1,
        "name": "Tech Innovation Challenge 2024",
        "description": "Создайте инновационные решения для будущего технологий",
        "status": "active",
        "start_date": "2024-01-15",
        "end_date": "2024-01-17"
    },
    2: {
        "id": 2,
        "name": "AI Solutions Hackathon",
        "description": "Разработка решений в области искусственного интеллекта",
        "status": "upcoming",
        "start_date": "2024-02-10",
        "end_date": "2024-02-12"
    }
}


# Роуты страниц
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = get_current_user(request)

    # ТВОЯ логика с активными хакатонами
    active_hackathons = [h for h in HACKATHONS_DB.values() if h.get("status") == "active"]

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "active_hackathons": active_hackathons
    })

@app.get("/index.html", response_class=HTMLResponse)
async def index(request: Request):
    user = get_current_user(request)
    active_hackathons = [h for h in HACKATHONS_DB.values() if h.get("status") == "active"]
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "active_hackathons": active_hackathons
    })

@app.get("/login.html", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/registration.html", response_class=HTMLResponse)
async def registration_page(request: Request):
    return templates.TemplateResponse("registration.html", {"request": request})

@app.get("/hackathons.html", response_class=HTMLResponse)
async def hackathons_page(request: Request):
    user = get_current_user(request)

    # ТВОЯ логика с хакатонами + логика друга
    all_hackathons = list(HACKATHONS_DB.values())  # Твои хакатоны
    db_hackathons = get_all_hackathons()  # Хакатоны друга из БД

    return templates.TemplateResponse("hackathons.html", {
        "request": request,
        "user": user,
        "hackathons": all_hackathons + db_hackathons  # Объединяем
    })

@app.get("/about.html", response_class=HTMLResponse)
async def about_page(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("about.html", {"request": request, "user": user})

@app.get("/admin.html", response_class=HTMLResponse)
async def admin_page(request: Request, user=Depends(require_admin)):
    return templates.TemplateResponse("admin.html", {"request": request, "user": user})

@app.get("/profile.html", response_class=HTMLResponse)
async def profile_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login.html", status_code=302)

    # ТВОЯ логика с хакатонами пользователя
    user_hackathons = []
    if user.get("hackathons"):
        try:
            hackathon_ids = [int(x.strip()) for x in user["hackathons"].split(",") if x.strip()]
            user_hackathons = [HACKATHONS_DB.get(hid) for hid in hackathon_ids if HACKATHONS_DB.get(hid)]
        except:
            pass

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user,
        "user_hackathons": user_hackathons
    })

@app.get("/expert.html", response_class=HTMLResponse)
async def expert_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login.html", status_code=302)
    return templates.TemplateResponse("expert.html", {"request": request, "user": user})

# ТВОИ НОВЫЕ РОУТЫ ДЛЯ ХАКАТОНОВ (добавляем к роутам друга)
@app.get("/hackathon/{hackathon_id}")
async def hackathon_main_page(hackathon_id: int, request: Request):
    """Главная страница конкретного хакатона"""
    hackathon = get_hackathon_by_id(hackathon_id)
    if not hackathon:
        # Если нет в БД, проверяем в локальной базе
        hackathon = HACKATHONS_DB.get(hackathon_id)
        if not hackathon:
            raise HTTPException(status_code=404, detail="Хакатон не найден")

    user = get_current_user(request)

    return templates.TemplateResponse("hackathon_main.html", {
        "request": request,
        "hackathon": hackathon,
        "user": user
    })

@app.get("/hackathon/{hackathon_id}/role-check")
async def role_checkup(hackathon_id: int, request: Request):
    """Проверка роли пользователя и редирект на соответствующую страницу"""
    user = get_current_user(request)

    if not user:
        return RedirectResponse(url="/login.html")

    # Проверяем существование хакатона
    hackathon = get_hackathon_by_id(hackathon_id) or HACKATHONS_DB.get(hackathon_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Хакатон не найден")

    role = user["role"].lower()

    if role == "user":
        return RedirectResponse(url=f"/hackathon/{hackathon_id}/user")
    elif role == "captain":
        return RedirectResponse(url=f"/hackathon/{hackathon_id}/captain")
    elif role == "case_holder":
        return RedirectResponse(url=f"/hackathon/{hackathon_id}/case-holder")
    elif role == "admin":
        return RedirectResponse(url=f"/hackathon/{hackathon_id}/admin")
    elif role == "expert":  # Добавляем эксперта из схемы друга
        return RedirectResponse(url=f"/hackathon/{hackathon_id}/expert")

# ТВОИ СТРАНИЦЫ ДЛЯ РАЗНЫХ РОЛЕЙ
@app.get("/hackathon/{hackathon_id}/user")
async def user_hackathon_page(hackathon_id: int, request: Request):
    """Страница участника хакатона"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login.html")

    hackathon = get_hackathon_by_id(hackathon_id) or HACKATHONS_DB.get(hackathon_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Хакатон не найден")

    return templates.TemplateResponse("user_hackathon.html", {
        "request": request,
        "hackathon": hackathon,
        "user_id": user["id"],
        "user_role": user["role"]
    })

@app.get("/hackathon/{hackathon_id}/captain")
async def captain_hackathon_page(hackathon_id: int, request: Request):
    """Страница капитана хакатона"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login.html")

    hackathon = get_hackathon_by_id(hackathon_id) or HACKATHONS_DB.get(hackathon_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Хакатон не найден")

    return templates.TemplateResponse("captain_hackathon.html", {
        "request": request,
        "hackathon": hackathon,
        "user_id": user["id"],
        "user_role": user["role"]
    })

@app.get("/hackathon/{hackathon_id}/case-holder")
async def case_holder_hackathon_page(hackathon_id: int, request: Request):
    """Страница кейсодержателя хакатона"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login.html")

    hackathon = get_hackathon_by_id(hackathon_id) or HACKATHONS_DB.get(hackathon_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Хакатон не найден")

    return templates.TemplateResponse("case_holder_hackathon.html", {
        "request": request,
        "hackathon": hackathon,
        "user_id": user["id"],
        "user_role": user["role"]
    })

@app.get("/hackathon/{hackathon_id}/admin")
async def admin_hackathon_page(hackathon_id: int, request: Request):
    """Страница администратора хакатона"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login.html")

    hackathon = get_hackathon_by_id(hackathon_id) or HACKATHONS_DB.get(hackathon_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Хакатон не найден")

    return templates.TemplateResponse("admin_hackathon.html", {
        "request": request,
        "hackathon": hackathon,
        "user_id": user["id"],
        "user_role": user["role"]
    })

# ТВОИ API для работы с хакатонами (обратная совместимость)
@app.get("/api/hackathons")
async def get_hackathons(request: Request):
    """Получить список всех хакатонов (объединенные)"""
    db_hackathons = get_all_hackathons()
    return list(HACKATHONS_DB.values()) + db_hackathons

@app.get("/api/hackathons/{hackathon_id}")
async def get_hackathon(hackathon_id: int, request: Request):
    """Получить информацию о конкретном хакатоне"""
    hackathon = get_hackathon_by_id(hackathon_id) or HACKATHONS_DB.get(hackathon_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Хакатон не найден")
    return hackathon

@app.post("/api/hackathons/{hackathon_id}/register")
async def register_for_hackathon(hackathon_id: int, request: Request):
    """Регистрация пользователя на хакатон (твоя упрощенная версия)"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    hackathon = get_hackathon_by_id(hackathon_id) or HACKATHONS_DB.get(hackathon_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Хакатон не найден")

    # Обновляем список хакатонов пользователя
    conn = get_db_connection()
    cursor = conn.cursor()

    current_hackathons = user.get("hackathons", "").split(",") if user.get("hackathons") else []
    if str(hackathon_id) not in current_hackathons:
        current_hackathons.append(str(hackathon_id))
        new_hackathons = ",".join(current_hackathons)

        cursor.execute("UPDATE Users SET hackathons = ? WHERE id = ?", (new_hackathons, user["id"]))
        conn.commit()

    conn.close()

    return {"message": f"Успешная регистрация на хакатон '{hackathon['name']}'"}

# API роуты друга (остаются без изменений)
@app.post("/api/login")
async def login(request: Request, credentials: UserLogin):
    # Приводим email к нижнему регистру для поиска
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

@app.post("/api/register")
async def register(request: Request, user_data: UserCreate):
    # Приводим email к нижнему регистру для проверки
    email_lower = user_data.email.lower()
    if get_user_by_email(email_lower):
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")

    # Проверка уникальности telegram_nickname
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
        "email": user_data.email.lower(),  # Сохраняем email в нижнем регистре
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

    # Получаем полные данные пользователя
    created_user = get_user_by_id(user_id)

    request.session["user_id"] = user_id
    request.session["role"] = new_user["role"]
    request.session["email"] = new_user["email"]
    request.session["username"] = new_user["username"]

    user_response = {k: v for k, v in created_user.items() if k != "password"}
    return {"message": "Регистрация успешна", "user": user_response}

@app.post("/api/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Успешный выход"}

@app.get("/api/user")
async def get_user(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")
    user_response = {k: v for k, v in user.items() if k != "password"}
    return user_response

@app.put("/api/user")
async def update_current_user(request: Request, user_data: dict):
    """Обновление данных текущего пользователя"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    user_id = user["id"]
    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверяем существование пользователя
    cursor.execute("SELECT * FROM Users WHERE id = ?", (user_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Обновляем только разрешенные поля (пользователь не может менять email, password, role)
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

    # Возвращаем обновленные данные пользователя
    updated_user = get_user_by_id(user_id)
    user_response = {k: v for k, v in updated_user.items() if k != "password"}
    return {"message": "Профиль обновлен", "user": user_response}

@app.get("/api/users")
async def get_users(request: Request, admin=Depends(require_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Удаляем пароли из ответа
    for user in users:
        user.pop("password", None)

    return users

@app.get("/api/statistics")
async def get_statistics(request: Request, admin=Depends(require_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Общее количество пользователей
    cursor.execute("SELECT COUNT(*) FROM Users")
    total_users = cursor.fetchone()[0]

    # Количество администраторов
    cursor.execute("SELECT COUNT(*) FROM Users WHERE role = 'admin'")
    admin_users = cursor.fetchone()[0]

    # Количество обычных пользователей
    cursor.execute("SELECT COUNT(*) FROM Users WHERE role = 'user'")
    regular_users = cursor.fetchone()[0]

    # Пользователи за текущий месяц
    current_month = datetime.now().strftime("%Y-%m")
    cursor.execute("SELECT COUNT(*) FROM Users WHERE strftime('%Y-%m', created_at) = ?", (current_month,))
    users_this_month = cursor.fetchone()[0]

    # Статистика по городам
    cursor.execute("SELECT city, COUNT(*) FROM Users WHERE city IS NOT NULL GROUP BY city")
    cities_stats = dict(cursor.fetchall())

    # Статистика по поиску команды
    cursor.execute("SELECT COUNT(*) FROM Users WHERE looking_for_team = 1")
    looking_for_team = cursor.fetchone()[0]

    conn.close()

    stats = {
        "totalUsers": total_users,
        "adminUsers": admin_users,
        "regularUsers": regular_users,
        "usersThisMonth": users_this_month,
        "citiesStats": cities_stats,
        "lookingForTeam": looking_for_team
    }
    return stats

@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int, request: Request, admin=Depends(require_admin)):
    # Проверяем, что пользователь не удаляет первого администратора
    if user_id == 1:
        raise HTTPException(status_code=400, detail="Нельзя удалить первого администратора")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверяем существование пользователя
    cursor.execute("SELECT * FROM Users WHERE id = ?", (user_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Удаляем пользователя
    cursor.execute("DELETE FROM Users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    return {"message": "Пользователь удалён"}

@app.put("/api/users/{user_id}")
async def update_user(user_id: int, user_data: dict, request: Request, admin=Depends(require_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверяем существование пользователя
    cursor.execute("SELECT * FROM Users WHERE id = ?", (user_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Обновляем только разрешенные поля
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

    return {"message": "Пользователь обновлен"}

# ========== Hackathons API (код друга) ==========
@app.get("/api/hackathons")
async def get_hackathons_api(request: Request, status_filter: Optional[str] = None):
    """Получение списка хакатонов (версия друга)"""
    hackathons = get_all_hackathons(status_filter)
    return hackathons

@app.get("/api/hackathons/{hackathon_id}")
async def get_hackathon_api(hackathon_id: int, request: Request):
    """Получение информации о хакатоне (версия друга)"""
    hackathon = get_hackathon_by_id(hackathon_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Хакатон не найден")
    return hackathon

@app.post("/api/hackathons")
async def create_hackathon(hackathon_data: HackathonCreate, request: Request, admin=Depends(require_admin)):
    """Создание нового хакатона (только для администраторов)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO Hackathons (name, description, organizer, start_date, end_date, 
                               duration_hours, prize_fund, max_team_size, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        hackathon_data.name, hackathon_data.description, hackathon_data.organizer,
        hackathon_data.start_date, hackathon_data.end_date, hackathon_data.duration_hours,
        hackathon_data.prize_fund, hackathon_data.max_team_size, hackathon_data.status, now
    ))

    hackathon_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {"message": "Хакатон создан", "hackathon_id": hackathon_id}

# ========== Participations API (код друга) ==========
@app.get("/api/participations")
async def get_my_participations(request: Request):
    """Получение всех участий текущего пользователя"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    participations = get_user_participations(user["id"])
    return participations

@app.get("/api/participations/{user_id}/{hackathon_id}")
async def get_participation_info(user_id: int, hackathon_id: int, request: Request):
    """Получение информации об участии"""
    participation = get_participation(user_id, hackathon_id)
    if not participation:
        raise HTTPException(status_code=404, detail="Участие не найдено")
    return participation

@app.post("/api/participations")
async def create_participation_endpoint(participation_data: ParticipationCreate, request: Request):
    """Создание участия в хакатоне"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    # Проверяем валидность роли
    valid_roles = ["captain", "team_member", "free_participant", "expert"]
    if participation_data.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Неверная роль. Допустимые: {', '.join(valid_roles)}")

    # Проверяем существование хакатона
    hackathon = get_hackathon_by_id(participation_data.hackathon_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Хакатон не найден")

    team_id = None

    # Обработка команд
    if participation_data.role == "captain":
        # Капитан создает команду
        if participation_data.team_name:
            try:
                team_id = create_team(
                    participation_data.hackathon_id,
                    participation_data.team_name,
                    user["id"],
                    participation_data.team_description
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail="Капитан должен указать название команды")

    elif participation_data.role == "team_member":
        # Участник присоединяется к команде
        if participation_data.team_code:
            team = get_team_by_code(participation_data.hackathon_id, participation_data.team_code)
            if not team:
                raise HTTPException(status_code=404, detail="Команда не найдена")
            team_id = team["id"]
        elif participation_data.team_id:
            team = get_team_by_id(participation_data.team_id)
            if not team or team["hackathon_id"] != participation_data.hackathon_id:
                raise HTTPException(status_code=404, detail="Команда не найдена")
            team_id = participation_data.team_id
        else:
            # Автоматическое присоединение к доступной команде
            available_teams = get_available_teams(participation_data.hackathon_id)
            if not available_teams or len(available_teams) == 0:
                raise HTTPException(status_code=404, detail="Нет доступных команд для присоединения")
            # Берем первую доступную команду
            team_id = available_teams[0]["id"]

    try:
        participation_id = create_participation(
            user["id"],
            participation_data.hackathon_id,
            participation_data.role,
            team_id
        )
        return {"message": "Участие создано", "participation_id": participation_id, "team_id": team_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/participations/{hackathon_id}")
async def cancel_participation_endpoint(hackathon_id: int, request: Request):
    """Отмена участия в хакатоне"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    # Проверяем существование участия
    participation = get_participation(user["id"], hackathon_id)
    if not participation:
        raise HTTPException(status_code=404, detail="Участие не найдено")

    try:
        delete_participation(user["id"], hackathon_id)
        return {"message": "Участие отменено"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/participations/{user_id}/{hackathon_id}/role")
async def update_participation_role_endpoint(
    user_id: int, hackathon_id: int, role_data: dict, request: Request, admin=Depends(require_admin)
):
    """Обновление роли участия (только для администраторов)"""
    new_role = role_data.get("role")
    if not new_role:
        raise HTTPException(status_code=400, detail="Роль не указана")

    valid_roles = ["captain", "team_member", "free_participant", "expert"]
    if new_role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Неверная роль. Допустимые: {', '.join(valid_roles)}")

    update_participation_role(user_id, hackathon_id, new_role)
    return {"message": "Роль обновлена"}

# ========== Reputation API (код друга) ==========
@app.get("/api/hackathons/{hackathon_id}/participants")
async def get_hackathon_participants_endpoint(hackathon_id: int, request: Request):
    """Получение списка участников хакатона"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    # Проверяем, что пользователь является экспертом или администратором
    try:
        require_expert_in_hackathon(request, hackathon_id)
    except HTTPException:
        if user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Требуются права эксперта")

    participants = get_hackathon_participants(hackathon_id)
    return participants

@app.put("/api/reputation")
async def update_reputation_endpoint(reputation_data: ReputationUpdate, request: Request):
    """Обновление репутации (только для экспертов)"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    # Получаем информацию об участии
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, h.id as hackathon_id FROM Participations p
        JOIN Hackathons h ON p.hackathon_id = h.id
        WHERE p.id = ?
    ''', (reputation_data.participation_id,))
    participation = cursor.fetchone()
    conn.close()

    if not participation:
        raise HTTPException(status_code=404, detail="Участие не найдено")

    # Проверяем права эксперта
    try:
        require_expert_in_hackathon(request, participation["hackathon_id"])
    except HTTPException:
        if user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Требуются права эксперта в данном хакатоне")

    # Обновляем репутацию
    update_reputation(
        reputation_data.participation_id,
        reputation_data.new_reputation,
        user["id"],
        reputation_data.reason
    )

    return {"message": "Репутация обновлена"}

@app.get("/api/reputation/history/{participation_id}")
async def get_reputation_history_endpoint(participation_id: int, request: Request):
    """Получение истории изменений репутации"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    # Получаем информацию об участии
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, h.id as hackathon_id FROM Participations p
        JOIN Hackathons h ON p.hackathon_id = h.id
        WHERE p.id = ?
    ''', (participation_id,))
    participation = cursor.fetchone()
    conn.close()

    if not participation:
        raise HTTPException(status_code=404, detail="Участие не найдено")

    # Пользователь может видеть свою историю, эксперты и админы - любую
    if participation["user_id"] != user["id"]:
        try:
            require_expert_in_hackathon(request, participation["hackathon_id"])
        except HTTPException:
            if user["role"] != "admin":
                raise HTTPException(status_code=403, detail="Нет доступа к этой истории")

    history = get_reputation_history(participation_id)
    return history

# ========== Teams API (код друга) ==========
@app.get("/api/teams/{team_id}")
async def get_team_info(team_id: int, request: Request):
    """Получение информации о команде"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    team = get_team_by_id(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Команда не найдена")

    # Проверяем, что пользователь участвует в этом хакатоне
    participation = get_participation(user["id"], team["hackathon_id"])
    if not participation and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Нет доступа к этой команде")

    members = get_team_members(team_id)
    team_data = dict(team)
    team_data["members"] = members

    return team_data

@app.get("/api/hackathons/{hackathon_id}/teams")
async def get_available_teams_endpoint(hackathon_id: int, request: Request):
    """Получение доступных команд в хакатоне"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    teams = get_available_teams(hackathon_id)
    return teams

@app.post("/api/teams")
async def create_team_endpoint(team_data: TeamCreate, request: Request):
    """Создание команды"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    # Проверяем, что пользователь участвует в хакатоне как капитан
    participation = get_participation(user["id"], team_data.hackathon_id)
    if not participation or participation["role"] != "captain":
        raise HTTPException(status_code=403, detail="Только капитаны могут создавать команды")

    try:
        team_id = create_team(team_data.hackathon_id, team_data.name, user["id"])

        # Обновляем участие, чтобы связать с командой
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('''
            UPDATE Participations SET team_id = ?, updated_at = ?
            WHERE user_id = ? AND hackathon_id = ?
        ''', (team_id, now, user["id"], team_data.hackathon_id))
        conn.commit()
        conn.close()

        return {"message": "Команда создана", "team_id": team_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/teams/{team_id}")
async def update_team_endpoint(team_id: int, team_data: TeamUpdate, request: Request):
    """Обновление команды (только капитан)"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    team = get_team_by_id(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Команда не найдена")

    # Проверяем, что пользователь - капитан команды
    if team["captain_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Только капитан может редактировать команду")

    try:
        update_team_name(team_id, team_data.name, team["hackathon_id"])
        return {"message": "Команда обновлена"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/teams/{team_id}/members")
async def add_team_member_endpoint(team_id: int, request: Request):
    """Добавление участника в команду"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    team = get_team_by_id(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Команда не найдена")

    # Проверяем, что пользователь участвует в этом хакатоне
    participation = get_participation(user["id"], team["hackathon_id"])
    if not participation:
        raise HTTPException(status_code=403, detail="Вы не участвуете в этом хакатоне")

    # Проверяем, что пользователь - капитан или участник команды
    if participation["role"] != "team_member" and participation["role"] != "captain":
        raise HTTPException(status_code=403, detail="Только участники команды могут присоединяться")

    try:
        add_member_to_team(user["id"], team["hackathon_id"], team_id)
        return {"message": "Участник добавлен в команду"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/teams/{team_id}/members")
async def remove_team_member_endpoint(team_id: int, user_id: Optional[int] = None, request: Request = None):
    """Удаление участника из команды"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    team = get_team_by_id(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Команда не найдена")

    # Используем переданный user_id или текущего пользователя
    target_user_id = user_id if user_id else user["id"]

    # Проверяем, что пользователь - капитан или сам участник
    if team["captain_id"] != user["id"]:
        if target_user_id != user["id"]:
            if user["role"] != "admin":
                raise HTTPException(status_code=403, detail="Только капитан может удалять участников")

    try:
        remove_member_from_team(target_user_id, team["hackathon_id"])
        return {"message": "Участник удален из команды"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/team.html", response_class=HTMLResponse)
async def team_page(request: Request):
    """Страница команды"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login.html", status_code=302)

    # Получаем параметры из query string
    hackathon_id_param = request.query_params.get("hackathon_id")
    team_id_param = request.query_params.get("team_id")

    if not hackathon_id_param:
        raise HTTPException(status_code=400, detail="hackathon_id обязателен")

    try:
        hackathon_id = int(hackathon_id_param)
        team_id = int(team_id_param) if team_id_param else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат параметров")

    # Если team_id не указан, пытаемся найти команду пользователя
    if not team_id:
        team = get_user_team_in_hackathon(user["id"], hackathon_id)
        if team:
            team_id = team["id"]
        else:
            raise HTTPException(status_code=404, detail="Команда не найдена")

    team = get_team_by_id(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Команда не найдена")

    # Проверяем доступ
    participation = get_participation(user["id"], hackathon_id)
    if not participation and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Нет доступа к этой команде")

    members = get_team_members(team_id)
    hackathon = get_hackathon_by_id(hackathon_id)

    return templates.TemplateResponse("team.html", {
        "request": request,
        "user": user,
        "team": team,
        "members": members,
        "hackathon": hackathon,
        "is_captain": team["captain_id"] == user["id"]
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
