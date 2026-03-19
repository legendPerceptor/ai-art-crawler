FROM python:3.11-slim

WORKDIR /app

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 创建数据目录
RUN mkdir -p /data/crawled/images

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV OUTPUT_DIR=/data/crawled
ENV PYTHONPATH=/app

# 默认命令
CMD ["python", "scripts/run_crawler.py", "--help"]
