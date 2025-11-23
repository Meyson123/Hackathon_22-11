from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from db import (
    get_current_user, get_db_connection, require_admin,
    require_expert_in_hackathon, get_hackathon_by_id,
    get_all_hackathons, get_participation, get_user_participations,
    get_hackathon_participants, create_participation, update_participation_role,
    update_reputation, get_reputation_history, delete_participation,
    create_team, get_team_by_id, get_team_by_code, get_team_members,
    get_user_team_in_hackathon, add_member_to_team, remove_member_from_team,
    update_team_name, get_available_teams, get_expert_areas
)

templates = Jinja2Templates(directory="templates")
router = APIRouter()

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
    min_participants: Optional[int] = 0
    published: Optional[int] = 0

class ParticipationCreate(BaseModel):
    hackathon_id: int
    role: str
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

# Роуты страниц хакатонов
@router.get("/hackathons.html", response_class=HTMLResponse)
async def hackathons_page(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("hackathons.html", {
        "request": request,
        "user": user
    })

@router.get("/expert.html", response_class=HTMLResponse)
async def expert_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login.html", status_code=302)
    return templates.TemplateResponse("expert.html", {"request": request, "user": user})

@router.get("/team.html", response_class=HTMLResponse)
async def team_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login.html", status_code=302)

    hackathon_id_param = request.query_params.get("hackathon_id")
    team_id_param = request.query_params.get("team_id")

    if not hackathon_id_param:
        raise HTTPException(status_code=400, detail="hackathon_id обязателен")

    try:
        hackathon_id = int(hackathon_id_param)
        team_id = int(team_id_param) if team_id_param else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат параметров")

    if not team_id:
        team = get_user_team_in_hackathon(user["id"], hackathon_id)
        if team:
            team_id = team["id"]
        else:
            raise HTTPException(status_code=404, detail="Команда не найдена")

    team = get_team_by_id(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Команда не найдена")

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

# Роуты для страниц хакатонов по ролям
@router.get("/hackathon/{hackathon_id}")
async def hackathon_main_page(hackathon_id: int, request: Request):
    hackathon = get_hackathon_by_id(hackathon_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Хакатон не найден")

    user = get_current_user(request)
    return templates.TemplateResponse("hackathon_main.html", {
        "request": request,
        "hackathon": hackathon,
        "user": user
    })

@router.get("/hackathon/{hackathon_id}/role-check")
async def role_checkup(hackathon_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login.html")

    hackathon = get_hackathon_by_id(hackathon_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Хакатон не найден")

    participation = get_participation(user["id"], hackathon_id)
    if participation:
        role = participation["role"].lower()
        if role == "captain":
            return RedirectResponse(url=f"/hackathon/{hackathon_id}/captain")
        elif role == "expert":
            return RedirectResponse(url=f"/hackathon/{hackathon_id}/expert")
        elif role == "team_member" or role == "free_participant":
            return RedirectResponse(url=f"/hackathon/{hackathon_id}/user")

    role = user["role"].lower()
    if role == "admin":
        return RedirectResponse(url=f"/hackathon/{hackathon_id}/admin")
    elif role == "case_holder":
        return RedirectResponse(url=f"/hackathon/{hackathon_id}/case-holder")
    else:
        return RedirectResponse(url=f"/hackathon/{hackathon_id}/user")

@router.get("/hackathon/{hackathon_id}/user")
async def user_hackathon_page(hackathon_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login.html")

    hackathon = get_hackathon_by_id(hackathon_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Хакатон не найден")

    return templates.TemplateResponse("user_hackathon.html", {
        "request": request,
        "hackathon": hackathon,
        "user_id": user["id"],
        "user_role": user["role"]
    })

@router.get("/hackathon/{hackathon_id}/captain")
async def captain_hackathon_page(hackathon_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login.html")

    hackathon = get_hackathon_by_id(hackathon_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Хакатон не найден")

    return templates.TemplateResponse("captain_hackathon.html", {
        "request": request,
        "hackathon": hackathon,
        "user_id": user["id"],
        "user_role": user["role"]
    })

@router.get("/hackathon/{hackathon_id}/case-holder")
async def case_holder_hackathon_page(hackathon_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login.html")

    hackathon = get_hackathon_by_id(hackathon_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Хакатон не найден")

    return templates.TemplateResponse("case_holder_hackathon.html", {
        "request": request,
        "hackathon": hackathon,
        "user_id": user["id"],
        "user_role": user["role"]
    })

@router.get("/hackathon/{hackathon_id}/admin")
async def admin_hackathon_page(hackathon_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login.html")

    hackathon = get_hackathon_by_id(hackathon_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Хакатон не найден")

    return templates.TemplateResponse("admin_hackathon.html", {
        "request": request,
        "hackathon": hackathon,
        "user_id": user["id"],
        "user_role": user["role"]
    })

@router.get("/hackathon/{hackathon_id}/expert")
async def expert_hackathon_page(hackathon_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login.html")

    try:
        require_expert_in_hackathon(request, hackathon_id)
    except HTTPException:
        if user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Требуются права эксперта в данном хакатоне")

    hackathon = get_hackathon_by_id(hackathon_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Хакатон не найден")

    expert_areas = get_expert_areas(user["id"], hackathon_id)

    return templates.TemplateResponse("expert_hackathon.html", {
        "request": request,
        "hackathon": hackathon,
        "user_id": user["id"],
        "user_role": user["role"],
        "expert_areas": expert_areas
    })

# API роуты хакатонов
@router.get("/api/hackathons")
async def get_hackathons_api(request: Request, status_filter: Optional[str] = None, admin_only: Optional[bool] = False):
    user = get_current_user(request)
    is_admin = user and user.get("role") == "admin"

    if admin_only or (is_admin and "/admin" in str(request.url)):
        hackathons = get_all_hackathons(status_filter)
        conn = get_db_connection()
        cursor = conn.cursor()
        for hackathon in hackathons:
            cursor.execute("SELECT COUNT(*) FROM Participations WHERE hackathon_id = ?", (hackathon["id"],))
            hackathon["participant_count"] = cursor.fetchone()[0]
        conn.close()
        return hackathons

    hackathons = get_all_hackathons(status_filter)
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(Hackathons)")
    columns = [column[1] for column in cursor.fetchall()]
    has_published = 'published' in columns
    has_min_participants = 'min_participants' in columns

    # Для обычных пользователей показываем все хакатоны, кроме черновиков
    filtered_hackathons = []
    for hackathon in hackathons:
        cursor.execute("SELECT COUNT(*) FROM Participations WHERE hackathon_id = ?", (hackathon["id"],))
        participant_count = cursor.fetchone()[0]

        if has_published and has_min_participants:
            published = hackathon.get("published", 0) or 0
            min_participants = hackathon.get("min_participants", 0) or 0

            # Показываем если опубликован ИЛИ если минимальное количество участников достигнуто
            if published == 1 or participant_count >= min_participants:
                filtered_hackathons.append(hackathon)
        else:
            # Если колонок нет, показываем все хакатоны
            filtered_hackathons.append(hackathon)

    conn.close()
    return filtered_hackathons

@router.get("/api/hackathons/{hackathon_id}")
async def get_hackathon_api(hackathon_id: int, request: Request):
    hackathon = get_hackathon_by_id(hackathon_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Хакатон не найден")
    return hackathon

@router.post("/api/hackathons")
async def create_hackathon(hackathon_data: HackathonCreate, request: Request, admin=Depends(require_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.now().isoformat()
    cursor.execute("PRAGMA table_info(Hackathons)")
    columns = [column[1] for column in cursor.fetchall()]
    has_min_participants = 'min_participants' in columns
    has_published = 'published' in columns

    if has_min_participants and has_published:
        cursor.execute('''
            INSERT INTO Hackathons (name, description, organizer, start_date, end_date, 
                                   duration_hours, prize_fund, max_team_size, status, 
                                   min_participants, published, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            hackathon_data.name, hackathon_data.description, hackathon_data.organizer,
            hackathon_data.start_date, hackathon_data.end_date, hackathon_data.duration_hours,
            hackathon_data.prize_fund, hackathon_data.max_team_size, hackathon_data.status,
            hackathon_data.min_participants or 0, hackathon_data.published or 0, now
        ))
    else:
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

@router.put("/api/hackathons/{hackathon_id}")
async def update_hackathon(hackathon_id: int, hackathon_data: HackathonCreate, request: Request, admin=Depends(require_admin)):
    user = get_current_user(request)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Требуются права администратора")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Hackathons WHERE id = ?", (hackathon_id,))
    hackathon = cursor.fetchone()
    if not hackathon:
        conn.close()
        raise HTTPException(status_code=404, detail="Хакатон не найден")

    hackathon_dict = dict(hackathon)
    start_date = datetime.fromisoformat(hackathon_dict["start_date"])
    if start_date <= datetime.now():
        conn.close()
        raise HTTPException(status_code=400, detail="Можно редактировать только предстоящие хакатоны")

    cursor.execute("PRAGMA table_info(Hackathons)")
    columns = [column[1] for column in cursor.fetchall()]
    has_min_participants = 'min_participants' in columns
    has_published = 'published' in columns

    if has_min_participants and has_published:
        cursor.execute('''
            UPDATE Hackathons 
            SET name = ?, description = ?, organizer = ?, start_date = ?, end_date = ?,
                duration_hours = ?, prize_fund = ?, max_team_size = ?, status = ?,
                min_participants = ?, published = ?
            WHERE id = ?
        ''', (
            hackathon_data.name, hackathon_data.description, hackathon_data.organizer,
            hackathon_data.start_date, hackathon_data.end_date, hackathon_data.duration_hours,
            hackathon_data.prize_fund, hackathon_data.max_team_size, hackathon_data.status,
            hackathon_data.min_participants or 0, hackathon_data.published or 0, hackathon_id
        ))
    else:
        cursor.execute('''
            UPDATE Hackathons 
            SET name = ?, description = ?, organizer = ?, start_date = ?, end_date = ?,
                duration_hours = ?, prize_fund = ?, max_team_size = ?, status = ?
            WHERE id = ?
        ''', (
            hackathon_data.name, hackathon_data.description, hackathon_data.organizer,
            hackathon_data.start_date, hackathon_data.end_date, hackathon_data.duration_hours,
            hackathon_data.prize_fund, hackathon_data.max_team_size, hackathon_data.status,
            hackathon_id
        ))

    conn.commit()
    conn.close()

    return {"message": "Хакатон обновлён"}

# ========== Participations API ==========
@router.get("/api/participations")
async def get_my_participations(request: Request):
    """Получение всех участий текущего пользователя"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    participations = get_user_participations(user["id"])
    return participations

@router.get("/api/participations/{user_id}/{hackathon_id}")
async def get_participation_info(user_id: int, hackathon_id: int, request: Request):
    """Получение информации об участии"""
    participation = get_participation(user_id, hackathon_id)
    if not participation:
        raise HTTPException(status_code=404, detail="Участие не найдено")
    return participation

@router.post("/api/participations")
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

@router.delete("/api/participations/{hackathon_id}")
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

@router.put("/api/participations/{user_id}/{hackathon_id}/role")
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

# ========== Reputation API ==========
@router.get("/api/hackathons/{hackathon_id}/participants")
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

@router.put("/api/reputation")
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

@router.get("/api/reputation/history/{participation_id}")
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

# ========== Teams API ==========
@router.get("/api/teams/{team_id}")
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

@router.get("/api/hackathons/{hackathon_id}/teams")
async def get_available_teams_endpoint(hackathon_id: int, request: Request):
    """Получение доступных команд в хакатоне"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    teams = get_available_teams(hackathon_id)
    return teams

@router.post("/api/teams")
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

@router.put("/api/teams/{team_id}")
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

@router.post("/api/teams/{team_id}/members")
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

@router.delete("/api/teams/{team_id}/members")
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
