import sqlite3
from datetime import datetime
from fastapi import Request, HTTPException, status
from typing import Optional, List

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
            basics_knowledge TEXT,
            city TEXT,
            team_name TEXT,
            looking_for_team BOOLEAN DEFAULT FALSE,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL
        )
    ''')

    # Создание таблицы хакатонов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Hackathons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            organizer TEXT,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            duration_hours INTEGER,
            prize_fund TEXT,
            max_team_size INTEGER,
            status TEXT NOT NULL DEFAULT 'upcoming',
            created_at TEXT NOT NULL
        )
    ''')

    # Создание таблицы команд
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hackathon_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            captain_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (hackathon_id) REFERENCES Hackathons(id) ON DELETE CASCADE,
            FOREIGN KEY (captain_id) REFERENCES Users(id) ON DELETE CASCADE,
            UNIQUE(hackathon_id, name)
        )
    ''')

    # Создание таблицы участий (Participation) - связывает пользователя, хакатон, роль и репутацию
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Participations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            hackathon_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            team_id INTEGER,
            reputation INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
            FOREIGN KEY (hackathon_id) REFERENCES Hackathons(id) ON DELETE CASCADE,
            FOREIGN KEY (team_id) REFERENCES Teams(id) ON DELETE SET NULL,
            UNIQUE(user_id, hackathon_id)
        )
    ''')

    # Создание таблицы истории изменений репутации
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ReputationHistory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participation_id INTEGER NOT NULL,
            old_reputation INTEGER NOT NULL,
            new_reputation INTEGER NOT NULL,
            changed_by INTEGER NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (participation_id) REFERENCES Participations(id) ON DELETE CASCADE,
            FOREIGN KEY (changed_by) REFERENCES Users(id) ON DELETE CASCADE
        )
    ''')

    # Создание таблицы проектов/презентаций
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hackathon_id INTEGER NOT NULL,
            team_id INTEGER,
            participation_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            presentation_url TEXT,
            area_topic TEXT,
            status TEXT DEFAULT 'draft',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (hackathon_id) REFERENCES Hackathons(id) ON DELETE CASCADE,
            FOREIGN KEY (team_id) REFERENCES Teams(id) ON DELETE SET NULL,
            FOREIGN KEY (participation_id) REFERENCES Participations(id) ON DELETE CASCADE
        )
    ''')

    # Создание таблицы областей экспертизы экспертов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ExpertAreas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expert_id INTEGER NOT NULL,
            hackathon_id INTEGER NOT NULL,
            area_topic TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (expert_id) REFERENCES Users(id) ON DELETE CASCADE,
            FOREIGN KEY (hackathon_id) REFERENCES Hackathons(id) ON DELETE CASCADE,
            UNIQUE(expert_id, hackathon_id, area_topic)
        )
    ''')

    # Создание таблицы комментариев экспертов к проектам
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ProjectComments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            expert_id INTEGER NOT NULL,
            comment TEXT NOT NULL,
            rating INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES Projects(id) ON DELETE CASCADE,
            FOREIGN KEY (expert_id) REFERENCES Users(id) ON DELETE CASCADE
        )
    ''')

    # Создание таблицы аудита действий экспертов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ExpertAuditLog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expert_id INTEGER NOT NULL,
            hackathon_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            target_type TEXT,
            target_id INTEGER,
            details TEXT,
            ip_address TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (expert_id) REFERENCES Users(id) ON DELETE CASCADE,
            FOREIGN KEY (hackathon_id) REFERENCES Hackathons(id) ON DELETE CASCADE
        )
    ''')

    # Создание таблицы вебинаров/семинаров
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Webinars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            speaker TEXT NOT NULL,
            date_time TEXT NOT NULL,
            duration_hours REAL,
            location TEXT DEFAULT 'Онлайн',
            max_participants INTEGER,
            status TEXT NOT NULL DEFAULT 'upcoming',
            created_at TEXT NOT NULL
        )
    ''')

    # Создание таблицы интенсивных курсов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            instructor TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            hours_per_week INTEGER,
            max_students INTEGER,
            status TEXT NOT NULL DEFAULT 'upcoming',
            certificate_available BOOLEAN DEFAULT FALSE,
            created_at TEXT NOT NULL
        )
    ''')

    # Создание таблицы регистраций на вебинары
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS WebinarRegistrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            webinar_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
            FOREIGN KEY (webinar_id) REFERENCES Webinars(id) ON DELETE CASCADE,
            UNIQUE(user_id, webinar_id)
        )
    ''')

    # Создание таблицы регистраций на курсы
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS CourseRegistrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES Courses(id) ON DELETE CASCADE,
            UNIQUE(user_id, course_id)
        )
    ''')

    # Добавляем примеры хакатонов для тестирования (если их нет)
    cursor.execute("SELECT COUNT(*) FROM Hackathons")
    if cursor.fetchone()[0] == 0:
        sample_hackathons = [
            {
                "name": "Tech Innovation Challenge 2024",
                "description": "Создайте инновационные решения для будущего технологий. Фокус на AI, IoT и блокчейн.",
                "organizer": "TechCorp",
                "start_date": "2024-03-15T00:00:00",
                "end_date": "2024-03-17T00:00:00",
                "duration_hours": 48,
                "prize_fund": "$50,000",
                "max_team_size": 5,
                "status": "upcoming"
            },
            {
                "name": "GreenTech Hackathon",
                "description": "Разработайте экологичные технологические решения для устойчивого будущего.",
                "organizer": "EcoSolutions",
                "start_date": "2024-03-22T00:00:00",
                "end_date": "2024-03-24T00:00:00",
                "duration_hours": 36,
                "prize_fund": "$30,000",
                "max_team_size": 4,
                "status": "upcoming"
            },
            {
                "name": "Web Development Marathon",
                "description": "Создайте современные веб-приложения с использованием последних технологий.",
                "organizer": "WebDev Academy",
                "start_date": "2024-03-10T00:00:00",
                "end_date": "2024-03-12T00:00:00",
                "duration_hours": 48,
                "prize_fund": "$25,000",
                "max_team_size": 4,
                "status": "ongoing"
            }
        ]

        for hackathon in sample_hackathons:
            cursor.execute('''
                INSERT INTO Hackathons (name, description, organizer, start_date, end_date, 
                                       duration_hours, prize_fund, max_team_size, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                hackathon["name"], hackathon["description"], hackathon["organizer"],
                hackathon["start_date"], hackathon["end_date"], hackathon["duration_hours"],
                hackathon["prize_fund"], hackathon["max_team_size"], hackathon["status"],
                datetime.now().isoformat()
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

def require_expert_in_hackathon(request: Request, hackathon_id: int):
    """Проверка, что пользователь является экспертом в данном хакатоне"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация"
        )

    # Администраторы имеют все права
    if user["role"] == "admin":
        return user

    # Проверяем, является ли пользователь экспертом в этом хакатоне
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM Participations 
        WHERE user_id = ? AND hackathon_id = ? AND role = 'expert'
    ''', (user["id"], hackathon_id))
    participation = cursor.fetchone()
    conn.close()

    if not participation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права эксперта в данном хакатоне"
        )
    return user

# Функции для работы с хакатонами
def get_hackathon_by_id(hackathon_id: int):
    """Получение хакатона по ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Hackathons WHERE id = ?", (hackathon_id,))
    hackathon = cursor.fetchone()
    conn.close()
    return dict(hackathon) if hackathon else None

def get_all_hackathons(status_filter: str = None):
    """Получение всех хакатонов с опциональной фильтрацией по статусу"""
    conn = get_db_connection()
    cursor = conn.cursor()
    if status_filter:
        cursor.execute("SELECT * FROM Hackathons WHERE status = ? ORDER BY start_date DESC", (status_filter,))
    else:
        cursor.execute("SELECT * FROM Hackathons ORDER BY start_date DESC")
    hackathons = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return hackathons

# Функции для работы с участиями
def get_participation(user_id: int, hackathon_id: int):
    """Получение участия пользователя в хакатоне"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, u.username, u.fio, u.email, h.name as hackathon_name,
               t.name as team_name
        FROM Participations p
        JOIN Users u ON p.user_id = u.id
        JOIN Hackathons h ON p.hackathon_id = h.id
        LEFT JOIN Teams t ON p.team_id = t.id
        WHERE p.user_id = ? AND p.hackathon_id = ?
    ''', (user_id, hackathon_id))
    participation = cursor.fetchone()
    conn.close()
    return dict(participation) if participation else None

def get_user_participations(user_id: int):
    """Получение всех участий пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, h.name as hackathon_name, h.status as hackathon_status,
               h.start_date, h.end_date, t.name as team_name, t.id as team_id
        FROM Participations p
        JOIN Hackathons h ON p.hackathon_id = h.id
        LEFT JOIN Teams t ON p.team_id = t.id
        WHERE p.user_id = ?
        ORDER BY h.start_date DESC
    ''', (user_id,))
    participations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return participations

def get_hackathon_participants(hackathon_id: int):
    """Получение всех участников хакатона"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, u.username, u.fio, u.email, u.telegram_nickname
        FROM Participations p
        JOIN Users u ON p.user_id = u.id
        WHERE p.hackathon_id = ?
        ORDER BY p.reputation DESC, u.username
    ''', (hackathon_id,))
    participants = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return participants

