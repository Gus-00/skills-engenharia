@echo off
REM Pesquisa de skills em vagas de engenharia - menu de execucao
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

python --version > nul 2>&1
if errorlevel 1 (
    echo Python nao encontrado. Instale em https://www.python.org/downloads/ e marque "Add to PATH".
    pause
    exit /b 1
)

if not exist ".deps_ok" (
    echo Instalando dependencias...
    python -m pip install -q -r requirements.txt || (pause & exit /b 1)
    echo ok > .deps_ok
)

:menu
echo.
echo ==== Skills em vagas de engenharia ====
echo  1 - Coletar vagas novas e atualizar os resultados  (pode levar ~1 h)
echo  2 - So atualizar os resultados (sem coletar)
echo  3 - Abrir o painel no navegador
echo  4 - Gerar amostra de validacao
echo  5 - Calcular metricas da validacao (depois de anotar)
echo  0 - Sair
set /p op="Escolha: "

if "%op%"=="1" (python coleta.py & python extrai.py & python analise.py & goto menu)
if "%op%"=="2" (python extrai.py & python analise.py & goto menu)
if "%op%"=="3" (python -m streamlit run app.py --server.port 8510 & goto menu)
if "%op%"=="4" (python validacao.py amostra --n 80 & goto menu)
if "%op%"=="5" (python validacao.py metricas & goto menu)
if "%op%"=="0" exit /b 0
goto menu
