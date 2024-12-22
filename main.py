from fastapi import FastAPI, Form, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal, Master, Service, TimeSlot, TimeSlotStatus, Admin, Review, export_database, User
import uvicorn, random, string, os, json
from collections import defaultdict
from datetime import datetime, timedelta
from babel.dates import format_datetime

app = FastAPI()

templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def read_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# страница входа
@app.post("/login", response_class=RedirectResponse)
async def login_user(
    request: Request,
    login: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    admin = db.query(Admin).filter(Admin.login == login, Admin.password == password).first()
    master = db.query(Master).filter(Master.login == login, Master.password == password).first()
    if admin:
        return RedirectResponse(url="/masters", status_code=302)
    elif master:
        return RedirectResponse(url=f"/lkmasters/{master.login}", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Неверное имя пользователя или пароль"})

# регистрация администратора
@app.post("/register-admin", response_class=HTMLResponse)
async def register_admin(request: Request, login: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    existing_admin = db.query(Admin).filter(Admin.login == login).first()
    if existing_admin:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Администратор с таким именем уже существует."
        })
    new_admin = Admin(login=login, password=password)
    db.add(new_admin)
    db.commit()
    return templates.TemplateResponse("login.html", {"request": request})

# первая страница администратора с мастерами и услугами
@app.get("/masters", response_class=HTMLResponse)
async def masters(request: Request, db: Session = Depends(get_db)):
    ms = db.query(Master).all()
    masters_list = [
        {
            "id": master.id,
            "name": master.name,
            "rating": master.rating,
            "login": master.login,
            "password": master.password,
            "services": ", ".join(service.name for service in master.services)
        }
        for master in ms
    ]
    sv = db.query(Service).all()
    services = [
        {
            "name": service.name,
            "price": service.cost,
            "duration": service.duration
        }
        for service in sv
    ]
    return templates.TemplateResponse("masters.html", {"request": request, "masters": masters_list, "services": services, "is_admin": True}, status_code=302)


# личный кабинет мастера
@app.get("/lkmasters/{login}", response_class=HTMLResponse)
async def master_lk(request: Request, login: str):
    return templates.TemplateResponse("lkmasters.html", {"request": request, "login": login, "is_admin": False})


# расписание общее для админа и мастера (метка админа чтобы вернутся каждому в свою изначальную страницу)
@app.get("/schedule/{login}/{is_admin}", response_class=HTMLResponse)
async def get_schedule(request: Request, login: str, is_admin: bool, db: Session = Depends(get_db)):
    master = db.query(Master).filter(Master.login == login).first()
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не был найден")

    timeslots = db.query(TimeSlot).filter(TimeSlot.master_id == master.id).all()
    slots_by_day = defaultdict(list)

    for slot in timeslots:
        date = slot.start_time.date()
        date_str = date.strftime("%d-%m-%y")
        weekday = date.strftime("%A")
        time = slot.start_time.strftime("%H:%M")
        slots_by_day[date_str].append({
            "time": time,
            "status": slot.status.value
        })
    schedule = [{
        "date": date,
        "weekday": format_datetime(datetime.strptime(date, "%d-%m-%y"), "EEEE", locale="ru").capitalize(),  # День недели для каждой даты
        "slots": slots
    } for date, slots in sorted(slots_by_day.items())]

    return templates.TemplateResponse("schedule.html", {
        "request": request,
        "login": login,
        "username": master.login,
        "schedule": schedule,
        "is_admin": is_admin
    })


@app.post("/schedule/{login}/{is_admin}", response_class=HTMLResponse)
async def update_schedule(
        request: Request,
        login: str,
        is_admin: bool,
        selected_slots: str = Form(...),
        db: Session = Depends(get_db)
):
    master = db.query(Master).filter(Master.login == login).first()
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")

    db.query(TimeSlot).filter(TimeSlot.master_id == master.id).delete()
    try:
        for line in selected_slots.split("\n"):
            parts = line.split(",")
            date_str, time_str, status = parts[0], parts[1], parts[2]
            if time_str == "off":
                start_time = datetime.strptime(date_str, "%d-%m-%y")
                for hour in range(9, 19):
                    for i in range(4):
                        time_slot = TimeSlot(
                            master_id=master.id,
                            start_time=start_time + timedelta(hours=hour, minutes=i * 15),
                            status=TimeSlotStatus.booked
                        )
                        db.add(time_slot)
            else:
                start_time = datetime.strptime(f"{date_str} {time_str}", "%d-%m-%y %H:%M")
                time_slot = TimeSlot(
                    master_id=master.id,
                    start_time=start_time,
                    status=TimeSlotStatus[status]
                )
                db.add(time_slot)
        db.commit()
    except ValueError:
        raise HTTPException(status_code=400, detail="неверный формат")
    return RedirectResponse(url=f"/schedule/{login}/{is_admin}", status_code=302)
# добавление услуги мастеру
@app.get("/addservicetomaster/{master_login}", response_class=HTMLResponse)
async def add_service_to_master(master_login: str, request: Request, db: Session = Depends(get_db)):
    master = db.query(Master).filter(Master.login == master_login).first()
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")
    services = db.query(Service).all()
    return templates.TemplateResponse("addservicetomaster.html", {"request": request, "master_login": master_login, "services": services})

# добавление услуг мастеру
@app.post("/addservicetomaster/{master_login}", response_class=HTMLResponse)
async def save_services_to_master(master_login: str, services: list[int] = Form([]), db: Session = Depends(get_db)):
    master = db.query(Master).filter(Master.login == master_login).first()
    selected_services = db.query(Service).filter(Service.id.in_(services)).all()
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")
    master.services.extend(selected_services)
    db.commit()
    return RedirectResponse(url="/masters", status_code=302)

# редактирование расписания
@app.get("/chooseschedule/{login}/{is_admin}", response_class=HTMLResponse)
async def choose_schedule(request: Request, login: str, is_admin: bool):
    today = datetime.today()
    start_day = today + timedelta(days=1)  # Начинаем с завтрашнего дня
    week = [
        {
            "weekday": format_datetime(start_day + timedelta(days=i), "EEEE", locale="ru").capitalize(),
            "date": (start_day + timedelta(days=i)).strftime("%d-%m-%y")
        }
        for i in range(7)
    ]
    return templates.TemplateResponse("chooseschedule.html", {"request": request, "week": week, "login": login,"is_admin": is_admin})

@app.post("/chooseschedule/{login}/{is_admin}", response_class=HTMLResponse)
async def set_schedule(request: Request, login: str, is_admin: bool, schedule: list[str] = Form([]),
                       db: Session = Depends(get_db)):
    master = db.query(Master).filter(Master.login == login).first()
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")
    selected_dates = {slot.split("_")[0] for slot in schedule}
    for date in selected_dates:
        start_datetime = datetime.strptime(date, "%d-%m-%y")
        end_datetime = start_datetime + timedelta(days=1)
        db.query(TimeSlot).filter(
            TimeSlot.master_id == master.id,
            TimeSlot.start_time >= start_datetime,
            TimeSlot.start_time < end_datetime
        ).delete()
    for slot in schedule:
        date_parts = slot.split("_")
        date = date_parts[0]
        if date_parts[1] == "off" or date_parts[0] == "off":  # Если это выходной
            start_datetime = datetime.strptime(date, "%d-%m-%y")
            # end_datetime = start_datetime + timedelta(days=1)
            for hour in range(9, 19):
                for i in range(4):  # 4 интервала по 15 минут
                    time_slot = TimeSlot(
                        master_id=master.id,
                        start_time=start_datetime + timedelta(hours=hour, minutes=i * 15),
                        status=TimeSlotStatus.free
                    )
                    db.add(time_slot)
        else:
            hour = int(date_parts[1])
            base_time = datetime.strptime(date, "%d-%m-%y") + timedelta(hours=hour)
            for i in range(4):
                time_slot = TimeSlot(
                    master_id=master.id,
                    start_time=base_time + timedelta(minutes=i * 15),
                    status=TimeSlotStatus.free
                )
                db.add(time_slot)
    db.commit()
    return RedirectResponse(url=f"/schedule/{login}/{is_admin}", status_code=302)

# отзывы
@app.get("/reviews/{username}/{is_admin}", response_class=HTMLResponse)
async def master_reviews(request: Request, username: str, is_admin: bool, db: Session = Depends(get_db)):
    rw = db.query(Review).filter(Master.login == username).all()
    reviews_list = [
        {
            "name": db.query(User).filter(User.id == review.user_id).first().telegram_id,
            "rating": review.rating,
            "text": review.review_text
        }
        for review in rw
    ]
    return templates.TemplateResponse("reviews.html", {
        "request": request,
        "username": username,
        "reviews": reviews_list,
        "is_admin": is_admin})

# скачивание файла
@app.get("/download-db", response_class=FileResponse)
async def download_db():
    file_path = "database_export.json"
    try:
        export_database(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting database: {str(e)}")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=500, detail="Exported database file not found")
    return FileResponse(
        file_path,
        media_type="application/json",
        filename="database_export.json"
    )

# добавление мастеров с сгенерированными паролями и логинами
def generate_password(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))
@app.get("/add-master", response_class=HTMLResponse)
async def add_master_form(request: Request, db: Session = Depends(get_db)):
    password = generate_password()
    login = f"master{random.randint(5, 9999)}"
    services = db.query(Service).all()
    return templates.TemplateResponse("addmaster.html", {
        "request": request,
        "login": login,
        "password": password,
        "services": services
    })
# добавление
@app.post("/add-master")
async def save_master(
    name: str = Form(...),
    telegram_id: int = Form(...),
    login: str = Form(...),
    password: str = Form(...),
    services: list[int] = Form([]),
    db: Session = Depends(get_db)
):
    new_master = Master(name=name, telegram_id=telegram_id, login=login, password=password, services=[])
    if services:
        selected_services = db.query(Service).filter(Service.id.in_(services)).all()
        new_master.services.extend(selected_services)
    db.add(new_master)
    db.commit()
    return RedirectResponse(url="/masters", status_code=302)

# добавление сервисов
@app.get("/add-service", response_class=HTMLResponse)
async def get_add_service_form(request: Request):
    return templates.TemplateResponse("addservice.html", {"request": request})
#
@app.post("/add-service")
async def add_service(
    request: Request,
    name: str = Form(...),
    price: int = Form(...),
    duration: int = Form(...),
    db: Session = Depends(get_db)
):
    new_service = Service(name=name, cost=price, duration=duration)
    db.add(new_service)
    db.commit()
    return RedirectResponse(url="/masters", status_code=302)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
