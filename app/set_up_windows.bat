@echo off
echo Instalando dependencias para Windows...
echo.

REM Crear entorno virtual (opcional pero recomendado)
python -m venv venv
call venv\Scripts\activate.bat

REM Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Instalacion completada!
echo.
echo Para ejecutar la aplicacion:
echo python main.py
pause