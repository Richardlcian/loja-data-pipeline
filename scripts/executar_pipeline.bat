@echo off
rem Executa o pipeline da loja, faz o backup e registra o resultado em logs\agendador.log.
rem Pode ser rodado com duplo clique ou agendado no Agendador de Tarefas do Windows.
setlocal
cd /d "%~dp0.."
if not exist logs mkdir logs

set PY=.venv\Scripts\python.exe
if not exist "%PY%" (
    echo [%date% %time%] ERRO: ambiente .venv nao encontrado em %cd% >> logs\agendador.log
    exit /b 2
)

echo [%date% %time%] Iniciando pipeline >> logs\agendador.log
"%PY%" -m src.pipeline >> logs\agendador.log 2>&1
set CODIGO=%errorlevel%

if %CODIGO% neq 0 (
    echo [%date% %time%] FALHOU com codigo %CODIGO% >> logs\agendador.log
    echo Falha em %date% %time% - codigo %CODIGO%. Veja logs\pipeline.log > logs\ULTIMA_FALHA.txt
) else (
    echo [%date% %time%] Concluido com sucesso >> logs\agendador.log
    if exist logs\ULTIMA_FALHA.txt del logs\ULTIMA_FALHA.txt
    "%PY%" scripts\backup.py >> logs\agendador.log 2>&1
)
exit /b %CODIGO%
