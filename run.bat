@echo off
chcp 65001 > nul
title ComfyUI 节点翻译 - 作者 OldX

:: 检查 Python 是否安装
python --version > nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.7 或更高版本
    pause
    exit /b
)

:: 检查是否需要安装依赖
if not exist "requirements.txt" (
    echo [错误] 未找到 requirements.txt 文件
    pause
    exit /b
)

:: 检查并安装依赖
echo [信息] 检查依赖...
pip install -r requirements.txt > nul 2>&1

:: 启动程序
echo [信息] 启动程序...
python main.py

:: 如果程序异常退出，暂停显示错误信息
if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出
    pause
) 