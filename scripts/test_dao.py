"""
DAO 测试
用法: PYTHONIOENCODING=utf-8 .venv/Scripts/python -m scripts.test_dao
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.response import PageVO
from app.dao.user_dao import UserDAO
from app.dao.task_dao import TaskDAO
from app.dao.model_dao import ModelDAO
from app.models.user import User
from app.models.task import Task
from app.models.model import Model

# 读 .env
env_path = Path(__file__).resolve().parent.parent / ".env"
env_vars = {}
with open(env_path, encoding="utf-8") as f:
    for line in f:
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            env_vars[k.strip()] = v.strip()

engine = create_engine(
    f"mysql+pymysql://{env_vars['DB_USER']}:{env_vars['DB_PASSWORD']}"
    f"@{env_vars['DB_HOST']}:{env_vars['DB_PORT']}/{env_vars['DB_NAME']}?charset=utf8mb4",
    echo=False,
)

with Session(engine) as session:
    user_dao = UserDAO(session)
    task_dao = TaskDAO(session)
    model_dao = ModelDAO(session)

    # ---- create ----
    u = User(account="daotest", username="DAOTest", password="pwd", role="student")
    u = user_dao.create(u)
    print(f"[UserDAO] create   → id={u.id}, account={u.account}")

    t = Task(task_id="dao-uuid-001", user_id=u.id, mode="aliyun", status="pending")
    t = task_dao.create(t)
    print(f"[TaskDAO] create   → id={t.id}, task_id={t.task_id}")

    # ---- get_by_id ----
    found = user_dao.get_by_id(u.id)
    print(f"[UserDAO] get_by_id → id={found.id}, username={found.username}")

    # ---- get_by_account (custom) ----
    by_acct = user_dao.get_by_account("daotest")
    print(f"[UserDAO] get_by_account → {by_acct.account}")

    # ---- update ----
    t = task_dao.update(t.id, {"status": "completed"})
    print(f"[TaskDAO] update   → status={t.status}")

    # ---- list (paginated) ----
    page = user_dao.list(page=1, page_size=10)
    print(f"[UserDAO] list     → total={page.total}, rows={len(page.rows)}")

    # ---- delete ----
    ok = task_dao.delete(t.id)
    print(f"[TaskDAO] delete   → {ok}")

    session.rollback()
    print("[OK] 全部 DAO 测试通过（已回滚）")
