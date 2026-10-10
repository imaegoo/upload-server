@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动文件服务 http://127.0.0.1:8888/ ...
python upload_server.py
echo.
echo 服务已停止。
pause
