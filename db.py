import sqlite3
from datetime import datetime
from fastapi import Request, HTTPException, status

# Путь к БД
DB_PATH = "hackathon_hub.db"
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
            alls INTEGER DEFAULT 0,
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
    """Получение пользователя по email (регистронезависимый поиск)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE LOWER(email) = LOWER(?)", (email,))
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
