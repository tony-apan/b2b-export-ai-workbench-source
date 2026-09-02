@echo off
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 "%~dp0install.py" %*
if errorlevel 1 goto failed
exit /b 0

:use_python
python "%~dp0install.py" %*
if errorlevel 1 goto failed
exit /b 0

:failed
echo 若失败请安装 Python 3.10+ 后重试。
exit /b 1
