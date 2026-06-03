@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set TARGET_DIR=%~dp0EduMark
set PROJECT_DIR=%~dp0.

echo 初始化部署目录: %TARGET_DIR%

rem 创建数据目录
if not exist "%TARGET_DIR%\mysql\data" mkdir "%TARGET_DIR%\mysql\data"
if not exist "%TARGET_DIR%\redis\conf" mkdir "%TARGET_DIR%\redis\conf"
if not exist "%TARGET_DIR%\redis\data" mkdir "%TARGET_DIR%\redis\data"
if not exist "%TARGET_DIR%\minio\data" mkdir "%TARGET_DIR%\minio\data"
if not exist "%TARGET_DIR%\minio\config" mkdir "%TARGET_DIR%\minio\config"
if not exist "%TARGET_DIR%\qdrant\storage" mkdir "%TARGET_DIR%\qdrant\storage"
if not exist "%TARGET_DIR%\nginx\html" mkdir "%TARGET_DIR%\nginx\html"
if not exist "%TARGET_DIR%\nginx\logs" mkdir "%TARGET_DIR%\nginx\logs"
if not exist "%TARGET_DIR%\fastapi\logs" mkdir "%TARGET_DIR%\fastapi\logs"

echo.
echo ====== 生成配置文件 ======

rem MySQL 配置
copy nul "%TARGET_DIR%\mysql\my.cnf" >nul
>> "%TARGET_DIR%\mysql\my.cnf" echo [mysqld]
>> "%TARGET_DIR%\mysql\my.cnf" echo character-set-server=utf8mb4
>> "%TARGET_DIR%\mysql\my.cnf" echo collation-server=utf8mb4_unicode_ci
>> "%TARGET_DIR%\mysql\my.cnf" echo default-time-zone=+08:00
>> "%TARGET_DIR%\mysql\my.cnf" echo max_connections=200
>> "%TARGET_DIR%\mysql\my.cnf" echo.
>> "%TARGET_DIR%\mysql\my.cnf" echo [client]
>> "%TARGET_DIR%\mysql\my.cnf" echo default-character-set=utf8mb4
>> "%TARGET_DIR%\mysql\my.cnf" echo.
>> "%TARGET_DIR%\mysql\my.cnf" echo [mysql]
>> "%TARGET_DIR%\mysql\my.cnf" echo default-character-set=utf8mb4
echo   OK mysql\my.cnf

rem Redis 配置
copy nul "%TARGET_DIR%\redis\conf\redis.conf" >nul
>> "%TARGET_DIR%\redis\conf\redis.conf" echo port 6379
>> "%TARGET_DIR%\redis\conf\redis.conf" echo requirepass 123456
>> "%TARGET_DIR%\redis\conf\redis.conf" echo dir /data
>> "%TARGET_DIR%\redis\conf\redis.conf" echo dbfilename dump.rdb
>> "%TARGET_DIR%\redis\conf\redis.conf" echo appendonly yes
>> "%TARGET_DIR%\redis\conf\redis.conf" echo appendfilename "appendonly.aof"
echo   OK redis\conf\redis.conf