def create_participation(user_id: int, hackathon_id: int, role: str, team_id: int = None):
    """Создание участия пользователя в хакатоне"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверяем, не существует ли уже участие
    cursor.execute('''
        SELECT * FROM Participations WHERE user_id = ? AND hackathon_id = ?
    ''', (user_id, hackathon_id))
    if cursor.fetchone():
        conn.close()
        raise ValueError("Пользователь уже участвует в этом хакатоне")

    now = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO Participations (user_id, hackathon_id, role, team_id, reputation, created_at, updated_at)
        VALUES (?, ?, ?, ?, 0, ?, ?)
    ''', (user_id, hackathon_id, role, team_id, now, now))

    participation_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return participation_id

def delete_participation(user_id: int, hackathon_id: int):
    """Удаление участия пользователя в хакатоне"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверяем, является ли пользователь капитаном команды
    cursor.execute('''
        SELECT p.team_id, t.captain_id FROM Participations p
        LEFT JOIN Teams t ON p.team_id = t.id
        WHERE p.user_id = ? AND p.hackathon_id = ?
    ''', (user_id, hackathon_id))
    result = cursor.fetchone()

    if result and result[0] and result[1] == user_id:
        # Если пользователь - капитан, удаляем команду (каскадное удаление)
        cursor.execute('DELETE FROM Teams WHERE id = ?', (result[0],))

    cursor.execute('''
        DELETE FROM Participations WHERE user_id = ? AND hackathon_id = ?
    ''', (user_id, hackathon_id))

    conn.commit()
    conn.close()

