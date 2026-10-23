@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo Rode primeiro o instalar.bat
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
if "%ZERA_DADOS%"=="" set "ZERA_DADOS=C:\ZeraPlanejamento\dados"
echo Abrindo o Zera Planejamento no navegador. Mantenha esta janela aberta enquanto usa o sistema.
python -m zera_planejamento app
pause
