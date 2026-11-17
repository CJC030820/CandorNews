import pytest
from app.services.topic_classifier import TopicClassifierService


class TestTopicDetection:
    """Test suite for topic detection to ensure correct tag assignment."""

    @pytest.fixture
    def classifier(self):
        """Initialize topic classifier service."""
        return TopicClassifierService()

    # ============ Crime Topic Tests ============
    def test_crime_murder_detected(self, classifier):
        """Test detection of crime-related murder content."""
        title = "Murder suspect arrested in downtown"
        topic = classifier.classify_topic(title)
        assert topic == "Crime", f"Expected 'Crime', got '{topic}'"

    def test_crime_robbery_detected(self, classifier):
        """Test detection of robbery in title."""
        title = "Bank robbery leaves three injured"
        topic = classifier.classify_topic(title)
        assert topic == "Crime", f"Expected 'Crime', got '{topic}'"

    def test_crime_assault_detected(self, classifier):
        """Test detection of assault in content."""
        content = "A severe assault occurred at the downtown plaza last night."
        topic = classifier.classify_topic("Local Incident", content=content)
        assert topic == "Crime", f"Expected 'Crime', got '{topic}'"

    def test_crime_fraud_detected(self, classifier):
        """Test detection of fraud case."""
        title = "Major fraud scheme uncovered by authorities"
        topic = classifier.classify_topic(title)
        assert topic == "Crime", f"Expected 'Crime', got '{topic}'"

    def test_crime_drug_bust_detected(self, classifier):
        """Test detection of drug bust."""
        title = "Police conduct major drug bust in residential area"
        topic = classifier.classify_topic(title)
        assert topic == "Crime", f"Expected 'Crime', got '{topic}'"

    # ============ Technology Topic Tests ============
    def test_technology_detected_single_keyword(self, classifier):
        """Test technology detection with single keyword."""
        title = "New smartphone announced"
        topic = classifier.classify_topic(title)
        assert topic == "Technology", f"Expected 'Technology', got '{topic}'"

    def test_technology_software_detected(self, classifier):
        """Test detection of software in technology category."""
        title = "Latest software update improves security"
        topic = classifier.classify_topic(title)
        assert topic == "Technology", f"Expected 'Technology', got '{topic}'"

    def test_technology_hardware_detected(self, classifier):
        """Test detection of hardware in technology category."""
        title = "Revolutionary hardware design unveiled"
        topic = classifier.classify_topic(title)
        assert topic == "Technology", f"Expected 'Technology', got '{topic}'"

    def test_technology_gadget_detected(self, classifier):
        """Test detection of gadget keyword."""
        title = "Smartphone gadget technology innovation"
        topic = classifier.classify_topic(title)
        assert topic == "Technology", f"Expected 'Technology', got '{topic}'"

    # ============ AI Topic Tests ============
    def test_ai_artificial_intelligence_detected(self, classifier):
        """Test detection of artificial intelligence."""
        title = "Artificial intelligence breakthrough uses deep learning"
        topic = classifier.classify_topic(title)
        assert topic == "AI", f"Expected 'AI', got '{topic}'"

    def test_ai_machine_learning_detected(self, classifier):
        """Test detection of machine learning."""
        title = "Deep learning and neural networks with artificial intelligence"
        topic = classifier.classify_topic(title)
        assert topic == "AI", f"Expected 'AI', got '{topic}'"

    def test_ai_deep_learning_detected(self, classifier):
        """Test detection of deep learning."""
        title = "Deep learning transforms image recognition"
        topic = classifier.classify_topic(title)
        assert topic == "AI", f"Expected 'AI', got '{topic}'"

    def test_ai_neural_network_detected(self, classifier):
        """Test detection of neural network."""
        title = "Neural network solves complex optimization problems"
        topic = classifier.classify_topic(title)
        assert topic == "AI", f"Expected 'AI', got '{topic}'"

    def test_ai_chatbot_detected(self, classifier):
        """Test detection of chatbot."""
        title = "Advanced chatbot provides customer support 24/7"
        topic = classifier.classify_topic(title)
        assert topic == "AI", f"Expected 'AI', got '{topic}'"

    def test_ai_llm_detected(self, classifier):
        """Test detection of large language model."""
        title = "New large language model outperforms competitors"
        topic = classifier.classify_topic(title)
        assert topic == "AI", f"Expected 'AI', got '{topic}'"

    # ============ Sports Topic Tests ============
    def test_sports_football_detected(self, classifier):
        """Test detection of football."""
        title = "Manchester United wins dramatic football match"
        topic = classifier.classify_topic(title)
        assert topic == "Sports", f"Expected 'Sports', got '{topic}'"

    def test_sports_basketball_detected(self, classifier):
        """Test detection of basketball."""
        title = "Lakers secure playoff position in basketball"
        topic = classifier.classify_topic(title)
        assert topic == "Sports", f"Expected 'Sports', got '{topic}'"

    def test_sports_tennis_detected(self, classifier):
        """Test detection of tennis."""
        title = "Tennis championship enters final rounds"
        topic = classifier.classify_topic(title)
        assert topic == "Sports", f"Expected 'Sports', got '{topic}'"

    def test_sports_olympics_detected(self, classifier):
        """Test detection of Olympics."""
        title = "Athletes prepare for upcoming Olympics"
        topic = classifier.classify_topic(title)
        assert topic == "Sports", f"Expected 'Sports', got '{topic}'"

    def test_sports_tournament_detected(self, classifier):
        """Test detection of tournament."""
        title = "Major tournament attracts global competitors"
        topic = classifier.classify_topic(title)
        assert topic == "Sports", f"Expected 'Sports', got '{topic}'"

    # ============ Business Topic Tests ============
    def test_business_company_detected(self, classifier):
        """Test detection of business company."""
        title = "Company announces business growth in market"
        topic = classifier.classify_topic(title)
        assert topic == "Business", f"Expected 'Business', got '{topic}'"

    def test_business_market_detected(self, classifier):
        """Test detection of market."""
        title = "Stock market reaches all-time high"
        topic = classifier.classify_topic(title)
        assert topic == "Business", f"Expected 'Business', got '{topic}'"

    def test_business_investment_detected(self, classifier):
        """Test detection of investment."""
        title = "Investment opportunities in emerging markets"
        topic = classifier.classify_topic(title)
        assert topic == "Business", f"Expected 'Business', got '{topic}'"

    def test_business_trade_detected(self, classifier):
        """Test detection of trade."""
        title = "International trade agreements reach consensus"
        topic = classifier.classify_topic(title)
        assert topic == "Business", f"Expected 'Business', got '{topic}'"

    # ============ Politics Topic Tests ============
    def test_politics_election_detected(self, classifier):
        """Test detection of election."""
        title = "General election scheduled for next month"
        topic = classifier.classify_topic(title)
        assert topic == "Politics", f"Expected 'Politics', got '{topic}'"

    def test_politics_government_detected(self, classifier):
        """Test detection of government."""
        title = "Government announces new policy initiatives"
        topic = classifier.classify_topic(title)
        assert topic == "Politics", f"Expected 'Politics', got '{topic}'"

    def test_politics_parliament_detected(self, classifier):
        """Test detection of parliament."""
        title = "Parliament debates controversial bill"
        topic = classifier.classify_topic(title)
        assert topic == "Politics", f"Expected 'Politics', got '{topic}'"

    def test_politics_president_detected(self, classifier):
        """Test detection of president."""
        title = "President addresses nation on economic outlook"
        topic = classifier.classify_topic(title)
        assert topic == "Politics", f"Expected 'Politics', got '{topic}'"

    # ============ Health Topic Tests ============
    def test_health_medical_detected(self, classifier):
        """Test detection of medical."""
        title = "Medical breakthrough in cancer treatment"
        topic = classifier.classify_topic(title)
        assert topic == "Health", f"Expected 'Health', got '{topic}'"

    def test_health_vaccine_detected(self, classifier):
        """Test detection of vaccine."""
        title = "New vaccine shows promise in clinical trials"
        topic = classifier.classify_topic(title)
        assert topic == "Health", f"Expected 'Health', got '{topic}'"

    def test_health_disease_detected(self, classifier):
        """Test detection of disease."""
        title = "Disease outbreak prompts health alerts"
        topic = classifier.classify_topic(title)
        assert topic == "Health", f"Expected 'Health', got '{topic}'"

    def test_health_hospital_detected(self, classifier):
        """Test detection of hospital."""
        title = "Hospital upgrades facilities with modern equipment"
        topic = classifier.classify_topic(title)
        assert topic == "Health", f"Expected 'Health', got '{topic}'"

    def test_health_fitness_detected(self, classifier):
        """Test detection of fitness."""
        title = "New fitness trends emerge in health industry"
        topic = classifier.classify_topic(title)
        assert topic == "Health", f"Expected 'Health', got '{topic}'"

    # ============ Finance Topic Tests ============
    def test_finance_banking_detected(self, classifier):
        """Test detection of banking."""
        title = "Banking sector faces regulatory changes"
        topic = classifier.classify_topic(title)
        assert topic == "Finance", f"Expected 'Finance', got '{topic}'"

    def test_finance_loan_detected(self, classifier):
        """Test detection of loan."""
        title = "Loan rates expected to change next quarter"
        topic = classifier.classify_topic(title)
        assert topic == "Finance", f"Expected 'Finance', got '{topic}'"

    def test_finance_insurance_detected(self, classifier):
        """Test detection of insurance."""
        title = "Insurance companies adjust premium rates"
        topic = classifier.classify_topic(title)
        assert topic == "Finance", f"Expected 'Finance', got '{topic}'"

    def test_finance_interest_rate_detected(self, classifier):
        """Test detection of interest rate."""
        title = "Central bank announces interest rate decision"
        topic = classifier.classify_topic(title)
        assert topic == "Finance", f"Expected 'Finance', got '{topic}'"

    # ============ Entertainment Topic Tests ============
    def test_entertainment_movie_detected(self, classifier):
        """Test detection of movie."""
        title = "New movie breaks box office records"
        topic = classifier.classify_topic(title)
        assert topic == "Entertainment", f"Expected 'Entertainment', got '{topic}'"

    def test_entertainment_music_detected(self, classifier):
        """Test detection of music."""
        title = "Music festival announces star-studded lineup"
        topic = classifier.classify_topic(title)
        assert topic == "Entertainment", f"Expected 'Entertainment', got '{topic}'"

    def test_entertainment_celebrity_detected(self, classifier):
        """Test detection of celebrity."""
        title = "Celebrity couple walks the red carpet"
        topic = classifier.classify_topic(title)
        assert topic == "Entertainment", f"Expected 'Entertainment', got '{topic}'"

    def test_entertainment_hollywood_detected(self, classifier):
        """Test detection of hollywood."""
        title = "Hollywood studios announce blockbuster films"
        topic = classifier.classify_topic(title)
        assert topic == "Entertainment", f"Expected 'Entertainment', got '{topic}'"

    # ============ Local Malaysia News Tests ============
    def test_local_malaysia_detected(self, classifier):
        """Test detection of local Malaysia news."""
        title = "Malaysia announces new infrastructure project"
        topic = classifier.classify_topic(title)
        assert topic == "Local Malaysia News", f"Expected 'Local Malaysia News', got '{topic}'"

    def test_local_kuala_lumpur_detected(self, classifier):
        """Test detection of Kuala Lumpur."""
        title = "Kuala Lumpur hosts international conference"
        topic = classifier.classify_topic(title)
        assert topic == "Local Malaysia News", f"Expected 'Local Malaysia News', got '{topic}'"

    def test_local_sabah_detected(self, classifier):
        """Test detection of Sabah."""
        title = "Sabah malaysia news updates today"
        topic = classifier.classify_topic(title)
        assert topic == "Local Malaysia News", f"Expected 'Local Malaysia News', got '{topic}'"

    def test_local_selangor_detected(self, classifier):
        """Test detection of Selangor."""
        title = "Selangor announces new transport system"
        topic = classifier.classify_topic(title)
        assert topic == "Local Malaysia News", f"Expected 'Local Malaysia News', got '{topic}'"

    # ============ Multiple Topics Tests ============
    def test_ai_multiple_keywords_strength(self, classifier):
        """Test that multiple AI keywords boost AI classification over Technology."""
        title = "Artificial intelligence, machine learning, and deep learning"
        topics = classifier.classify_topics(title, max_categories=2)
        assert topics[0] == "AI", f"Expected 'AI' as top topic, got {topics}"

    def test_multiple_topics_no_duplicates(self, classifier):
        """Test that classify_topics doesn't return duplicate topics."""
        title = "AI machine learning deep learning neural network"
        topics = classifier.classify_topics(title)
        assert len(topics) == len(set(topics)), "Topics list contains duplicates"

    def test_multiple_topics_respects_max_categories(self, classifier):
        """Test that classify_topics respects max_categories parameter."""
        title = "Crime fraud theft robbery assault artificial intelligence machine learning technology business market"
        topics = classifier.classify_topics(title, max_categories=2)
        assert len(topics) <= 2, f"Expected max 2 topics, got {len(topics)}"

    # ============ Edge Cases Tests ============
    def test_general_topic_for_no_matches(self, classifier):
        """Test that unrecognized content returns General."""
        title = "Clouds drift slowly across the sky"
        topic = classifier.classify_topic(title)
        assert topic == "General", f"Expected 'General', got '{topic}'"

    def test_empty_string_returns_general(self, classifier):
        """Test that empty string returns General."""
        topic = classifier.classify_topic("")
        assert topic == "General", f"Expected 'General', got '{topic}'"

    def test_topic_classification_case_insensitive(self, classifier):
        """Test that classification is case-insensitive."""
        title1 = "ARTIFICIAL INTELLIGENCE BREAKTHROUGH"
        title2 = "artificial intelligence breakthrough"
        topic1 = classifier.classify_topic(title1)
        topic2 = classifier.classify_topic(title2)
        assert topic1 == topic2, f"Expected same topic, got '{topic1}' and '{topic2}'"

    def test_whole_word_boundary_matching(self, classifier):
        """Test that keyword matching respects word boundaries."""
        # "AI" in "said", "detail", "obtained" should not match AI topic
        title = "He said the detailed information was obtained from files"
        topic = classifier.classify_topic(title)
        assert topic != "AI", f"Should not classify as AI due to substrings, but got '{topic}'"

    def test_whole_phrase_matching(self, classifier):
        """Test that multi-word phrases are matched correctly."""
        title = "Large language model powers conversational AI"
        topic = classifier.classify_topic(title)
        assert topic == "AI", f"Expected 'AI' for large language model match, got '{topic}'"

    def test_description_and_content_contribute(self, classifier):
        """Test that description and content fields contribute to classification."""
        title = "Breaking News"
        description = "A murder suspect has been arrested"
        content = "Police arrested the suspect after weeks of investigation"
        topic = classifier.classify_topic(title, description, content)
        assert topic == "Crime", f"Expected 'Crime' when keyword in description/content, got '{topic}'"

    # ============ Real-World Scenarios Tests ============
    def test_tech_article_classified_correctly(self, classifier):
        """Test real-world tech article."""
        title = "Apple launches new smartphone with advanced AI features"
        description = "The latest technology brings machine learning to everyday users"
        content = "Apple's new smartphone features artificial intelligence capabilities for better photography and performance."
        topics = classifier.classify_topics(title, description, content, max_categories=2)
        assert "Technology" in topics or "AI" in topics, f"Expected Technology or AI, got {topics}"

    def test_crime_article_classified_correctly(self, classifier):
        """Test real-world crime article."""
        title = "Major drug bust results in multiple arrests"
        description = "Police conducted a raid that uncovered significant trafficking operation"
        content = "In a coordinated operation, authorities arrested several suspects involved in drug trafficking."
        topic = classifier.classify_topic(title, description, content)
        assert topic == "Crime", f"Expected 'Crime', got '{topic}'"

    def test_business_article_classified_correctly(self, classifier):
        """Test real-world business article."""
        title = "Tech company's market valuation soars"
        description = "Investment in stock market reaches record highs"
        content = "The company's business strategy has led to significant industry growth and investment opportunities."
        topics = classifier.classify_topics(title, description, content)
        assert topics[0] == "Business", f"Expected 'Business' as top topic, got {topics}"

    def test_sports_article_classified_correctly(self, classifier):
        """Test real-world sports article."""
        title = "Champions claim victory in dramatic football match"
        description = "The tournament championship game was intense"
        content = "In an exciting football match, the home team secured the tournament championship."
        topic = classifier.classify_topic(title, description, content)
        assert topic == "Sports", f"Expected 'Sports', got '{topic}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
