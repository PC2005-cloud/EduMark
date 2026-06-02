from sqlalchemy.orm import Session

from app.dao import BaseDAO
from app.models.task import Task


class TaskDAO(BaseDAO[Task]):
    def __init__(self, db: Session):
        super().__init__(db, Task)

    def get_by_task_id(self, task_id: str) -> Task | None:
        return self.db.query(Task).filter(Task.task_id == task_id).first()

    def list_by_user_id(self, user_id: int, page: int = 1, page_size: int = 10):
        return self.list(page=page, page_size=page_size, user_id=user_id)

    def cascade_delete(self, task_id: str):
        from app.dao.image_dao import ImageDAO
        from app.dao.question_dao import QuestionDAO
        from app.dao.block_dao import BlockDAO
        from app.dao.correction_dao import CorrectionDAO
        from app.clients.minio import minio_client
        from app.models.question_chunk import QuestionChunk

        task = self.get_by_task_id(task_id)
        if not task:
            return

        for q in QuestionDAO(self.db).list_by_task_id(task_id):
            self.db.query(QuestionChunk).filter(QuestionChunk.question_id == q.id).delete()
            for b in BlockDAO(self.db).list_by_question_id(q.id):
                BlockDAO(self.db).delete(b.id)
            c = CorrectionDAO(self.db).get_by_question_id(q.id)
            if c:
                CorrectionDAO(self.db).delete(c.id)
            QuestionDAO(self.db).delete(q.id)

        for img in ImageDAO(self.db).list_by_task_id(task_id):
            try:
                minio_client.delete(img.url)
            except Exception:
                pass
            ImageDAO(self.db).delete(img.id)

        self.delete(task.id)
