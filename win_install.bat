@echo off
echo [1/2] 正在升级 pip...
python -m pip install --upgrade pip

echo [2/2] 正在安装 Tinbot 依赖库...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo ==========================================
echo  ✅ 安装完成！
echo  无需下载浏览器，直接接管现有 Chrome/Edge。
echo  请确保配置好 .env 文件。
echo  启动方式: python agent.py
echo ==========================================
pause