# Функции для работы с командами
def create_team(hackathon_id: int, name: str, captain_id: int, description: str = None):
    """Создание команды"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверяем уникальность имени команды в рамках хакатона
    cursor.execute('''
        SELECT * FROM Teams WHERE hackathon_id = ? AND name = ?
    ''', (hackathon_id, name))
    if cursor.fetchone():
        conn.close()
        raise ValueError("Команда с таким именем уже существует в этом хакатоне")

    now = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO Teams (hackathon_id, name, description, captain_id, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (hackathon_id, name, description, captain_id, now))

    team_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return team_id

def get_team_by_id(team_id: int):
    """Получение команды по ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.*, u.username as captain_username, u.fio as captain_fio, h.name as hackathon_name
        FROM Teams t
        JOIN Users u ON t.captain_id = u.id
        JOIN Hackathons h ON t.hackathon_id = h.id
        WHERE t.id = ?
    ''', (team_id,))
    team = cursor.fetchone()
    conn.close()
    return dict(team) if team else None

def get_team_by_code(hackathon_id: int, team_code: str):
    """Получение команды по коду (ID) в рамках хакатона"""
    try:
        team_id = int(team_code)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM Teams WHERE id = ? AND hackathon_id = ?
        ''', (team_id, hackathon_id))
        team = cursor.fetchone()
        conn.close()
        return dict(team) if team else None
    except ValueError:
        return None

