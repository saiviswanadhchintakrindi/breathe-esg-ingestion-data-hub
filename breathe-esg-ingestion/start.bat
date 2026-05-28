@echo off
echo ==============================================================
echo 🌱 Starting Breathe ESG Data Ingestion & Normalization Platform
echo ==============================================================

:: Ensure database migrations and initial seeds are configured
echo [1/3] Running backend database checks...
cd backend
python manage.py migrate
python manage.py seed_esg_data
cd ..

:: Spin up Django REST Backend
echo [2/3] Starting REST API backend in new window (Port 8000)...
start "Breathe ESG - Django Backend" cmd /k "cd backend && python manage.py runserver 127.0.0.1:8000"

:: Spin up React Frontend
echo [3/3] Starting React client in new window (Port 3000)...
start "Breathe ESG - React Frontend" cmd /k "cd frontend && npm run dev"

echo --------------------------------------------------------------
echo ✅ Startup commands issued!
echo 🚀 API Backend URL: http://127.0.0.1:8000/api/
echo 💻 Review Dashboard URL: http://localhost:3000/
echo --------------------------------------------------------------
pause
