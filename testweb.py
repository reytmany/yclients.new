import pytest, os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, Admin, Master, Service
from main import app, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="function")
def setup_database():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    test_admin = Admin(login="test_admin", password="password123")
    test_master = Master(name="Test Master", login="test_master", password="master123", telegram_id='12345')
    test_service = Service(name="Test Service", cost=100, duration=30)
    db.add(test_admin)
    db.add(test_master)
    db.add(test_service)
    db.commit()
    yield db
    Base.metadata.drop_all(bind=engine)

def test_read_login_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "login" in response.text

def test_login_admin_success(setup_database):
    response = client.post("/login", data={"login": "test_admin", "password": "password123"})
    assert response.status_code == 302

def test_register_admin_success(setup_database):
    response = client.post("/register-admin", data={"login": "new_admin", "password": "newpassword"})
    assert response.status_code == 200
    assert "login" in response.text  # возвращает на логин

def test_add_master_success(setup_database):
    response = client.post("/add-master", data={
        "name": "New Master",
        "telegram_id": 54321,
        "login": "new_master",
        "password": "newpassword",
        "services": []
    })
    assert response.status_code == 302

def test_login_failure(setup_database):
    response = client.post("/login", data={"login": "invalid_user", "password": "wrong_password"})
    assert response.status_code == 200
    assert "Неверное имя пользователя или пароль" in response.text

def test_register_admin_duplicate(setup_database):
    response = client.post("/register-admin", data={"login": "test_admin", "password": "password123"})
    assert response.status_code == 200
    assert "Администратор с таким именем уже существует." in response.text

def test_get_masters_page(setup_database):
    response = client.get("/masters")
    assert response.status_code == 302

def test_get_master_lk(setup_database):
    master_login = "test_master"
    response = client.get(f"/lkmasters/{master_login}")
    assert response.status_code == 200
    assert master_login.encode() in response.content

def test_get_schedule_page(setup_database):
    master_login = "test_master"
    response = client.get(f"/schedule/{master_login}/True")
    assert response.status_code == 200

def test_get_reviews_page(setup_database):
    username = "test_master"
    response = client.get(f"/reviews/{username}/False")
    assert response.status_code == 200

def test_get_add_service_page():
    response = client.get("/add-service")
    assert response.status_code == 200

def test_add_service_to_master(setup_database):
    db = next(override_get_db())
    test_master = db.query(Master).filter_by(login="test_master").first()
    test_service = db.query(Service).filter_by(name="Test Service").first()
    response = client.post(f"/addservicetomaster/{test_master.login}", data={"services": [test_service.id]})
    assert response.status_code == 302
    updated_master = db.query(Master).filter_by(login="test_master").first()
    assert len(updated_master.services) == 1
    assert updated_master.services[0].name == "Test Service"

def test_download_database():
    if os.path.exists("database_export.json"):
        os.remove("database_export.json")
    response = client.get("/download-db")
    assert response.status_code == 200
    assert response.headers['content-type'] == 'application/json'
    assert 'attachment; filename="database_export.json"' in response.headers['content-disposition']
    assert os.path.exists("database_export.json")
    os.remove("database_export.json")