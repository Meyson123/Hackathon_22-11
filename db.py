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
