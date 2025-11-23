from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional

from db import (
    get_current_user, require_admin, get_all_webinars, get_webinar_by_id,
    create_webinar, register_for_webinar, get_user_webinar_registrations,
    cancel_webinar_registration, is_user_registered_for_webinar,
    get_webinar_participant_count, get_all_courses, get_course_by_id,
    create_course, register_for_course, get_user_course_registrations,
    cancel_course_registration, is_user_registered_for_course,
    get_course_participant_count
)

templates = Jinja2Templates(directory="templates")
router = APIRouter()

class WebinarCreate(BaseModel):
    name: str
    description: Optional[str] = None
    speaker: str
    date_time: str
    duration_hours: Optional[float] = None
    location: str = "Онлайн"
    max_participants: Optional[int] = None
    status: str = "upcoming"

class CourseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    instructor: str
    start_date: str
    end_date: str
    hours_per_week: Optional[int] = None
    max_students: Optional[int] = None
    status: str = "upcoming"
    certificate_available: bool = False

# Роуты страниц
@router.get("/seminars.html", response_class=HTMLResponse)
async def seminars_page(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("seminars.html", {
        "request": request,
        "user": user
    })

# Webinars API
@router.get("/api/webinars")
async def get_webinars_api(request: Request, status_filter: Optional[str] = None):
    webinars = get_all_webinars(status_filter)

    user = get_current_user(request)
    if user:
        for webinar in webinars:
            webinar["is_registered"] = is_user_registered_for_webinar(user["id"], webinar["id"])
            webinar["participant_count"] = get_webinar_participant_count(webinar["id"])
    else:
        for webinar in webinars:
            webinar["is_registered"] = False
            webinar["participant_count"] = get_webinar_participant_count(webinar["id"])

    return webinars

@router.get("/api/webinars/{webinar_id}")
async def get_webinar_api(webinar_id: int, request: Request):
    webinar = get_webinar_by_id(webinar_id)
    if not webinar:
        raise HTTPException(status_code=404, detail="Вебинар не найден")

    user = get_current_user(request)
    if user:
        webinar["is_registered"] = is_user_registered_for_webinar(user["id"], webinar_id)
    else:
        webinar["is_registered"] = False
    webinar["participant_count"] = get_webinar_participant_count(webinar_id)

    return webinar

@router.post("/api/webinars")
async def create_webinar_api(webinar_data: WebinarCreate, request: Request, admin=Depends(require_admin)):
    webinar_id = create_webinar(
        webinar_data.name,
        webinar_data.description,
        webinar_data.speaker,
        webinar_data.date_time,
        webinar_data.duration_hours,
        webinar_data.location,
        webinar_data.max_participants,
        webinar_data.status
    )
    return {"message": "Вебинар создан", "webinar_id": webinar_id}

@router.post("/api/webinars/{webinar_id}/register")
async def register_for_webinar_api(webinar_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    try:
        registration_id = register_for_webinar(user["id"], webinar_id)
        return {"message": "Регистрация успешна", "registration_id": registration_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/api/webinars/{webinar_id}/register")
async def cancel_webinar_registration_api(webinar_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    try:
        cancel_webinar_registration(user["id"], webinar_id)
        return {"message": "Регистрация отменена"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/webinars/my-registrations")
async def get_my_webinar_registrations_api(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    registrations = get_user_webinar_registrations(user["id"])
    return registrations

# Courses API
@router.get("/api/courses")
async def get_courses_api(request: Request, status_filter: Optional[str] = None):
    courses = get_all_courses(status_filter)

    user = get_current_user(request)
    if user:
        for course in courses:
            course["is_registered"] = is_user_registered_for_course(user["id"], course["id"])
            course["participant_count"] = get_course_participant_count(course["id"])
    else:
        for course in courses:
            course["is_registered"] = False
            course["participant_count"] = get_course_participant_count(course["id"])

    return courses

@router.get("/api/courses/{course_id}")
async def get_course_api(course_id: int, request: Request):
    course = get_course_by_id(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Курс не найден")

    user = get_current_user(request)
    if user:
        course["is_registered"] = is_user_registered_for_course(user["id"], course_id)
    else:
        course["is_registered"] = False
    course["participant_count"] = get_course_participant_count(course_id)

    return course

@router.post("/api/courses")
async def create_course_api(course_data: CourseCreate, request: Request, admin=Depends(require_admin)):
    course_id = create_course(
        course_data.name,
        course_data.description,
        course_data.instructor,
        course_data.start_date,
        course_data.end_date,
        course_data.hours_per_week,
        course_data.max_students,
        course_data.status,
        course_data.certificate_available
    )
    return {"message": "Курс создан", "course_id": course_id}

@router.post("/api/courses/{course_id}/register")
async def register_for_course_api(course_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    try:
        registration_id = register_for_course(user["id"], course_id)
        return {"message": "Регистрация успешна", "registration_id": registration_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/api/courses/{course_id}/register")
async def cancel_course_registration_api(course_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    try:
        cancel_course_registration(user["id"], course_id)
        return {"message": "Регистрация отменена"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/courses/my-registrations")
async def get_my_course_registrations_api(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    registrations = get_user_course_registrations(user["id"])
    return registrations
