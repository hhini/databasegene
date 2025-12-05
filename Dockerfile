# 1. 选一个 Python 基础镜像 (轻量版)
FROM python:3.12-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 先把依赖文件拷贝进去
COPY requirements.txt .

# 4. 安装依赖 (加 -i 是为了用国内源下载快一点，如果在国外可去掉)
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 5. 把你的代码文件都拷进去
COPY . .

# 6. 告诉容器我们要暴露 8000 端口
EXPOSE 8000

# 7. 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
