from app.db.session import SessionLocal
from app.infrastructure.db.repositories.topic_repository import TopicRepository
from app.infrastructure.db.repositories.word_query_repository import WordQueryRepository
from app.infrastructure.db.repositories.word_repository import WordRepository


class UnitOfWork:
    def __init__(self) -> None:
        self.session = None
        self.words: WordRepository | None = None
        self.topics: TopicRepository | None = None
        self.word_queries: WordQueryRepository | None = None

    async def __aenter__(self) -> "UnitOfWork":
        self.session = SessionLocal()
        self.words = WordRepository(self.session)
        self.topics = TopicRepository(self.session)
        self.word_queries = WordQueryRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.session is None:
            return
        if exc:
            await self.session.rollback()
        await self.session.close()

    async def commit(self) -> None:
        if self.session is not None:
            await self.session.commit()

    async def rollback(self) -> None:
        if self.session is not None:
            await self.session.rollback()