rem Nginx 配置
copy nul "%TARGET_DIR%\nginx\nginx.conf" >nul
>> "%TARGET_DIR%\nginx\nginx.conf" echo user  nginx;
>> "%TARGET_DIR%\nginx\nginx.conf" echo worker_processes  auto;
>> "%TARGET_DIR%\nginx\nginx.conf" echo error_log  /var/log/nginx/error.log notice;
>> "%TARGET_DIR%\nginx\nginx.conf" echo pid        /run/nginx.pid;
>> "%TARGET_DIR%\nginx\nginx.conf" echo.
>> "%TARGET_DIR%\nginx\nginx.conf" echo events {
>> "%TARGET_DIR%\nginx\nginx.conf" echo     worker_connections  1024;
>> "%TARGET_DIR%\nginx\nginx.conf" echo }
>> "%TARGET_DIR%\nginx\nginx.conf" echo.
>> "%TARGET_DIR%\nginx\nginx.conf" echo http {
>> "%TARGET_DIR%\nginx\nginx.conf" echo     include       /etc/nginx/mime.types;
>> "%TARGET_DIR%\nginx\nginx.conf" echo     default_type  application/octet-stream;
>> "%TARGET_DIR%\nginx\nginx.conf" echo     sendfile        on;
>> "%TARGET_DIR%\nginx\nginx.conf" echo     keepalive_timeout  65;
>> "%TARGET_DIR%\nginx\nginx.conf" echo.
>> "%TARGET_DIR%\nginx\nginx.conf" echo     server {
>> "%TARGET_DIR%\nginx\nginx.conf" echo         listen       9050;
>> "%TARGET_DIR%\nginx\nginx.conf" echo         listen  [::]:9050;
>> "%TARGET_DIR%\nginx\nginx.conf" echo         server_name  localhost;
>> "%TARGET_DIR%\nginx\nginx.conf" echo.
>> "%TARGET_DIR%\nginx\nginx.conf" echo         location / {
>> "%TARGET_DIR%\nginx\nginx.conf" echo             root   /usr/share/nginx/html;
>> "%TARGET_DIR%\nginx\nginx.conf" echo             index  index.html index.htm;
>> "%TARGET_DIR%\nginx\nginx.conf" echo         }
>> "%TARGET_DIR%\nginx\nginx.conf" echo.
>> "%TARGET_DIR%\nginx\nginx.conf" echo         error_page   500 502 503 504  /50x.html;
>> "%TARGET_DIR%\nginx\nginx.conf" echo         location = /50x.html {
>> "%TARGET_DIR%\nginx\nginx.conf" echo             root   /usr/share/nginx/html;
>> "%TARGET_DIR%\nginx\nginx.conf" echo         }
>> "%TARGET_DIR%\nginx\nginx.conf" echo     }
>> "%TARGET_DIR%\nginx\nginx.conf" echo }
echo   OK nginx\nginx.conf

