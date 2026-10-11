@echo off
REM Пересобрать .exe одной командой
py -m PyInstaller --onefile --windowed --name TrashSpy --icon icon.ico deleted_viewer.py
echo.
echo Gotovo: dist\TrashSpy.exe
pause
