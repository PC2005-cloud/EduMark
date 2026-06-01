"""
数据库连接测试 & 初始化
用法: PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/test_db.py
"""

from pathlib import Path

import pymysql
from pymysql.constants import ER

# 读取 .env
env_path = Path(__file__).resolve().parent.parent / ".env"
env_vars = {}
with open(env_path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env_vars[k.strip()] = v.strip()

DB = env_vars.get("DB_NAME", "edumark")

# 先连 MySQL（不指定库），建库
conn = pymysql.connect(
    host=env_vars.get("DB_HOST", "localhost"),
    port=int(env_vars.get("DB_PORT", 7006)),
    user=env_vars.get("DB_USER", "root"),
    password=env_vars.get("DB_PASSWORD", "123456"),
    charset="utf8mb4",
)
with conn.cursor() as cur:
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB}` DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci")
    print(f"[OK] 数据库 `{DB}` 就绪")
conn.close()

# 再连指定库，建表
conn = pymysql.connect(
    host=env_vars.get("DB_HOST", "localhost"),
    port=int(env_vars.get("DB_PORT", 7006)),
    user=env_vars.get("DB_USER", "root"),
    password=env_vars.get("DB_PASSWORD", "123456"),
    database=DB,
    charset="utf8mb4",
)
with conn.cursor() as cur:
    cur.execute("SELECT VERSION()")
    print(f"[OK] MySQL 版本: {cur.fetchone()[0]}")

    # 执行 schema.sql
    schema_path = Path(__file__).resolve().parent.parent / "app" / "models" / "schema.sql"
    if schema_path.exists():
        raw = schema_path.read_text(encoding="utf-8")
        # 去除注释行和空行
        lines = []
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("--") or stripped.startswith("/*"):
                continue
            lines.append(line)
        # 按分号拆分并逐条执行
        for stmt in "".join(lines).split(";"):
            stmt = stmt.strip()
            if not stmt or stmt.upper().startswith("USE"):
                continue
            try:
                cur.execute(stmt)
            except pymysql.err.OperationalError as e:
                if e.args[0] == ER.TABLE_EXISTS_ERROR:
                    continue
                raise
        conn.commit()
        print("[OK] 建表完成")

    cur.execute("SHOW TABLES")
    tables = [t[0] for t in cur.fetchall()]
    print(f"   表 ({len(tables)}): {', '.join(tables)}")

conn.close()
print("[OK] 完成")