def get_team_members(team_id: int):
    """Получение всех участников команды"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, u.username, u.fio, u.email, u.telegram_nickname
        FROM Participations p
        JOIN Users u ON p.user_id = u.id
        WHERE p.team_id = ?
        ORDER BY 
            CASE p.role 
                WHEN 'captain' THEN 1
                WHEN 'team_member' THEN 2
                ELSE 3
            END,
            u.username
    ''', (team_id,))
    members = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return members

def get_user_team_in_hackathon(user_id: int, hackathon_id: int):
    """Получение команды пользователя в хакатоне"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.* FROM Teams t
        JOIN Participations p ON t.id = p.team_id
        WHERE p.user_id = ? AND p.hackathon_id = ?
    ''', (user_id, hackathon_id))
    team = cursor.fetchone()
    conn.close()
    return dict(team) if team else None

def add_member_to_team(user_id: int, hackathon_id: int, team_id: int):
    """Добавление участника в команду"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверяем участие
    cursor.execute('''
        SELECT * FROM Participations WHERE user_id = ? AND hackathon_id = ?
    ''', (user_id, hackathon_id))
    participation = cursor.fetchone()
    if not participation:
        conn.close()
        raise ValueError("Пользователь не участвует в этом хакатоне")

    # Проверяем размер команды
    cursor.execute('''
        SELECT h.max_team_size, COUNT(p.id) as current_size
        FROM Hackathons h
        LEFT JOIN Participations p ON p.team_id = ?
        WHERE h.id = ?
        GROUP BY h.id
    ''', (team_id, hackathon_id))
    result = cursor.fetchone()

    if result and result[0]:
        current_size = result[1] or 0
        if current_size >= result[0]:
            conn.close()
            raise ValueError("Команда достигла максимального размера")

    # Обновляем участие
    now = datetime.now().isoformat()
    cursor.execute('''
        UPDATE Participations 
        SET team_id = ?, updated_at = ?
        WHERE user_id = ? AND hackathon_id = ?
    ''', (team_id, now, user_id, hackathon_id))

    conn.commit()
    conn.close()

def remove_member_from_team(user_id: int, hackathon_id: int):
    """Удаление участника из команды"""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute('''
        UPDATE Participations 
        SET team_id = NULL, updated_at = ?
        WHERE user_id = ? AND hackathon_id = ?
    ''', (now, user_id, hackathon_id))
    conn.commit()
    conn.close()

def update_team_name(team_id: int, new_name: str, hackathon_id: int):
    """Обновление названия команды"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверяем уникальность
    cursor.execute('''
        SELECT * FROM Teams WHERE hackathon_id = ? AND name = ? AND id != ?
    ''', (hackathon_id, new_name, team_id))
    if cursor.fetchone():
        conn.close()
        raise ValueError("Команда с таким именем уже существует")

    cursor.execute('''
        UPDATE Teams SET name = ? WHERE id = ?
    ''', (new_name, team_id))

    conn.commit()
    conn.close()

def get_available_teams(hackathon_id: int):
    """Получение команд с доступными местами"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.*, 
               COUNT(p.id) as member_count,
               h.max_team_size,
               u.username as captain_username,
               u.fio as captain_fio
        FROM Teams t
        JOIN Hackathons h ON t.hackathon_id = h.id
        JOIN Users u ON t.captain_id = u.id
        LEFT JOIN Participations p ON t.id = p.team_id
        WHERE t.hackathon_id = ?
        GROUP BY t.id
        HAVING member_count < COALESCE(h.max_team_size, 999) OR h.max_team_size IS NULL
        ORDER BY t.name
    ''', (hackathon_id,))
    teams = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return teams

def update_participation_role(user_id: int, hackathon_id: int, new_role: str):
    """Обновление роли пользователя в хакатоне"""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute('''
        UPDATE Participations 
        SET role = ?, updated_at = ?
        WHERE user_id = ? AND hackathon_id = ?
    ''', (new_role, now, user_id, hackathon_id))
    conn.commit()
    conn.close()

