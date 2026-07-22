import asyncio
import uuid
from datetime import datetime, UTC
from typing import Any
from threading import Lock
from enum import StrEnum
from fastembed import TextEmbedding
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.conversions import common_types as types
from qdrant_client.http import models as rest_models
from rag_packages.contracts.dto.shared_dto import BaseDTO
from rag_packages.contracts.dto.vector_document import CreateVectorDocumentRequest

# for use in packages importing this module
from qdrant_client.conversions.common_types import ScoredPoint


# # * equivalent types
# types.QueryResponse
# rest_models.QueryResponse


class CollectionPayload(BaseDTO):
    payload: CreateVectorDocumentRequest | None = None
    vector: list[float] | list[list[float]] | None = None


class UploadMethod(StrEnum):
    UPSERT = "upsert"
    UPLOAD = "upload"


class QdrantServiceConfig(BaseDTO):
    collection_name: str = "documents"
    host: str
    port: int | None = None
    grpc_port: int | None = None
    batch_size: int = 100
    concurrent_batches: int = 5


class QdrantService:
    def __init__(self, config: QdrantServiceConfig):
        self._lock = Lock()
        self.client: AsyncQdrantClient | None = None
        self.collection_name = config.collection_name
        self.config = config
        self._semaphore = asyncio.Semaphore(self.config.concurrent_batches)
        self.service_name = f"qdrant-service-{self.collection_name}"
        self.model_name = "BAAI/bge-base-en"
        self.embedding_model = TextEmbedding(
            model_name=self.model_name,
            lazy_load=True,
        )
        self._vector_params_lock = Lock()
        self.vector_params: models.VectorParams | None = None

    def get_client(self) -> AsyncQdrantClient:
        if self.client is not None:
            return self.client

        with self._lock:
            if self.client is not None:
                return self.client

            if self.config.grpc_port is not None:
                self.client = AsyncQdrantClient(
                    host=self.config.host,
                    grpc_port=self.config.grpc_port,
                    prefer_grpc=True,
                )
            else:
                self.client = AsyncQdrantClient(
                    host=self.config.host, port=self.config.port
                )

        return self.client

    async def get_vector_params(
        self, client: AsyncQdrantClient | None = None
    ) -> models.VectorParams:
        if self.vector_params is not None:
            return self.vector_params

        with self._vector_params_lock:
            if self.vector_params is not None:
                return self.vector_params

            client = client or self.get_client()
            size = client.get_embedding_size(self.model_name)

            self.vector_params = models.VectorParams(
                size=size, distance=models.Distance.COSINE
            )

        return self.vector_params

    async def create_collection(self, recreate: bool = False) -> bool:
        client = self.get_client()
        vector_params = await self.get_vector_params(client)

        if recreate:
            return await client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=vector_params,
            )
            
        collection_response = await client.get_collections()
        collections = collection_response.collections

        exists = any(c.name == self.collection_name for c in collections)
        if exists:
            return True

        return await client.create_collection(
            collection_name=self.collection_name,
            vectors_config=vector_params,
        )

    async def generate_vector_embeddings(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            raise ValueError(
                f"[{self.service_name}] texts are required to generate embeddings."
            )

        # NOTE: if unstable under heavy concurrency, protect embedding calls with an asyncio.Lock or use a small worker pool.
        embeddings = await asyncio.to_thread(
            lambda: [
                embedding.tolist() for embedding in self.embedding_model.embed(texts)
            ]
        )
        if not embeddings:
            raise ValueError(
                f"[{self.service_name}] Failed to generate embeddings for the supplied texts."
            )

        return embeddings

    def get_point(self, item: CollectionPayload, index: int) -> models.PointStruct:
        if item.payload is None:
            raise ValueError(f"[{self.service_name}] Collection payload is required.")

        if item.vector is None:
            raise ValueError(f"[{self.service_name}] Vector embedding is required.")

        vector = item.vector

        item.payload.chunk_id = item.payload.chunk_id or index
        payload = item.payload.model_dump()

        point = models.PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload=payload,
        )
        return point

    def get_points(self, items: list[CollectionPayload]) -> list[models.PointStruct]:
        points = [self.get_point(item, idx) for idx, item in enumerate(items)]
        return points

    async def upsert_points(
        self,
        points: list[models.PointStruct],
        method: UploadMethod = UploadMethod.UPSERT,
    ) -> types.UpdateResult | None:
        client = self.get_client()

        async with self._semaphore:
            match method:
                case UploadMethod.UPSERT:
                    result = await client.upsert(
                        collection_name=self.collection_name,
                        points=points,
                    )
                case UploadMethod.UPLOAD:
                    result = await client.upload_collection(
                        collection_name=self.collection_name,
                        points=points,
                    )
                case _:
                    raise ValueError(
                        f"[{self.service_name}] Invalid upload method: {method}"
                    )

        return result

    async def add_chunks_to_collection(
        self, chunks: list[CreateVectorDocumentRequest]
    ) -> list[types.UpdateResult]:
        initiated_at = datetime.now(tz=UTC)

        valid_chunks: list[CreateVectorDocumentRequest] = []
        for chunk in chunks:
            if not chunk.text.strip():
                continue

            # ? the chunk mutation is intentional and doesn't change it's usage
            chunk.text = chunk.text.strip()
            chunk.initiated_at = chunk.initiated_at or initiated_at
            valid_chunks.append(chunk)

        if not valid_chunks:
            raise ValueError(
                f"[{self.service_name}] No valid chunks to add to the collection."
            )

        vectors = await self.generate_vector_embeddings(
            [chunk.text for chunk in valid_chunks]
        )

        if len(vectors) != len(valid_chunks):
            raise RuntimeError(
                f"[{self.service_name}] Embedding count does not match the number of valid chunks: {len(vectors)} != {len(valid_chunks)}."
            )

        payload_list = [
            CollectionPayload(payload=chunk, vector=vector)
            for chunk, vector in zip(valid_chunks, vectors)
        ]
        points = self.get_points(payload_list)
        batched_points = [
            points[i : i + self.config.batch_size]
            for i in range(0, len(points), self.config.batch_size)
        ]

        # # use this instead if asyncio.gather causes performance issues
        # results = [await self.upsert_points(batch) for batch in batched_points]

        # use asyncio.gather to run upsert_points concurrently for each batch
        results = await asyncio.gather(
            *(self.upsert_points(batch) for batch in batched_points)
        )

        valid_results = [result for result in results if result is not None]

        # ? empty array is fine, as long as there is no error
        return valid_results

    async def get_matching_vectors(
        self,
        query_vector: list[float] | list[list[float]] | None = None,
        limit: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> rest_models.QueryResponse:
        """
        Search for matching vectors in the collection based on the provided query vector and optional filters.

        Args:
            query_vector (list[float] | list[list[float]] | None): The query vector(s) to search for. If None, only filters will be applied.
            limit (int): The maximum number of results to return. Default is 5.
            filters (dict[str, Any] | None): Optional filters to apply to the search.

        Returns:
            rest_models.QueryResponse: The response containing the matching vectors and their metadata.
        """

        client = self.get_client()

        if query_vector is None and filters is None:
            raise ValueError(
                f"[{self.service_name}] query_vector or filters is required for vector search."
            )

        filters = filters or {}

        # # ? example
        # condition = models.FieldCondition(
        #     # Condition based on values of `rand_number` field.
        #     key="rand_number",
        #     # Select only those results where `rand_number` >= 3
        #     range=models.Range(gte=3),
        #     # match=models.MatchValue(value=3),
        # )

        conditions = [
            models.FieldCondition(key=key, match=models.MatchValue(value=value))
            for key, value in filters.items()
        ]
        query_filter = models.Filter(must=conditions) if conditions else None

        hits = await client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,  # Return [limit] closest points
        )
        return hits

    async def search(
        self,
        query: str | list[str] | None = None,
        limit: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[types.ScoredPoint]:

        if query is None and filters is None:
            raise ValueError(
                f"[{self.service_name}] query or filters is required for vector search."
            )

        is_list = isinstance(query, list)
        query_vector: list[float] | list[list[float]] | None = None

        if query is not None and not is_list:
            query = [query]

        query_vector = await self.generate_vector_embeddings(query)
        if query_vector is not None:
            query_vector = query_vector if is_list else query_vector[0]

        hits: rest_models.QueryResponse = await self.get_matching_vectors(
            query_vector=query_vector,
            limit=limit,
            filters=filters,
        )
        points = hits.points
        return points

    async def remove_vectors_by_filter(
        self, filters: dict[str, Any]
    ) -> types.UpdateResult:
        client = self.get_client()

        conditions = [
            models.FieldCondition(key=key, match=models.MatchValue(value=value))
            for key, value in filters.items()
        ]
        query_filter = models.Filter(must=conditions) if conditions else None

        result = await client.delete(
            collection_name=self.collection_name,
            filter=query_filter,
        )
        return result

    async def remove_points_by_ids(self, point_ids: list[str]) -> types.UpdateResult:
        client = self.get_client()
        result = await client.delete(
            collection_name=self.collection_name,
            points=point_ids,
        )
        return result

    async def delete_collection(self) -> bool:
        client = self.get_client()
        result = await client.delete_collection(
            collection_name=self.collection_name,
        )
        return result

    async def close(self):
        if self.client is None:
            return

        await self.client.close()
