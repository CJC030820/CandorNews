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

        try:
            # Enforce uniqueness on article URL at the database level. This is
            # the authoritative guard against duplicate articles: even if two
            # fetch cycles overlap (e.g. the background worker's startup run
            # racing with a manual "Refresh News" click or the scheduled email
            # job's pre-send refresh), MongoDB itself will reject the second
            # insert instead of silently creating a duplicate row.
            await self.articles.create_index("url", unique=True)
        except Exception as exc:
            logger.warning(f"Could not ensure articles.url unique index: {exc}")

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
    async def create_article(self, article: ArticleCreate) -> Optional[ArticleInDB]:
        """Insert a new article. Returns None (instead of raising) if an
        article with the same URL already exists, so callers can treat this
        as a normal "already ingested, skip it" outcome rather than a crash -
        this is what actually prevents duplicate news from ever being stored,
        even if two fetch cycles run concurrently."""
        from pymongo.errors import DuplicateKeyError
        try:
            result = await self.articles.insert_one(article.dict())
        except DuplicateKeyError:
            logger.info(f"Skipping duplicate article (URL already exists): {article.url}")
            return None
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
        """Return the most recently published completed articles, newest first.
        If `topic` is given, matches against either the primary `topic` field
        or the `topics` array (an article can belong to up to 3 categories)."""
        query = {"processing_status": "completed"}
        if topic and topic.lower() != "all":
            query["$or"] = [{"topic": topic}, {"topics": topic}]
        cursor = self.articles.find(query).sort("published_date", -1).limit(limit)
        articles = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            articles.append(ArticleInDB(**doc))
        return articles

    async def get_latest_articles_for_topics(self, topics: List[str], limit: int = 10) -> List[ArticleInDB]:
        """Return the most recent completed articles matching any of the
        given topics, checking both the primary `topic` field and the
        `topics` array (an article can belong to up to 3 categories).
        If `topics` is empty, falls back to the latest articles overall so
        callers (e.g. email digests) always have something to send."""
        query = {"processing_status": "completed"}
        if topics:
            query["$or"] = [{"topic": {"$in": topics}}, {"topics": {"$in": topics}}]
        cursor = self.articles.find(query).sort("published_date", -1).limit(limit)
        articles = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            articles.append(ArticleInDB(**doc))
        return articles

    async def count_articles(self) -> int:
        return await self.articles.count_documents({})

    async def find_articles_by_keywords(self, keywords: List[str], exclude_url: str, hours: int = 72, limit: int = 15) -> List[ArticleInDB]:
        """Find recently-ingested articles (from any source) sharing at
        least one extracted keyword with the given article, excluding the
        article itself. Used for real cross-source corroboration: if
        multiple independent outlets are reporting the same story, that's
        strong evidence it actually happened, and trust score should reflect
        that instead of staying flat around a default midpoint."""
        if not keywords:
            return []
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        query = {
            "keywords": {"$in": keywords},
            "url": {"$ne": exclude_url},
            "published_date": {"$gte": cutoff},
            "processing_status": "completed"
        }
        cursor = self.articles.find(query).limit(limit)
        articles = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            articles.append(ArticleInDB(**doc))
        return articles

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

    async def seed_source_credibility(self):
        """Populate known source credibility scores if the collection is
        empty. Without this, every article gets the flat 0.5 (50%) default
        reputation score regardless of how reputable the outlet actually is,
        which is why trust scores previously clustered tightly around
        40-60%. Real, well-established outlets now get meaningfully higher
        baseline scores, and known-corroborating cross-source matches can
        push well-evidenced stories up into the 80-95% range."""
        try:
            existing_count = await self.source_credibility.count_documents({})
            if existing_count > 0:
                return

            known_sources = [
                {"source_name": "Bernama", "domain": "www.bernama.com", "credibility_score": 92, "category": "news_agency"},
                {"source_name": "Bernama", "domain": "bernama.com", "credibility_score": 92, "category": "news_agency"},
                {"source_name": "New Straits Times", "domain": "www.nst.com.my", "credibility_score": 87, "category": "newspaper"},
                {"source_name": "New Straits Times", "domain": "nst.com.my", "credibility_score": 87, "category": "newspaper"},
                {"source_name": "The Star", "domain": "www.thestar.com.my", "credibility_score": 87, "category": "newspaper"},
                {"source_name": "The Star", "domain": "thestar.com.my", "credibility_score": 87, "category": "newspaper"},
                {"source_name": "Free Malaysia Today", "domain": "www.freemalaysiatoday.com", "credibility_score": 83, "category": "news_site"},
                {"source_name": "Free Malaysia Today", "domain": "freemalaysiatoday.com", "credibility_score": 83, "category": "news_site"},
                {"source_name": "Malay Mail", "domain": "www.malaymail.com", "credibility_score": 80, "category": "news_site"},
                {"source_name": "Malay Mail", "domain": "malaymail.com", "credibility_score": 80, "category": "news_site"},
                {"source_name": "The Edge Malaysia", "domain": "theedgemalaysia.com", "credibility_score": 86, "category": "business_news"},
                {"source_name": "The Edge Markets", "domain": "www.theedgemarkets.com", "credibility_score": 86, "category": "business_news"},
                {"source_name": "Astro AWANI", "domain": "www.astroawani.com", "credibility_score": 81, "category": "broadcast_news"},
                {"source_name": "Focus Malaysia", "domain": "focusmalaysia.my", "credibility_score": 74, "category": "news_site"},
                {"source_name": "Reuters", "domain": "www.reuters.com", "credibility_score": 93, "category": "news_agency"},
                {"source_name": "Associated Press", "domain": "apnews.com", "credibility_score": 93, "category": "news_agency"},
                {"source_name": "BBC", "domain": "www.bbc.com", "credibility_score": 91, "category": "broadcast_news"},
                {"source_name": "Channel News Asia", "domain": "www.channelnewsasia.com", "credibility_score": 88, "category": "broadcast_news"},
            ]

            docs = [SourceCredibilityCreate(**s).dict() for s in known_sources]
            if docs:
                await self.source_credibility.insert_many(docs)
                logger.info(f"Seeded {len(docs)} known source credibility records.")
        except Exception as exc:
            logger.warning(f"Could not seed source credibility: {exc}")

storage_service = StorageService()