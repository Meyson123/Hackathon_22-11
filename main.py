from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
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

# Путь к БД
DB_PATH = "hackathon_hub.db"

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

def init_database():
    """Инициализация базы данных SQLite с новой схемой"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Создание таблицы пользователей с новой схемой
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            age INTEGER,
            fio TEXT,
            telegram_nickname TEXT UNIQUE,
            balls INTEGER DEFAULT 0,
            basics_knowledge TEXT,
            city TEXT,
            team_name TEXT,
            looking_for_team BOOLEAN DEFAULT FALSE,
            hackathons TEXT DEFAULT '',
            intensives TEXT DEFAULT '',
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL
        )
    ''')

    # Создание администратора по умолчанию, если его нет
    cursor.execute("SELECT * FROM Users WHERE role='admin'")
    if not cursor.fetchone():
        admin_user = {
            "username": "admin",
            "email": "admin@example.com",
            "password": "admin123",  # Пароль в открытом виде
            "fio": "Administrator",
            "telegram_nickname": "@admin",
            "basics_knowledge": "management,organization",
            "city": "Moscow",
            "role": "admin",
            "created_at": datetime.now().isoformat()
        }
        cursor.execute('''
            INSERT INTO Users (username, email, password, fio, telegram_nickname, basics_knowledge, city, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            admin_user["username"], admin_user["email"], admin_user["password"],
            admin_user["fio"], admin_user["telegram_nickname"], admin_user["basics_knowledge"],
            admin_user["city"], admin_user["role"], admin_user["created_at"]
        ))

    conn.commit()
    conn.close()

# Вспомогательные функции для работы с БД
def get_db_connection():
    """Создание соединения с базой данных"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
    return conn

def get_user_by_email(email: str):
    """Получение пользователя по email"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_id(user_id: int):
    """Получение пользователя по ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def get_current_user(request: Request):
    """Получение текущего пользователя из сессии"""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(user_id)

def require_admin(request: Request):
    """Проверка прав администратора"""
    user = get_current_user(request)
    if not user or user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора"
        )
    return user

# Инициализация БД
init_database()

# Роуты страниц
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/login.html", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/registration.html", response_class=HTMLResponse)
async def registration_page(request: Request):
    return templates.TemplateResponse("registration.html", {"request": request})

@app.get("/hackathons.html", response_class=HTMLResponse)
async def hackathons_page(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("hackathons.html", {"request": request, "user": user})

@app.get("/about.html", response_class=HTMLResponse)
async def about_page(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("about.html", {"request": request, "user": user})

@app.get("/admin.html", response_class=HTMLResponse)
async def admin_page(request: Request, user=Depends(require_admin)):
    return templates.TemplateResponse("admin.html", {"request": request, "user": user})

# API роуты
@app.post("/api/login")
async def login(request: Request, credentials: UserLogin):
    user = get_user_by_email(credentials.email)
    if not user or credentials.password != user["password"]:  # Прямое сравнение паролей
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    request.session["user_id"] = user["id"]
    request.session["role"] = user["role"]
    request.session["email"] = user["email"]
    request.session["username"] = user["username"]

    user_response = {k: v for k, v in user.items() if k != "password"}
    return {"message": "Успешный вход", "user": user_response}

@app.post("/api/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Успешный выход"}

@app.post("/api/register")
async def register(request: Request, user_data: UserCreate):
    if get_user_by_email(user_data.email):
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
        "email": user_data.email,
        "password": user_data.password,  # Пароль сохраняется в открытом виде
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

@app.get("/api/user")
async def get_user(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")
    user_response = {k: v for k, v in user.items() if k != "password"}
    return user_response

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
