from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
from dotenv import load_dotenv
from db import get_current_user, require_admin, get_db_connection
from routes.auth import UserCreate

templates = Jinja2Templates(directory="templates")
router = APIRouter()
load_dotenv()
ADM_PASS = os.getenv('ADM_PASS')

# Роуты страниц админки
@router.get("/admin-hackathons.html", response_class=HTMLResponse)
async def admin_hackathons_page(request: Request, user=Depends(require_admin)):
    return templates.TemplateResponse("admin-hackathons.html", {"request": request, "user": user})

@router.get("/admin-hackathon-details.html", response_class=HTMLResponse)
async def admin_hackathon_details_page(request: Request, user=Depends(require_admin)):
    return templates.TemplateResponse("admin-hackathon-details.html", {"request": request, "user": user})

@router.get("/admin-webinars.html", response_class=HTMLResponse)
async def admin_webinars_page(request: Request, user=Depends(require_admin)):
    return templates.TemplateResponse("admin-webinars.html", {"request": request, "user": user})

@router.get("/admin-analytics.html", response_class=HTMLResponse)
async def admin_analytics_page(request: Request, user=Depends(require_admin)):
    return templates.TemplateResponse("admin-analytics.html", {"request": request, "user": user})

@router.get("/admin.html", response_class=HTMLResponse)
async def admin_page(request: Request, user=Depends(require_admin)):
    return templates.TemplateResponse("admin.html", {"request": request, "user": user})

@router.get("/admin-login.html", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse("admin-login.html", {"request": request})

# API роуты админки
@router.post("/api/admin/login")
async def admin_login(request: Request, credentials: dict):
    login = credentials.get("login", "").strip()
    password = credentials.get("password", "").strip()

    if login == "admin" and password == ADM_PASS:
        from db import get_user_by_email, get_user_by_id
        user = get_user_by_email("admin@hackathon.local")
        if not user:
            conn = get_db_connection()
            cursor = conn.cursor()
            from datetime import datetime
            cursor.execute('''
                INSERT INTO Users (username, email, password, role, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', ("admin", "admin@hackathon.local", "admin123", "admin", datetime.now().isoformat()))
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            user = get_user_by_id(user_id)
        else:
            if user["password"] != "admin123":
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE Users SET password = ? WHERE id = ?", ("admin123", user["id"]))
                conn.commit()
                conn.close()

        request.session["user_id"] = user["id"]
        request.session["role"] = "admin"
        request.session["email"] = user["email"]
        request.session["username"] = user["username"]

        return {"message": "Успешный вход администратора", "user": {k: v for k, v in user.items() if k != "password"}}
    else:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

@router.get("/api/users")
async def get_users(request: Request, admin=Depends(require_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()

    for user in users:
        user.pop("password", None)

    return users

@router.get("/api/statistics")
async def get_statistics(request: Request, admin=Depends(require_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM Users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Users WHERE role = 'admin'")
    admin_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Users WHERE role = 'user'")
    regular_users = cursor.fetchone()[0]

    from datetime import datetime
    current_month = datetime.now().strftime("%Y-%m")
    cursor.execute("SELECT COUNT(*) FROM Users WHERE strftime('%Y-%m', created_at) = ?", (current_month,))
    users_this_month = cursor.fetchone()[0]

    cursor.execute("SELECT city, COUNT(*) FROM Users WHERE city IS NOT NULL GROUP BY city")
    cities_stats = dict(cursor.fetchall())

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

@router.delete("/api/users/{user_id}")
async def delete_user(user_id: int, request: Request, admin=Depends(require_admin)):
    if user_id == 1:
        raise HTTPException(status_code=400, detail="Нельзя удалить первого администратора")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Users WHERE id = ?", (user_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    cursor.execute("DELETE FROM Users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    return {"message": "Пользователь удалён"}

@router.put("/api/users/{user_id}")
async def update_user(user_id: int, user_data: dict, request: Request, admin=Depends(require_admin)):
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

    return {"message": "Пользователь обновлен"}
