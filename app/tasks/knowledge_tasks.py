import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy.orm import Session

from app.clients.mineru import mineru_client, ContentType
from app.clients.minio import minio_client
from app.clients.bailian import bailian
from app.clients.qdrant import qdrant
from app.dao.knowledge_dao import KnowledgeDAO
from app.models import SessionLocal
from app.tasks.celery_app import celery_app
from qdrant_client.http.models import PointStruct

logger = logging.getLogger(__name__)

_MAX_WORKERS = 10


@celery_app.task(bind=True, max_retries=3)
def knowledge_parse(self, knowledge_id: int) -> int:
    logger.info("知识解析任务开始: knowledge_id=%d", knowledge_id)
    db: Session = SessionLocal()

    try:
        # 1. 查记录
        knowledge = KnowledgeDAO(db).get_by_id(knowledge_id)
        if not knowledge:
            raise ValueError(f"Knowledge 记录不存在: {knowledge_id}")
        knowledge.status = "parsing"
        db.commit()
        logger.info("Knowledge 记录: title=%s url=%s subject=%s", knowledge.title, knowledge.url, knowledge.subject)

        # 2. 从 MinIO 下载文件
        file_data = minio_client.download(knowledge.url)
        logger.info("文件已下载: %s size=%d", knowledge.url, len(file_data))

        # 3. MinerU 上传解析
        batch_id = mineru_client.upload_and_parse(file_data, knowledge.title)
        logger.info("MinerU 提交成功: batch_id=%s", batch_id)

        # 4. 轮询
        deadline = time.time() + 1800
        while True:
            result = mineru_client.get_zip_urls(batch_id)
            if result.success:
                break
            if time.time() > deadline:
                raise TimeoutError("MinerU 解析超时")
            time.sleep(5)

        # 5. 解析结果
        items = mineru_client.handle_parse_result(result.zip_urls, process_images=True)

        # 6. 分块（父子结构）+ 向量化 + 写入 Qdrant
        import re
        texts = []
        for item in items:
            if item.type == ContentType.TEXT and item.text:
                texts.append(item.text)

        qdrant.ensure_collection()
        points = []

        # 收集所有文本（父子两级）及元数据，text 统一在 index 3
        _MAX_EMBED_LEN = 2000
        entries = []
        for i, text in enumerate(texts):
            pid = int(f"{knowledge_id}{i:04d}")
            entries.append(("parent", i, pid, text[:_MAX_EMBED_LEN]))
            sentences = [s.strip() for s in re.split(r'[。！？\n]+', text) if len(s.strip()) > 10]
            for j, sent in enumerate(sentences):
                cid = int(f"{knowledge_id}{i:04d}_{j:04d}")
                entries.append(("child", i, cid, sent[:_MAX_EMBED_LEN], pid, j))

        # 按 API 限额（10 条/批）拆成多个 chunk，多线程并发 embedding
        _BATCH_SIZE = 10
        _MAX_WORKERS_EMBED = 10
        _MAX_RETRIES = 3
        chunks = [entries[i:i + _BATCH_SIZE] for i in range(0, len(entries), _BATCH_SIZE)]
        total = len(chunks)
        logger.info("向量化开始: 共 %d 条文本, %d 批, %d 线程并发", len(entries), total, _MAX_WORKERS_EMBED)
        all_vectors = [None] * len(entries)

        def embed_with_retry(texts: list[str]) -> list[list[float]]:
            last_err = None
            for attempt in range(1, _MAX_RETRIES + 1):
                try:
                    return bailian.embed(texts)
                except Exception as e:
                    last_err = e
                    logger.warning("向量化失败(第%d次重试): %s", attempt, e)
                    if attempt < _MAX_RETRIES:
                        time.sleep(attempt * 2)
            raise last_err

        with ThreadPoolExecutor(max_workers=_MAX_WORKERS_EMBED) as executor:
            fut_offset = {}
            off = 0
            for chunk in chunks:
                fut = executor.submit(embed_with_retry, [e[3] for e in chunk])
                fut_offset[fut] = off
                off += len(chunk)

            done = 0
            for fut in as_completed(fut_offset):
                done += 1
                off = fut_offset[fut]
                vecs = fut.result()
                for i, v in enumerate(vecs):
                    all_vectors[off + i] = v
                logger.info("向量化进度: %d/%d 批完成", done, total)

        if any(v is None for v in all_vectors):
            raise RuntimeError("部分向量化失败")
        vectors = all_vectors

        for entry, vec in zip(entries, vectors):
            if entry[0] == "parent":
                _, i, pid, t = entry
                points.append(PointStruct(
                    id=pid, vector=vec,
                    payload={
                        "document_id": knowledge_id,
                        "content": t[:2000],
                        "subject": knowledge.subject or "",
                        "grade": knowledge.grade or "",
                        "seq_in_doc": i,
                        "node_type": "parent",
                        "parent_id": 0,
                    },
                ))
            else:
                _, i, cid, sent, pid, j = entry
                points.append(PointStruct(
                    id=cid, vector=vec,
                    payload={
                        "document_id": knowledge_id,
                        "content": sent[:2000],
                        "subject": knowledge.subject or "",
                        "grade": knowledge.grade or "",
                        "node_type": "child",
                        "parent_id": pid,
                        "child_seq": j,
                    },
                ))

        if points:
            _BATCH_UPSERT = 100
            for i in range(0, len(points), _BATCH_UPSERT):
                qdrant.upsert(points[i:i + _BATCH_UPSERT])

        # 7. 更新 Knowledge 记录
        knowledge = KnowledgeDAO(db).get_by_id(knowledge_id)
        if knowledge:
            knowledge.status = "completed"
            knowledge.chunk = len(points)
            db.commit()

        logger.info("知识解析完成: knowledge_id=%d chunks=%d", knowledge_id, len(points))
        return knowledge_id

    except Exception as e:
        logger.error("知识解析失败: %s", e, exc_info=True)
        db.rollback()
        kn = KnowledgeDAO(db).get_by_id(knowledge_id)
        if kn:
            kn.status = "failed"
            db.commit()
        raise
    finally:
        db.close()
