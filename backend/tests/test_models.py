import pytest
from pydantic import ValidationError
from app.models.user import UserCreate, UserInDB, UserResponse
from app.models.article import ArticleCreate
from app.models.interaction import InteractionCreate
from app.models.source_credibility import SourceCredibilityCreate
from datetime import datetime

def test_user_create_valid():
    """Test that a valid UserCreate model is created."""
    user_data = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "securepassword123",
        "preferred_topics": ["Technology", "AI"]
    }
    user = UserCreate(**user_data)
    assert user.name == user_data["name"]
    assert user.email == user_data["email"]
    assert user.password == user_data["password"]
    assert user.preferred_topics == user_data["preferred_topics"]

def test_user_create_missing_required():
    """Test that missing required fields raise validation error."""
    with pytest.raises(ValidationError):
        UserCreate(name="Test User")  # missing email and password

def test_user_create_invalid_email():
    """Test that invalid email raises validation error."""
    with pytest.raises(ValidationError):
        UserCreate(
            name="Test User",
            email="not-an-email",
            password="password123"
        )

def test_user_in_db_from_orm():
    """Test that UserInDB can be created from ORM object (simulated with dict)."""
    # Simulate an ORM object with _id field
    orm_obj = {
        "_id": "60a7b5c8f1d0d2001ca8f0b0",
        "name": "ORM User",
        "email": "orm@example.com",
        "hashed_password": "hashedpass",
        "preferred_topics": ["Sports"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    user = UserInDB(**orm_obj)
    assert user.id == orm_obj["_id"]
    assert user.email == orm_obj["email"]
    assert user.hashed_password == orm_obj["hashed_password"]
    assert user.preferred_topics == orm_obj["preferred_topics"]

def test_user_response_model():
    """Test UserResponse model."""
    user_data = {
        "id": "60a7b5c8f1d0d2001ca8f0b0",
        "name": "Response User",
        "email": "response@example.com",
        "preferred_topics": ["News"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    user = UserResponse(**user_data)
    assert user.id == user_data["id"]
    assert user.name == user_data["name"]
    assert user.email == user_data["email"]
    assert user.preferred_topics == user_data["preferred_topics"]
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.updated_at, datetime)

def test_article_create_model():
    """Test ArticleCreate model."""
    article_data = {
        "title": "Test Article",
        "source": "Test Source",
        "url": "https://example.com/article",
        "published_at": datetime.utcnow(),
        "description": "A test article",
        "content": "Full content",
        "topic": "Technology"
    }
    article = ArticleCreate(**article_data)
    assert article.title == article_data["title"]
    assert article.source == article_data["source"]
    assert article.url == article_data["url"]
    assert article.description == article_data["description"]
    assert article.content == article_data["content"]
    assert article.topic == article_data["topic"]

def test_interaction_create_model():
    """Test InteractionCreate model."""
    interaction_data = {
        "user_id": "60a7b5c8f1d0d2001ca8f0b0",
        "article_id": "60a7b5c8f1d0d2001ca8f0b1",
        "action_type": "bookmark"
    }
    interaction = InteractionCreate(**interaction_data)
    assert interaction.user_id == interaction_data["user_id"]
    assert interaction.article_id == interaction_data["article_id"]
    assert interaction.action_type == interaction_data["action_type"]

def test_source_credibility_create_model():
    """Test SourceCredibilityCreate model."""
    cred_data = {
        "name": "Trusted News",
        "domain": "trustednews.com",
        "credibility_score": 95,
        "category": "News"
    }
    cred = SourceCredibilityCreate(**cred_data)
    assert cred.name == cred_data["name"]
    assert cred.domain == cred_data["domain"]
    assert cred.credibility_score == cred_data["credibility_score"]
    assert cred.category == cred_data["category"]

def test_source_credibility_score_validation():
    """Test that credibility score must be between 0 and 100."""
    # Valid score
    cred = SourceCredibilityCreate(
        name="Valid",
        domain="valid.com",
        credibility_score=50,
        category="News"
    )
    assert cred.credibility_score == 50

    # Too low
    with pytest.raises(ValidationError):
        SourceCredibilityCreate(
            name="Low",
            domain="low.com",
            credibility_score=-1,
            category="News"
        )

    # Too high
    with pytest.raises(ValidationError):
        SourceCredibilityCreate(
            name="High",
            domain="high.com",
            credibility_score=101,
            category="News"
        )

def test_user_in_db_alias():
    """Test that UserInDB uses alias for id field."""
    data = {
        "_id": "60a7b5c8f1d0d2001ca8f0b0",
        "name": "Alias User",
        "email": "alias@example.com",
        "hashed_password": "hashedpass",
        "preferred_topics": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    user = UserInDB(**data)
    # When using alias, the id field should be populated from _id
    assert user.id == "60a7b5c8f1d0d2001ca8f0b0"
    # Also check that the internal _id attribute is not present (Pydantic uses alias)
    # The model does not have an attribute named '_id' unless we set it.
    # We can check that the object's dict includes the id.
    user_dict = user.dict(by_alias=True)
    assert user_dict["_id"] == "60a7b5c8f1d0d2001ca8f0b0"