rem Docker Compose 配置（相对路径挂载）
copy nul "%TARGET_DIR%\em-com.yml" >nul
>> "%TARGET_DIR%\em-com.yml" echo services:
>> "%TARGET_DIR%\em-com.yml" echo   em-qdrant:
>> "%TARGET_DIR%\em-com.yml" echo     image: qdrant/qdrant:latest
>> "%TARGET_DIR%\em-com.yml" echo     container_name: em-qdrant
>> "%TARGET_DIR%\em-com.yml" echo     ports:
>> "%TARGET_DIR%\em-com.yml" echo       - "7333:6333"
>> "%TARGET_DIR%\em-com.yml" echo       - "7334:6334"
>> "%TARGET_DIR%\em-com.yml" echo     volumes:
>> "%TARGET_DIR%\em-com.yml" echo       - ./qdrant/storage:/qdrant/storage
>> "%TARGET_DIR%\em-com.yml" echo     environment:
>> "%TARGET_DIR%\em-com.yml" echo       - QDRANT__SERVICE__HTTP_PORT=6333
>> "%TARGET_DIR%\em-com.yml" echo       - QDRANT__SERVICE__GRPC_PORT=6334
>> "%TARGET_DIR%\em-com.yml" echo       - RUST_LOG=info
>> "%TARGET_DIR%\em-com.yml" echo     networks:
>> "%TARGET_DIR%\em-com.yml" echo       - EduMark-network
>> "%TARGET_DIR%\em-com.yml" echo     restart: unless-stopped
>> "%TARGET_DIR%\em-com.yml" echo.
>> "%TARGET_DIR%\em-com.yml" echo   em-redis:
>> "%TARGET_DIR%\em-com.yml" echo     image: redis
>> "%TARGET_DIR%\em-com.yml" echo     container_name: em-redis
>> "%TARGET_DIR%\em-com.yml" echo     ports:
>> "%TARGET_DIR%\em-com.yml" echo       - "7379:6379"
>> "%TARGET_DIR%\em-com.yml" echo     volumes:
>> "%TARGET_DIR%\em-com.yml" echo       - ./redis/data:/data
>> "%TARGET_DIR%\em-com.yml" echo       - ./redis/conf/redis.conf:/usr/local/etc/redis/redis.conf
>> "%TARGET_DIR%\em-com.yml" echo     command: redis-server /usr/local/etc/redis/redis.conf
>> "%TARGET_DIR%\em-com.yml" echo     networks:
>> "%TARGET_DIR%\em-com.yml" echo       - EduMark-network
>> "%TARGET_DIR%\em-com.yml" echo.
>> "%TARGET_DIR%\em-com.yml" echo   em-mysql:
>> "%TARGET_DIR%\em-com.yml" echo     image: mysql:8.0
>> "%TARGET_DIR%\em-com.yml" echo     container_name: em-mysql
>> "%TARGET_DIR%\em-com.yml" echo     ports:
>> "%TARGET_DIR%\em-com.yml" echo       - "7006:3306"
>> "%TARGET_DIR%\em-com.yml" echo     environment:
>> "%TARGET_DIR%\em-com.yml" echo       MYSQL_ALLOW_EMPTY_PASSWORD: "yes"
>> "%TARGET_DIR%\em-com.yml" echo       MYSQL_ROOT_PASSWORD: 123456
>> "%TARGET_DIR%\em-com.yml" echo     volumes:
>> "%TARGET_DIR%\em-com.yml" echo       - ./mysql/my.cnf:/etc/mysql/conf.d/my.cnf
>> "%TARGET_DIR%\em-com.yml" echo       - ./mysql/data:/var/lib/mysql
>> "%TARGET_DIR%\em-com.yml" echo       - ./schema.sql:/docker-entrypoint-initdb.d/schema.sql
>> "%TARGET_DIR%\em-com.yml" echo     networks:
>> "%TARGET_DIR%\em-com.yml" echo       - EduMark-network
>> "%TARGET_DIR%\em-com.yml" echo.
>> "%TARGET_DIR%\em-com.yml" echo   em-minio:
>> "%TARGET_DIR%\em-com.yml" echo     image: minio/minio:RELEASE.2025-04-22T22-12-26Z
>> "%TARGET_DIR%\em-com.yml" echo     container_name: em-minio
>> "%TARGET_DIR%\em-com.yml" echo     ports:
>> "%TARGET_DIR%\em-com.yml" echo       - "7090:9000"
>> "%TARGET_DIR%\em-com.yml" echo       - "7000:9001"
>> "%TARGET_DIR%\em-com.yml" echo     environment:
>> "%TARGET_DIR%\em-com.yml" echo       MINIO_ROOT_USER: minioadmin
>> "%TARGET_DIR%\em-com.yml" echo       MINIO_ROOT_PASSWORD: minioadmin
>> "%TARGET_DIR%\em-com.yml" echo     volumes:
>> "%TARGET_DIR%\em-com.yml" echo       - ./minio/data:/data
>> "%TARGET_DIR%\em-com.yml" echo       - ./minio/config:/root/.minio
>> "%TARGET_DIR%\em-com.yml" echo     command: server /data --console-address ":9001"
>> "%TARGET_DIR%\em-com.yml" echo     networks:
>> "%TARGET_DIR%\em-com.yml" echo       - EduMark-network
>> "%TARGET_DIR%\em-com.yml" echo.
>> "%TARGET_DIR%\em-com.yml" echo   em-nginx:
>> "%TARGET_DIR%\em-com.yml" echo     image: nginx:latest
>> "%TARGET_DIR%\em-com.yml" echo     container_name: em-nginx
>> "%TARGET_DIR%\em-com.yml" echo     ports:
>> "%TARGET_DIR%\em-com.yml" echo       - "7050:9050"
>> "%TARGET_DIR%\em-com.yml" echo     volumes:
>> "%TARGET_DIR%\em-com.yml" echo       - ./nginx/nginx.conf:/etc/nginx/nginx.conf
>> "%TARGET_DIR%\em-com.yml" echo       - ./nginx/html:/usr/share/nginx/html
>> "%TARGET_DIR%\em-com.yml" echo       - ./nginx/logs:/var/log/nginx
>> "%TARGET_DIR%\em-com.yml" echo     networks:
>> "%TARGET_DIR%\em-com.yml" echo       - EduMark-network
>> "%TARGET_DIR%\em-com.yml" echo.
>> "%TARGET_DIR%\em-com.yml" echo   em-fastapi:
>> "%TARGET_DIR%\em-com.yml" echo     image: edumark-fastapi:latest
>> "%TARGET_DIR%\em-com.yml" echo     container_name: em-fastapi
>> "%TARGET_DIR%\em-com.yml" echo     ports:
>> "%TARGET_DIR%\em-com.yml" echo       - "7080:8000"
>> "%TARGET_DIR%\em-com.yml" echo     volumes:
>> "%TARGET_DIR%\em-com.yml" echo       - ./fastapi/logs:/app/logs
>> "%TARGET_DIR%\em-com.yml" echo     build:
>> "%TARGET_DIR%\em-com.yml" echo       context: .
>> "%TARGET_DIR%\em-com.yml" echo       dockerfile: Dockerfile
>> "%TARGET_DIR%\em-com.yml" echo     depends_on:
>> "%TARGET_DIR%\em-com.yml" echo       - em-mysql
>> "%TARGET_DIR%\em-com.yml" echo       - em-redis
>> "%TARGET_DIR%\em-com.yml" echo       - em-qdrant
>> "%TARGET_DIR%\em-com.yml" echo       - em-minio
>> "%TARGET_DIR%\em-com.yml" echo     networks:
>> "%TARGET_DIR%\em-com.yml" echo       - EduMark-network
>> "%TARGET_DIR%\em-com.yml" echo     restart: unless-stopped
>> "%TARGET_DIR%\em-com.yml" echo.
>> "%TARGET_DIR%\em-com.yml" echo   em-celery-worker:
>> "%TARGET_DIR%\em-com.yml" echo     image: edumark-fastapi:latest
>> "%TARGET_DIR%\em-com.yml" echo     container_name: em-celery-worker
>> "%TARGET_DIR%\em-com.yml" echo     build:
>> "%TARGET_DIR%\em-com.yml" echo       context: .
>> "%TARGET_DIR%\em-com.yml" echo       dockerfile: Dockerfile
>> "%TARGET_DIR%\em-com.yml" echo     command: uv run celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
>> "%TARGET_DIR%\em-com.yml" echo     environment:
>> "%TARGET_DIR%\em-com.yml" echo       C_FORCE_ROOT: "1"
>> "%TARGET_DIR%\em-com.yml" echo     volumes:
>> "%TARGET_DIR%\em-com.yml" echo       - ./fastapi/logs:/app/logs
>> "%TARGET_DIR%\em-com.yml" echo     depends_on:
>> "%TARGET_DIR%\em-com.yml" echo       - em-redis
>> "%TARGET_DIR%\em-com.yml" echo       - em-mysql
>> "%TARGET_DIR%\em-com.yml" echo       - em-qdrant
>> "%TARGET_DIR%\em-com.yml" echo       - em-minio
>> "%TARGET_DIR%\em-com.yml" echo     networks:
>> "%TARGET_DIR%\em-com.yml" echo       - EduMark-network
>> "%TARGET_DIR%\em-com.yml" echo     restart: unless-stopped
>> "%TARGET_DIR%\em-com.yml" echo.
>> "%TARGET_DIR%\em-com.yml" echo networks:
>> "%TARGET_DIR%\em-com.yml" echo   EduMark-network:
>> "%TARGET_DIR%\em-com.yml" echo     name: EduMark-network
>> "%TARGET_DIR%\em-com.yml" echo     driver: bridge
echo   OK em-com.yml

rem 复制 schema.sql（从 docs 或 app/models 查找）
if exist "%PROJECT_DIR%\docs\schema.sql" (
    copy "%PROJECT_DIR%\docs\schema.sql" "%TARGET_DIR%\schema.sql" >nul
    echo   OK schema.sql
) else if exist "%PROJECT_DIR%\app\models\schema.sql" (
    copy "%PROJECT_DIR%\app\models\schema.sql" "%TARGET_DIR%\schema.sql" >nul
    echo   OK schema.sql
)


echo.
echo 所有配置文件生成完毕！
echo.
echo 请将 %TARGET_DIR% 整个目录复制到 Linux 服务器
echo.
echo 然后在服务器上执行:
echo.
echo   cd /path/to/EduMark
echo.
echo   docker-compose -f em-com.yml up -d
echo.
pause