import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware


from routes import auth, hackathon, webinars_courses, admin
from db import init_database, migrate_hackathons_table


ADM_PASS = os.getenv('ADM_PASS')
app = FastAPI(title="Хакатон Хаб}")

# Middleware для сессий
app.add_middleware(
    SessionMiddleware,
    secret_key="hackathon-hub-secret-key-2024-change-in-production",
    max_age=86400
)

# Статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# Подключение роутов
app.include_router(auth.router, tags=["Authentication"])
app.include_router(hackathon.router, tags=["Hackathons"])
app.include_router(webinars_courses.router, tags=["Webinars & Courses"])
app.include_router(admin.router, tags=["Admin"])

# Инициализация БД
init_database()
migrate_hackathons_table()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