def update_reputation(participation_id: int, new_reputation: int, changed_by: int, reason: str = None):
    """Обновление репутации с сохранением истории"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Получаем текущую репутацию
    cursor.execute("SELECT reputation FROM Participations WHERE id = ?", (participation_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        raise ValueError("Участие не найдено")

    old_reputation = result[0]

    # Обновляем репутацию
    now = datetime.now().isoformat()
    cursor.execute('''
        UPDATE Participations 
        SET reputation = ?, updated_at = ?
        WHERE id = ?
    ''', (new_reputation, now, participation_id))

    # Сохраняем в историю
    cursor.execute('''
        INSERT INTO ReputationHistory (participation_id, old_reputation, new_reputation, changed_by, reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (participation_id, old_reputation, new_reputation, changed_by, reason, now))

    conn.commit()
    conn.close()

def get_reputation_history(participation_id: int):
    """Получение истории изменений репутации"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT rh.*, u.username as changed_by_username, u.fio as changed_by_fio
        FROM ReputationHistory rh
        JOIN Users u ON rh.changed_by = u.id
        WHERE rh.participation_id = ?
        ORDER BY rh.created_at DESC
    ''', (participation_id,))
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return history

# ========== Функции для работы с проектами ==========
def get_projects_by_hackathon(hackathon_id: int, area_topic: str = None):
    """Получение проектов хакатона, опционально фильтрованных по области"""
    conn = get_db_connection()
    cursor = conn.cursor()
    if area_topic:
        cursor.execute('''
            SELECT p.*, t.name as team_name, u.username, u.fio, part.role
            FROM Projects p
            LEFT JOIN Teams t ON p.team_id = t.id
            JOIN Participations part ON p.participation_id = part.id
            JOIN Users u ON part.user_id = u.id
            WHERE p.hackathon_id = ? AND p.area_topic = ?
            ORDER BY p.created_at DESC
        ''', (hackathon_id, area_topic))
    else:
        cursor.execute('''
            SELECT p.*, t.name as team_name, u.username, u.fio, part.role
            FROM Projects p
            LEFT JOIN Teams t ON p.team_id = t.id
            JOIN Participations part ON p.participation_id = part.id
            JOIN Users u ON part.user_id = u.id
            WHERE p.hackathon_id = ?
            ORDER BY p.created_at DESC
        ''', (hackathon_id,))
    projects = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return projects

def get_project_by_id(project_id: int):
    """Получение проекта по ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, t.name as team_name, u.username, u.fio, part.role
        FROM Projects p
        LEFT JOIN Teams t ON p.team_id = t.id
        JOIN Participations part ON p.participation_id = part.id
        JOIN Users u ON part.user_id = u.id
        WHERE p.id = ?
    ''', (project_id,))
    project = cursor.fetchone()
    conn.close()
    return dict(project) if project else None

# ========== Функции для работы с областями экспертизы ==========
def get_expert_areas(expert_id: int, hackathon_id: int):
    """Получение областей экспертизы эксперта в хакатоне"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM ExpertAreas
        WHERE expert_id = ? AND hackathon_id = ?
        ORDER BY area_topic
    ''', (expert_id, hackathon_id))
    areas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return areas

def add_expert_area(expert_id: int, hackathon_id: int, area_topic: str):
    """Добавление области экспертизы эксперту"""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    try:
        cursor.execute('''
            INSERT INTO ExpertAreas (expert_id, hackathon_id, area_topic, created_at)
            VALUES (?, ?, ?, ?)
        ''', (expert_id, hackathon_id, area_topic, now))
        conn.commit()
        area_id = cursor.lastrowid
        conn.close()
        return area_id
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError("Эта область уже назначена эксперту")

def remove_expert_area(expert_id: int, hackathon_id: int, area_topic: str):
    """Удаление области экспертизы"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM ExpertAreas
        WHERE expert_id = ? AND hackathon_id = ? AND area_topic = ?
    ''', (expert_id, hackathon_id, area_topic))
    conn.commit()
    conn.close()

# ========== Функции для работы с комментариями ==========
def get_project_comments(project_id: int):
    """Получение комментариев к проекту"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*, u.username, u.fio
        FROM ProjectComments c
        JOIN Users u ON c.expert_id = u.id
        WHERE c.project_id = ?
        ORDER BY c.created_at DESC
    ''', (project_id,))
    comments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return comments

def add_project_comment(project_id: int, expert_id: int, comment: str, rating: int = None):
    """Добавление комментария к проекту"""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO ProjectComments (project_id, expert_id, comment, rating, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (project_id, expert_id, comment, rating, now, now))
    comment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return comment_id

