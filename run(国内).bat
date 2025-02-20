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

:: 检查虚拟环境
if not exist "venv" (
    echo [信息] 创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b
    )
)

:: 激活虚拟环境
echo [信息] 激活虚拟环境...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [错误] 激活虚拟环境失败
    pause
    exit /b
)

:: 设置pip国内源
echo [信息] 设置pip国内源...
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
pip config set global.trusted-host mirrors.aliyun.com

:: 检查是否需要安装依赖
if not exist "requirements.txt" (
    echo [错误] 未找到 requirements.txt 文件
    pause
    exit /b
)

:: 检查并安装依赖
echo [信息] 检查依赖...
pip list > installed_packages.txt 2>&1

:: 读取 requirements.txt 中的每个包
for /f "tokens=1,2 delims==" %%a in (requirements.txt) do (
    :: 检查包是否已安装
    findstr /i /c:"%%a" installed_packages.txt > nul
    if errorlevel 1 (
        echo [信息] 正在从国内源安装 %%a...
        pip install %%a -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
        if errorlevel 1 (
            echo [错误] 安装 %%a 失败，尝试其他源...
            :: 尝试清华源
            pip install %%a -i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn
            if errorlevel 1 (
                :: 尝试腾讯源
                pip install %%a -i https://mirrors.cloud.tencent.com/pypi/simple/ --trusted-host mirrors.cloud.tencent.com
                if errorlevel 1 (
                    echo [错误] 所有源安装失败
                    del installed_packages.txt
                    deactivate
                    pause
                    exit /b
                )
            )
        )
    )
)

:: 清理临时文件
del installed_packages.txt

:: 启动程序
echo [信息] 启动程序...
python main.py

:: 如果程序异常退出，暂停显示错误信息
if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出
    pause
)

:: 退出前停用虚拟环境
deactivate 