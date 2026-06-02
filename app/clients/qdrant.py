import logging
from dataclasses import dataclass

from qdrant_client import QdrantClient as _QdrantClient
from qdrant_client.http.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class CollectionInfo:
    name: str
    status: str
    points_count: int
    segments_count: int


class QdrantClient:
    def __init__(self):
        self._client = _QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_HTTP_PORT,
            grpc_port=settings.QDRANT_GRPC_PORT,
            api_key=settings.QDRANT_API_KEY or None,
        )
        self._collection = settings.QDRANT_COLLECTION
        logger.info("Qdrant 客户端初始化: host=%s port=%d collection=%s",
                     settings.QDRANT_HOST, settings.QDRANT_HTTP_PORT, self._collection)

    def ensure_collection(self, vector_size: int = 1536, distance: Distance = Distance.COSINE):
        logger.info("检查 collection: %s", self._collection)
        if self._client.collection_exists(self._collection):
            logger.debug("collection 已存在: %s", self._collection)
            return
        self._client.create_collection(
            collection_name=self._collection,
            vectors_config=VectorParams(size=vector_size, distance=distance),
        )
        logger.info("创建 collection: %s size=%d distance=%s", self._collection, vector_size, distance.name)

    def upsert(self, points: list[PointStruct]):
        logger.info("写入向量: %s 条", len(points))
        self._client.upsert(collection_name=self._collection, points=points)
        logger.info("写入成功: %d 条", len(points))

    def search(self, query_vector: list[float], top_k: int = 10,
               score_threshold: float | None = None,
               filter_conditions: dict | None = None):
        logger.info("搜索向量: top_k=%d filter=%s", top_k, filter_conditions)
        _filter = None
        if filter_conditions:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filter_conditions.items()
            ]
            _filter = Filter(must=conditions)

        result = self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            query_filter=_filter,
        )
        logger.info("搜索完成: %d 条结果", len(result.points))
        return result.points

    def delete(self, filter_conditions: dict):
        logger.info("删除向量: filter=%s", filter_conditions)
        conditions = [
            FieldCondition(key=k, match=MatchValue(value=v))
            for k, v in filter_conditions.items()
        ]
        self._client.delete(
            collection_name=self._collection,
            points_selector=Filter(must=conditions),
        )
        logger.info("删除完成: filter=%s", filter_conditions)

    def delete_collection(self):
        logger.info("删除 collection: %s", self._collection)
        self._client.delete_collection(self._collection)
        logger.info("删除完成: %s", self._collection)

    def collection_info(self) -> CollectionInfo:
        info = self._client.get_collection(self._collection)
        ci = CollectionInfo(
            name=self._collection,
            status=str(info.status),
            points_count=info.points_count,
            segments_count=info.segments_count,
        )
        logger.debug("collection 信息: %s", ci)
        return ci


qdrant = QdrantClient()