def update_project_comment(comment_id: int, comment: str, rating: int = None):
    """Обновление комментария"""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute('''
        UPDATE ProjectComments
        SET comment = ?, rating = ?, updated_at = ?
        WHERE id = ?
    ''', (comment, rating, now, comment_id))
    conn.commit()
    conn.close()

# ========== Функции для аудита ==========
def log_expert_action(expert_id: int, hackathon_id: int, action_type: str, 
                     target_type: str = None, target_id: int = None, 
                     details: str = None, ip_address: str = None):
    """Логирование действия эксперта"""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO ExpertAuditLog (expert_id, hackathon_id, action_type, target_type, target_id, details, ip_address, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (expert_id, hackathon_id, action_type, target_type, target_id, details, ip_address, now))
    conn.commit()
    conn.close()

# ========== Функции для работы с вебинарами ==========
def get_all_webinars(status_filter: Optional[str] = None):
    """Получение всех вебинаров"""
    conn = get_db_connection()
    cursor = conn.cursor()
    if status_filter:
        cursor.execute('''
            SELECT * FROM Webinars
            WHERE status = ?
            ORDER BY date_time ASC
        ''', (status_filter,))
    else:
        cursor.execute('''
            SELECT * FROM Webinars
            ORDER BY date_time ASC
        ''')
    webinars = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return webinars

def get_webinar_by_id(webinar_id: int):
    """Получение вебинара по ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Webinars WHERE id = ?', (webinar_id,))
    webinar = cursor.fetchone()
    conn.close()
    return dict(webinar) if webinar else None

def create_webinar(name: str, description: str, speaker: str, date_time: str, 
                   duration_hours: Optional[float] = None, location: str = "Онлайн",
                   max_participants: Optional[int] = None, status: str = "upcoming"):
    """Создание вебинара"""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO Webinars (name, description, speaker, date_time, duration_hours, 
                             location, max_participants, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, description, speaker, date_time, duration_hours, location, 
          max_participants, status, now))
    webinar_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return webinar_id

def register_for_webinar(user_id: int, webinar_id: int):
    """Регистрация пользователя на вебинар"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Проверяем, не зарегистрирован ли уже
    cursor.execute('''
        SELECT * FROM WebinarRegistrations
        WHERE user_id = ? AND webinar_id = ?
    ''', (user_id, webinar_id))
    if cursor.fetchone():
        conn.close()
        raise ValueError("Вы уже зарегистрированы на этот вебинар")
    
    # Проверяем максимальное количество участников
    cursor.execute('SELECT max_participants FROM Webinars WHERE id = ?', (webinar_id,))
    result = cursor.fetchone()
    if result and result[0]:
        cursor.execute('SELECT COUNT(*) FROM WebinarRegistrations WHERE webinar_id = ?', (webinar_id,))
        current_count = cursor.fetchone()[0]
        if current_count >= result[0]:
            conn.close()
            raise ValueError("Достигнуто максимальное количество участников")
    
    now = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO WebinarRegistrations (user_id, webinar_id, created_at)
        VALUES (?, ?, ?)
    ''', (user_id, webinar_id, now))
    registration_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return registration_id

def get_user_webinar_registrations(user_id: int):
    """Получение всех регистраций пользователя на вебинары"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT w.*, wr.created_at as registration_date
        FROM Webinars w
        JOIN WebinarRegistrations wr ON w.id = wr.webinar_id
        WHERE wr.user_id = ?
        ORDER BY w.date_time ASC
    ''', (user_id,))
    registrations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return registrations

