import React, { useState } from 'react';
import './HelpPage.css';

const HelpPage = () => {
  const [expandedSection, setExpandedSection] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  const faqData = [
    {
      category: 'Getting Started',
      items: [
        {
          question: 'How do I create an account?',
          answer: 'Click the "Sign Up" button on the login page and enter your email, name, and password. Your account will be created instantly and you can start using the platform.'
        },
        {
          question: 'How do I log in?',
          answer: 'Enter your registered email and password on the login page. Your session will be saved, so you\'ll stay logged in even if you close the browser.'
        },
        {
          question: 'What if I forget my password?',
          answer: 'Currently, please contact our support team. We recommend using a password manager to keep track of your credentials securely.'
        },
        {
          question: 'How do I delete my account?',
          answer: 'Go to your Profile page and click "Delete Account". You\'ll need to confirm your password. This action is permanent and cannot be undone.'
        }
      ]
    },
    {
      category: 'News Feed',
      items: [
        {
          question: 'How do I customize my news feed?',
          answer: 'During signup, select your preferred topics. You can also update these anytime in your Profile settings. We\'ll prioritize news from your selected topics.'
        },
        {
          question: 'What does the Trust Score mean?',
          answer: 'The Trust Score (0-100) indicates the credibility of the news source based on historical accuracy, editorial standards, and bias ratings. Higher scores mean more reliable sources.'
        },
        {
          question: 'How often is the news updated?',
          answer: 'Our system fetches the latest news every 15 minutes from NewsAPI, GNews, and RSS feeds. You\'ll see the most recent articles at the top of your feed.'
        },
        {
          question: 'Can I manually refresh the news?',
          answer: 'Yes! Click the "Refresh News" button to fetch the latest articles immediately.'
        }
      ]
    },
    {
      category: 'Articles & Reading',
      items: [
        {
          question: 'How do I read a full article?',
          answer: 'Click on any article card to open the full article detail page. You\'ll see the complete story, source, publication date, and sentiment analysis.'
        },
        {
          question: 'What do the sentiment indicators mean?',
          answer: 'Sentiment shows the emotional tone of the article: Positive (optimistic), Neutral (factual), or Negative (critical). This helps you understand the article\'s perspective.'
        },
        {
          question: 'Can I share articles?',
          answer: 'You can copy the article URL from the detail page and share it with others. Click on the article to open its detail view.'
        },
        {
          question: 'How do I bookmark an article?',
          answer: 'Click the bookmark icon (♡) on any article card. Your bookmarks are saved to your account and you can view them anytime in the Bookmarks section.'
        }
      ]
    },
    {
      category: 'Bookmarks & History',
      items: [
        {
          question: 'Where are my bookmarks saved?',
          answer: 'Your bookmarks are saved in your profile. Click "Bookmarks" in the navigation menu to view all articles you\'ve saved.'
        },
        {
          question: 'Can I delete a bookmark?',
          answer: 'Yes, click the bookmark icon again on any article to remove it from your bookmarks. The change is instant.'
        },
        {
          question: 'How do I view my reading history?',
          answer: 'Click "History" in the navigation menu to see all articles you\'ve read. This helps you keep track of what you\'ve already covered.'
        },
        {
          question: 'Can I clear my history?',
          answer: 'You can delete individual articles from your history by clicking the delete icon, or you can delete your entire account to clear all data.'
        }
      ]
    },
    {
      category: 'Notifications',
      items: [
        {
          question: 'How do I enable email notifications?',
          answer: 'Go to your Profile page and toggle "Email Notifications". Then select when you\'d like to receive digests: Morning (7am), Evening (7pm), or Both.'
        },
        {
          question: 'What will I receive in email digests?',
          answer: 'You\'ll get a personalized digest with up to 10 of the latest articles from your preferred topics, complete with trust scores and summaries.'
        },
        {
          question: 'Can I change my notification frequency?',
          answer: 'Yes, go to your Profile settings and select your preferred notification schedule. Changes take effect immediately.'
        },
        {
          question: 'How do I test email notifications?',
          answer: 'In your Profile settings, click "Send Test Email" to receive a sample digest immediately. This helps verify your email is working.'
        }
      ]
    },
    {
      category: 'Account & Privacy',
      items: [
        {
          question: 'Is my data secure?',
          answer: 'Yes, your account data is stored securely in our database. Your password is encrypted and never shared. We follow industry best practices for data security.'
        },
        {
          question: 'Can I change my profile name?',
          answer: 'Yes, go to your Profile page and click "Edit Name". Enter your new name and save the changes.'
        },
        {
          question: 'What information do you collect?',
          answer: 'We collect your email, name, password (encrypted), preferred topics, and reading activity to personalize your experience. We do not sell this data.'
        },
        {
          question: 'How do I export my data?',
          answer: 'Currently, you can view all your data in the Profile section. For detailed export options, please contact our support team.'
        }
      ]
    },
    {
      category: 'Troubleshooting',
      items: [
        {
          question: 'Why aren\'t articles loading?',
          answer: 'Check your internet connection. If the problem persists, try refreshing the page or clearing your browser cache. Contact support if it continues.'
        },
        {
          question: 'Why aren\'t my preferences saving?',
          answer: 'Make sure you\'ve clicked "Save" after making changes. Try logging out and back in. If the issue continues, clear your browser cache.'
        },
        {
          question: 'Why didn\'t I receive my email notification?',
          answer: 'Check that email notifications are enabled in your Profile. Verify the email address is correct. Check your spam folder. Try sending a test email.'
        },
        {
          question: 'The page looks broken or unusual. What should I do?',
          answer: 'Try clearing your browser cache and cookies, then refresh the page. Make sure you\'re using a supported browser (Chrome, Firefox, Safari, or Edge).'
        }
      ]
    }
  ];

  const filteredFaq = faqData.map(category => ({
    ...category,
    items: category.items.filter(
      item =>
        item.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.answer.toLowerCase().includes(searchQuery.toLowerCase())
    )
  })).filter(category => category.items.length > 0);

  const toggleItem = (sectionIndex, itemIndex) => {
    const key = `${sectionIndex}-${itemIndex}`;
    setExpandedSection(expandedSection === key ? null : key);
  };

  return (
    <div className="help-page">
      <div className="help-header">
        <div className="help-header-content">
          <h1>Help Center</h1>
          <p>Find answers to common questions about News Intelligence</p>
        </div>
      </div>

      <div className="help-container">
        {/* Search Bar */}
        <div className="help-search-section">
          <div className="search-box">
            <input
              type="text"
              placeholder="Search for help..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
            <span className="search-icon">🔍</span>
          </div>
          {searchQuery && (
            <p className="search-results-info">
              Found {filteredFaq.reduce((sum, cat) => sum + cat.items.length, 0)} results
            </p>
          )}
        </div>

        {/* Quick Links */}
        {!searchQuery && (
          <div className="quick-links-section">
            <h2>Quick Links</h2>
            <div className="quick-links-grid">
              <div className="quick-link-card">
                <div className="quick-link-icon">🚀</div>
                <h3>Getting Started</h3>
                <p>New to News Intelligence? Learn the basics</p>
              </div>
              <div className="quick-link-card">
                <div className="quick-link-icon">📰</div>
                <h3>News Feed</h3>
                <p>Understand how to use your personalized feed</p>
              </div>
              <div className="quick-link-card">
                <div className="quick-link-icon">📧</div>
                <h3>Notifications</h3>
                <p>Set up email digests and alerts</p>
              </div>
              <div className="quick-link-card">
                <div className="quick-link-icon">🔒</div>
                <h3>Security</h3>
                <p>Learn about your privacy and data</p>
              </div>
            </div>
          </div>
        )}

        {/* FAQ Sections */}
        <div className="faq-section">
          <h2>{searchQuery ? 'Search Results' : 'Frequently Asked Questions'}</h2>

          {filteredFaq.length === 0 ? (
            <div className="no-results">
              <p>No results found for "{searchQuery}"</p>
              <p>Try using different keywords or contact our support team.</p>
            </div>
          ) : (
            filteredFaq.map((category, sectionIndex) => (
              <div key={sectionIndex} className="faq-category">
                <h3 className="category-title">{category.category}</h3>
                <div className="faq-items">
                  {category.items.map((item, itemIndex) => (
                    <div
                      key={itemIndex}
                      className="faq-item"
                      onClick={() => toggleItem(sectionIndex, itemIndex)}
                    >
                      <div className="faq-question">
                        <span className="question-text">{item.question}</span>
                        <span className={`toggle-icon ${expandedSection === `${sectionIndex}-${itemIndex}` ? 'open' : ''}`}>
                          ▼
                        </span>
                      </div>
                      {expandedSection === `${sectionIndex}-${itemIndex}` && (
                        <div className="faq-answer">
                          {item.answer}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Contact Support */}
        <div className="support-section">
          <h2>Didn't find what you're looking for?</h2>
          <div className="support-content">
            <p>Our support team is here to help. You can reach out to us with any questions or issues.</p>
            <div className="support-options">
              <div className="support-option">
                <div className="support-icon">📧</div>
                <h4>Email Support</h4>
                <p>support@newsintelligence.com</p>
              </div>
              <div className="support-option">
                <div className="support-icon">📱</div>
                <h4>Live Chat</h4>
                <p>Available 9am-5pm EST</p>
              </div>
              <div className="support-option">
                <div className="support-icon">📋</div>
                <h4>Documentation</h4>
                <p>Visit our full documentation</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HelpPage;
