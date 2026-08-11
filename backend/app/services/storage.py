from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.models.user import UserInDB, UserCreate
from app.models.article import ArticleInDB, ArticleCreate
from app.models.interaction import InteractionInDB, InteractionCreate
from app.models.source_credibility import SourceCredibilityInDB, SourceCredibilityCreate
from typing import List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.client[settings.DATABASE_NAME]
        self.users = self.db.users
        self.articles = self.db.articles
        self.interactions = self.db.interactions
        self.source_credibility = self.db.source_credibility

    async def ensure_indexes(self):
        """Create indexes needed for data integrity (safe to call repeatedly)."""
        try:
            await self.users.create_index("email", unique=True)
        except Exception as exc:
            logger.warning(f"Could not ensure users.email unique index: {exc}")

    # User methods
    async def create_user(self, user: UserCreate) -> UserInDB:
        from app.core.security import get_password_hash
        hashed_password = get_password_hash(user.password)
        user_dict = user.dict()
        user_dict["hashed_password"] = hashed_password
        del user_dict["password"]
        result = await self.users.insert_one(user_dict)
        user_dict["_id"] = str(result.inserted_id)
        return UserInDB(**user_dict)

    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        user_doc = await self.users.find_one({"email": email})
        if user_doc:
            user_doc["_id"] = str(user_doc["_id"])
            return UserInDB(**user_doc)
        return None

    async def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        from bson import ObjectId
        user_doc = await self.users.find_one({"_id": ObjectId(user_id)})
        if user_doc:
            user_doc["_id"] = str(user_doc["_id"])
            return UserInDB(**user_doc)
        return None

    async def update_user_by_email(self, email: str, update_data: dict) -> Optional[UserInDB]:
        update_data["updated_at"] = datetime.utcnow()
        await self.users.update_one(
            {"email": email},
            {"$set": update_data}
        )
        return await self.get_user_by_email(email)

    async def delete_user_by_email(self, email: str) -> bool:
        """Permanently delete a user account. Returns True if a document was deleted."""
        result = await self.users.delete_one({"email": email})
        return result.deleted_count > 0

    # Article methods
    async def create_article(self, article: ArticleCreate) -> ArticleInDB:
        result = await self.articles.insert_one(article.dict())
        article_dict = article.dict()
        article_dict["_id"] = str(result.inserted_id)
        return ArticleInDB(**article_dict)

    async def get_article_by_id(self, article_id: str) -> Optional[ArticleInDB]:
        from bson import ObjectId
        article_doc = await self.articles.find_one({"_id": ObjectId(article_id)})
        if article_doc:
            article_doc["_id"] = str(article_doc["_id"])
            return ArticleInDB(**article_doc)
        return None

    async def get_article_by_url(self, url: str) -> Optional[ArticleInDB]:
        article_doc = await self.articles.find_one({"url": url})
        if article_doc:
            article_doc["_id"] = str(article_doc["_id"])
            return ArticleInDB(**article_doc)
        return None

    async def get_articles_by_status(self, status: str, limit: int = 100) -> List[ArticleInDB]:
        cursor = self.articles.find({"processing_status": status}).limit(limit)
        articles = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            articles.append(ArticleInDB(**doc))
        return articles

    async def get_latest_articles(self, limit: int = 50, topic: Optional[str] = None) -> List[ArticleInDB]:
        """Return the most recently published completed articles, newest first."""
        query = {"processing_status": "completed"}
        if topic and topic.lower() != "all":
            query["topic"] = topic
        cursor = self.articles.find(query).sort("published_date", -1).limit(limit)
        articles = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            articles.append(ArticleInDB(**doc))
        return articles

    async def get_latest_articles_for_topics(self, topics: List[str], limit: int = 10) -> List[ArticleInDB]:
        """Return the most recent completed articles matching any of the
        given topics (case-sensitive match against the stored topic field).
        If `topics` is empty, falls back to the latest articles overall so
        callers (e.g. email digests) always have something to send."""
        query = {"processing_status": "completed"}
        if topics:
            query["topic"] = {"$in": topics}
        cursor = self.articles.find(query).sort("published_date", -1).limit(limit)
        articles = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            articles.append(ArticleInDB(**doc))
        return articles

    async def count_articles(self) -> int:
        return await self.articles.count_documents({})

    async def update_article_status(self, article_id: str, status: str, processed_at: Optional[datetime] = None):
        from bson import ObjectId
        from datetime import datetime
        update_dict = {"processing_status": status}
        if processed_at:
            update_dict["processed_at"] = processed_at
        else:
            update_dict["processed_at"] = datetime.utcnow()
        await self.articles.update_one(
            {"_id": ObjectId(article_id)},
            {"$set": update_dict}
        )

    async def update_article_fields(self, article_id: str, update_data: dict):
        from bson import ObjectId
        await self.articles.update_one(
            {"_id": ObjectId(article_id)},
            {"$set": update_data}
        )

    # Interaction methods
    async def create_interaction(self, interaction: InteractionCreate) -> InteractionInDB:
        result = await self.interactions.insert_one(interaction.dict())
        interaction_dict = interaction.dict()
        interaction_dict["_id"] = str(result.inserted_id)
        return InteractionInDB(**interaction_dict)

    async def get_interactions_by_user_and_article(self, user_id: str, article_id: str) -> List[InteractionInDB]:
        cursor = self.interactions.find({"user_id": user_id, "article_id": article_id})
        interactions = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            interactions.append(InteractionInDB(**doc))
        return interactions

    # Source credibility methods
    async def create_source_credibility(self, source: SourceCredibilityCreate) -> SourceCredibilityInDB:
        result = await self.source_credibility.insert_one(source.dict())
        source_dict = source.dict()
        source_dict["_id"] = str(result.inserted_id)
        return SourceCredibilityInDB(**source_dict)

    async def get_source_credibility_by_domain(self, domain: str) -> Optional[SourceCredibilityInDB]:
        source_doc = await self.source_credibility.find_one({"domain": domain})
        if source_doc:
            source_doc["_id"] = str(source_doc["_id"])
            return SourceCredibilityInDB(**source_doc)
        return None

    async def get_all_source_credibility(self) -> List[SourceCredibilityInDB]:
        cursor = self.source_credibility.find()
        sources = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            sources.append(SourceCredibilityInDB(**doc))
        return sources

storage_service = StorageService()