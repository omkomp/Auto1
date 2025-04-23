@echo off
start python -m http.server 8000 --directory static
start cmd /k "ngrok http 8000"
python bot.py