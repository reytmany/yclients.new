from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import uvicorn
app = FastAPI()

templates = Jinja2Templates(directory="templates")

# примеры данных, позже добавим связь с бд
ADMINS = {"admin": "password"}
MASTERS = {"master1": "password", "master2": "password"}
masters_data = [
    {"id": 1, "name": "John", "rating": 4.5},
    {"id": 2, "name": "Jane", "rating": 3.8},
    {"id": 3, "name": "Emily", "rating": 5.0}
]
schedule = {
        "master1": ["Понедельник: 10:00-18:00", "Вторник: 10:00-18:00", "Среда: 10:00-18:00"],
        "master2": ["Понедельник: 11:00-19:00", "Вторник: 11:00-19:00", "Среда: 11:00-19:00"],
        "master3": ["Понедельник: 12:00-20:00", "Вторник: 12:00-20:00", "Среда: 12:00-20:00"]
    }
reviews_data = {
    "master1": [
        {"author": "Алексей Иванов", "rating": 5, "comment": "Отличный мастер! Быстро и качественно."},
        {"author": "Мария Смирнова", "rating": 4, "comment": "Хорошая работа, но чуть задержал выполнение."},
        {"author": "Дмитрий Кузнецов", "rating": 5, "comment": "Очень профессионально, рекомендую!"}
    ],
    "master2": [
        {"author": "Ольга Петрова", "rating": 3, "comment": "Средний результат, ожидала большего."},
        {"author": "Иван Сидоров", "rating": 4, "comment": "Хорошо, но не идеально."}
    ],
    "master3": [
        {"author": "Елена Федорова", "rating": 5, "comment": "Работа выполнена на высшем уровне!"},
        {"author": "Павел Васильев", "rating": 5, "comment": "Просто супер! Очень доволен."},
        {"author": "Анастасия Новикова", "rating": 4, "comment": "Работа хорошая, но есть над чем поработать."}
    ]
}

@app.get("/", response_class=HTMLResponse)
async def read_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# страница входа(требует ввод логин + пароль)
@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    # проверка прав администратора
    if username in ADMINS and ADMINS[username] == password:
        return RedirectResponse(url="/masters", status_code=302)
    # недопроверка существования аккаунта мастера
    elif username in MASTERS and MASTERS[username] == password:
        return RedirectResponse(url=f"/lkmasters/{username}", status_code=302)
    # данные неверные или не существует такого аккаунта
    return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный логин или пароль."})

# страница доступная только администратору с анкетами всех мастеров
@app.get("/masters", response_class=HTMLResponse)
async def masters(request: Request):
    return templates.TemplateResponse("masters.html", {"request": request, "masters": masters_data, "is_admin": True})

# страница отзывов на конкретного мастера, есть доступ как со страницы администратора, так и лк мастера
@app.get("/reviews/{username}/{is_admin}", response_class=HTMLResponse)
async def master_reviews(request: Request, username: str, is_admin: bool):
    reviews = reviews_data.get(username, [])
    return templates.TemplateResponse("reviews.html", {
        "request": request,
        "username": username,
        "reviews": reviews,
        "is_admin": is_admin})

# аналогично reviews(нужно добавить реализацию изменения расписания)
@app.get("/schedule/{username}/{is_admin}", response_class=HTMLResponse)
async def master_schedule(request: Request, username: str, is_admin: bool):
    sch = schedule.get(username, [])
    return templates.TemplateResponse("schedule.html", {
        "request": request,
        "username": username,
        "schedule": sch,
        "is_admin": is_admin})

# личный кабинет мастера, доступ к отзывам и своему расписанию(без возможности его изменить)
@app.get("/lkmasters/{username}", response_class=HTMLResponse)
async def master_lk(request: Request, username: str):
    return templates.TemplateResponse("lkmasters.html", {"request": request, "username": username, "is_admin": False})

# страница для добавления администратором нового мастера
@app.get("/add-master", response_class=HTMLResponse)
async def add_master(request: Request):
    return templates.TemplateResponse("addmaster.html", {"request": request})

# процесс добавления мастера(потом тоже добавим изменения в бд)
@app.post("/add-master")
async def save_master(request: Request, name: str = Form(...)):
    new_master = {
        "id": len(masters_data) + 1,
        "name": name,
        "rating": 0
    }
    masters_data.append(new_master)
    return RedirectResponse(url="/masters", status_code=302)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
