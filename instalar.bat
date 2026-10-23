@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Instalando o Zera Planejamento Tributario...
where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale o Python 3.11 ou superior em https://www.python.org/downloads/
  echo e marque a opcao "Add python.exe to PATH" na primeira tela do instalador.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\activate.bat" python -m venv .venv
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -e .
if errorlevel 1 (
  echo Falha na instalacao. Veja as mensagens acima.
  pause
  exit /b 1
)
if not exist "C:\ZeraPlanejamento\dados" mkdir "C:\ZeraPlanejamento\dados"
echo.
echo Instalacao concluida. Para abrir o sistema use "Iniciar Zera Planejamento.bat".
pause
