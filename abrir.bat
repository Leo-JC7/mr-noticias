@echo off
REM Atualiza as noticias e abre a pagina no navegador (clique duplo aqui)
cd /d "%~dp0"
echo Buscando noticias, aguarde alguns segundos...
python atualizar.py
REM Abre a pagina mesmo se a busca falhar (ex.: sem internet) - mostra a versao anterior
start "" "%~dp0site\index.html"