def cancel_webinar_registration(user_id: int, webinar_id: int):
    """Отмена регистрации на вебинар"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM WebinarRegistrations
        WHERE user_id = ? AND webinar_id = ?
    ''', (user_id, webinar_id))
    conn.commit()
    deleted = cursor.rowcount
    conn.close()
    if deleted == 0:
        raise ValueError("Регистрация не найдена")
    return True

def is_user_registered_for_webinar(user_id: int, webinar_id: int):
    """Проверка, зарегистрирован ли пользователь на вебинар"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM WebinarRegistrations
        WHERE user_id = ? AND webinar_id = ?
    ''', (user_id, webinar_id))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_webinar_participant_count(webinar_id: int):
    """Получение количества зарегистрированных участников вебинара"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM WebinarRegistrations WHERE webinar_id = ?', (webinar_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

# ========== Функции для работы с курсами ==========
def get_all_courses(status_filter: Optional[str] = None):
    """Получение всех курсов"""
    conn = get_db_connection()
    cursor = conn.cursor()
    if status_filter:
        cursor.execute('''
            SELECT * FROM Courses
            WHERE status = ?
            ORDER BY start_date ASC
        ''', (status_filter,))
    else:
        cursor.execute('''
            SELECT * FROM Courses
            ORDER BY start_date ASC
        ''')
    courses = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return courses

def get_course_by_id(course_id: int):
    """Получение курса по ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Courses WHERE id = ?', (course_id,))
    course = cursor.fetchone()
    conn.close()
    return dict(course) if course else None

def create_course(name: str, description: str, instructor: str, start_date: str, end_date: str,
                  hours_per_week: Optional[int] = None, max_students: Optional[int] = None,
                  status: str = "upcoming", certificate_available: bool = False):
    """Создание курса"""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO Courses (name, description, instructor, start_date, end_date,
                            hours_per_week, max_students, status, certificate_available, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, description, instructor, start_date, end_date, hours_per_week,
          max_students, status, certificate_available, now))
    course_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return course_id

def register_for_course(user_id: int, course_id: int):
    """Регистрация пользователя на курс"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Проверяем, не зарегистрирован ли уже
    cursor.execute('''
        SELECT * FROM CourseRegistrations
        WHERE user_id = ? AND course_id = ?
    ''', (user_id, course_id))
    if cursor.fetchone():
        conn.close()
        raise ValueError("Вы уже зарегистрированы на этот курс")
    
    # Проверяем максимальное количество студентов
    cursor.execute('SELECT max_students FROM Courses WHERE id = ?', (course_id,))
    result = cursor.fetchone()
    if result and result[0]:
        cursor.execute('SELECT COUNT(*) FROM CourseRegistrations WHERE course_id = ?', (course_id,))
        current_count = cursor.fetchone()[0]
        if current_count >= result[0]:
            conn.close()
            raise ValueError("Достигнуто максимальное количество студентов")
    
    now = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO CourseRegistrations (user_id, course_id, created_at)
        VALUES (?, ?, ?)
    ''', (user_id, course_id, now))
    registration_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return registration_id

def get_user_course_registrations(user_id: int):
    """Получение всех регистраций пользователя на курсы"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*, cr.created_at as registration_date
        FROM Courses c
        JOIN CourseRegistrations cr ON c.id = cr.course_id
        WHERE cr.user_id = ?
        ORDER BY c.start_date ASC
    ''', (user_id,))
    registrations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return registrations

def cancel_course_registration(user_id: int, course_id: int):
    """Отмена регистрации на курс"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM CourseRegistrations
        WHERE user_id = ? AND course_id = ?
    ''', (user_id, course_id))
    conn.commit()
    deleted = cursor.rowcount
    conn.close()
    if deleted == 0:
        raise ValueError("Регистрация не найдена")
    return True

def is_user_registered_for_course(user_id: int, course_id: int):
    """Проверка, зарегистрирован ли пользователь на курс"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM CourseRegistrations
        WHERE user_id = ? AND course_id = ?
    ''', (user_id, course_id))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_course_participant_count(course_id: int):
    """Получение количества зарегистрированных студентов на курс"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM CourseRegistrations WHERE course_id = ?', (course_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_expert_audit_log(expert_id: int, hackathon_id: int = None):
    """Получение лога действий эксперта"""
    conn = get_db_connection()
    cursor = conn.cursor()
    if hackathon_id:
        cursor.execute('''
            SELECT * FROM ExpertAuditLog
            WHERE expert_id = ? AND hackathon_id = ?
            ORDER BY created_at DESC
        ''', (expert_id, hackathon_id))
    else:
        cursor.execute('''
            SELECT * FROM ExpertAuditLog
            WHERE expert_id = ?
            ORDER BY created_at DESC
        ''', (expert_id,))
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return logs
