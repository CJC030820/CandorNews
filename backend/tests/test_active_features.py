import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
import pytest
from httpx import AsyncClient, ASGITransport
from app import main
from app.models.article import ArticleCreate
from app.models.user import UserCreate
from app.services.storage import storage_service
from app.services.trust_scorer import TrustScorerService, SCORE_VERSION, publisher_domain
from app.services.deduplicator import DeduplicatorService
from app.worker import NewsWorker, _parse_published_date


def sample(**updates):
    return dict(title="City council approves new public transport funding",
                source="Example News", url="https://example.com/story", author="Reporter",
                published_date=datetime.utcnow(), description="Public transport funding approved.",
                topic="Politics", topics=["Politics"], keywords=["transport", "funding"],
                sentiment="Neutral", tone_label="Neutral / Objective", trust_score=50,
                processing_status="completed", **updates)


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as client:
        yield client


@pytest.fixture
async def auth(client):
    await storage_service.ensure_indexes()
    assert (await client.post('/api/auth/register', json={"name":"Tester", "email":"test@example.com", "password":"password123"})).status_code == 200
    response = await client.post('/api/auth/login', json={"email":"test@example.com", "password":"password123"})
    return {"Authorization": "Bearer " + response.json()["access_token"]}


@pytest.mark.parametrize('payload', [
    {"name":"Tester","email":"bad","password":"password123"},
    {"name":" ","email":"test@example.com","password":"password123"},
    {"name":"Tester","email":"test@example.com","password":"short"}])
async def test_registration_validation(client, payload):
    assert (await client.post('/api/auth/register',json=payload)).status_code == 422


async def test_registration_login_persistence_and_password(client, auth):
    doc = await storage_service.users.find_one({"email":"test@example.com"})
    assert 'password' not in doc and doc['hashed_password'] != 'password123'
    assert doc['created_at'] == doc['updated_at']
    assert (await client.get('/api/auth/me',headers=auth)).json()['name'] == 'Tester'
    assert (await client.post('/api/auth/login',json={"email":"test@example.com","password":"wrong"})).status_code == 401
    assert (await client.post('/api/auth/register',json={"name":"Duplicate","email":"test@example.com","password":"password123"})).status_code == 400


async def test_query_tokens_rejected(client, auth):
    token=auth['Authorization'].split()[1]
    assert (await client.get('/api/auth/me',params={'token':token})).status_code == 401
    assert (await client.get('/api/articles/feed',headers={'Authorization':'Bearer bad'})).status_code == 401


async def test_preferences_and_profile(client, auth):
    response=await client.put('/api/users/preferences',headers=auth,json={'preferred_topics':['Sports','Technology']})
    assert response.json()['preferred_topics'] == ['Sports','Technology']
    await client.put('/api/users/profile',headers=auth,json={'name':'Updated'})
    assert (await client.get('/api/auth/me',headers=auth)).json()['name']=='Updated'


async def test_feed_and_direct_detail_expose_analysis(client, auth):
    data=sample()
    data.update(await TrustScorerService().calculate_trust_score(data))
    saved=await storage_service.create_article(ArticleCreate(**data))
    feed=(await client.get('/api/articles/feed',headers=auth)).json()['articles'][0]
    detail=(await client.get('/api/articles/'+saved.id,headers=auth)).json()
    for key in ['sentiment','trustScore','trustLabel']:
        assert detail[key] == feed[key]
    # the full analysis comes with the article page; the feed list stays light
    for key in ['trustExplanation','trustComponents','trustWeights','relatedReports','trustVersion']:
        assert key in detail and key not in feed
    assert detail['trustVersion']==SCORE_VERSION and detail['date'].endswith('+00:00')
    assert (await client.get('/api/articles/not-an-id',headers=auth)).status_code==404
    assert (await client.get('/api/articles/feed?limit=-1',headers=auth)).status_code==422


async def test_legacy_score_hidden_until_rescored(client, auth):
    await storage_service.create_article(ArticleCreate(**sample()))
    assert (await client.get('/api/articles/feed',headers=auth)).json()['articles'][0]['trustScore'] is None


async def test_same_publisher_cannot_inflate_score():
    scorer=TrustScorerService()
    article=sample()
    base=await scorer.calculate_trust_score(article)
    matches=[{**article,'url':f'https://www.example.com/copy/{i}'} for i in range(5)]
    result=await scorer.calculate_trust_score(article,matches)
    assert result['trust_score']==base['trust_score']
    assert result['trust_evidence']==[]


async def test_distinct_publisher_evidence_and_duplicate_domain():
    scorer=TrustScorerService()
    article=sample()
    reports=[{**article,'url':f'https://other.com/{i}','source':'Other News'} for i in range(3)]
    result=await scorer.calculate_trust_score(article,reports)
    assert len(result['trust_evidence'])==1
    assert result['trust_components']['corroboration']==pytest.approx(.425)
    assert 'fact_check_availability' not in result['trust_components']
    unrelated={**reports[0], 'title':'Football club wins championship trophy tonight'}
    assert not (await scorer.calculate_trust_score(article,[unrelated]))['trust_evidence']


def test_publisher_aliases():
    assert publisher_domain('https://WWW.NST.COM.MY:443/news')=='nst.com.my'
    assert publisher_domain('https://news.nst.com.my/news')=='nst.com.my'


async def test_score_cap_and_components(monkeypatch):
    scorer=TrustScorerService()
    monkeypatch.setattr(scorer,'calculate_source_reputation_async',AsyncMock(return_value=1.))
    import app.services.trust_scorer as trust_module
    monkeypatch.setattr(trust_module,'analyze_content',lambda article:{'score':1.,'checks':[]})
    article=sample()
    result=await scorer.calculate_trust_score(article,[{**article,'url':f'https://outlet{i}.com/report'} for i in range(4)])
    assert result['trust_score']==95
    assert sum(result['trust_weights'].values())==1
    assert 'not a fact check' in result['trust_explanation']


@pytest.mark.parametrize('value', ['2026-10-15T08:00:00+08:00','Thu, 15 Oct 2026 08:00:00 +0800',datetime(2026,10,15,tzinfo=timezone.utc)])
def test_date_normalization(value):
    assert _parse_published_date(value)==datetime(2026,10,15)


def test_dedup_preserves_other_outlets():
    a=sample()
    articles=DeduplicatorService().remove_duplicates([a,a,{**a,'url':'https://other.com/report'}])
    assert len(articles)==2


async def test_worker_normalized_inputs_and_rescoring(monkeypatch):
    worker=NewsWorker()
    monkeypatch.setattr('app.worker.is_english_article',lambda *args:True)
    monkeypatch.setattr(worker.sentiment_analyzer, 'analyze_article_sentiment', Mock(return_value={
        'sentiment': 'Neutral', 'sentiment_score': 0., 'tone_label': 'Neutral / Objective'}))
    raw={'title':'City council approves new public transport funding','url':'https://example.com/story',
         'source':'Example News','description':'The city council approved public transport funding.',
         'author':'Reporter','published_at':datetime.utcnow().isoformat()+'Z'}
    assert await worker.process_article(raw)
    first=await storage_service.get_article_by_url(raw['url'])
    assert first.trust_components['metadata_completeness']==pytest.approx(1.)
    assert first.trust_components['sentiment_neutrality']==1.
    assert not await worker.process_article(raw)
    assert await worker.process_article({**raw,'url':'https://other.com/story','source':'Other'})
    await worker.rescore_recent_articles()
    updated=await storage_service.get_article_by_url(raw['url'])
    assert len(updated.trust_evidence)==1 and updated.trust_score > first.trust_score


async def test_refresh_job_completion_and_ownership(client, auth, monkeypatch):
    gate=asyncio.Event()
    async def work(platforms):
        await gate.wait()
        return {'saved':2}
    monkeypatch.setattr(main.news_worker,'fetch_and_process_news',work)
    response=await client.post('/api/articles/refresh',headers=auth,json={'platforms':['Bernama']})
    assert response.status_code==202
    job=response.json()['jobId']
    again=await client.post('/api/articles/refresh',headers=auth,json={'platforms':['Bernama']})
    assert again.json()['jobId']==job
    assert (await client.get('/api/articles/refresh/'+job,headers=auth)).json()['status']=='pending'
    gate.set(); await asyncio.sleep(.01)
    assert (await client.get('/api/articles/refresh/'+job,headers=auth)).json()['stats']['saved']==2
    main.refresh_jobs[job]['owner']='another-account'
    assert (await client.get('/api/articles/refresh/'+job,headers=auth)).status_code==404
    main.refresh_jobs.clear()


async def test_refresh_failure_is_reported(client, auth, monkeypatch):
    monkeypatch.setattr(main.news_worker,'fetch_and_process_news',AsyncMock(return_value={'error':'feed unavailable'}))
    job=(await client.post('/api/articles/refresh',headers=auth,json={'platforms':['Bernama']})).json()['jobId']
    await asyncio.sleep(.01)
    assert (await client.get('/api/articles/refresh/'+job,headers=auth)).json()['status']=='failed'
    main.refresh_jobs.clear()


async def test_health_dependency_failure(client, monkeypatch):
    monkeypatch.setattr(storage_service,'client',SimpleNamespace(admin=SimpleNamespace(command=AsyncMock(side_effect=RuntimeError('offline')))))
    assert (await client.get('/health')).status_code==503


def test_email_scheduler_async_timezone(monkeypatch):
    scheduler=Mock(running=False)
    monkeypatch.setattr(main,'email_scheduler',scheduler)
    main.start_email_scheduler()
    assert scheduler.add_job.call_count==1
    call=scheduler.add_job.call_args
    assert call.args[0] is main._run_due_email_notifications
    assert str(call.args[1].timezone)=='Asia/Kuala_Lumpur'


async def test_email_settings_and_failure_without_sending(client,auth,monkeypatch):
    assert (await client.put('/api/notifications/email',headers=auth,json={'email_notification_schedule':'bad'})).status_code==400
    result=await client.put('/api/notifications/email',headers=auth,json={'email_notifications_enabled':True,'email_notification_schedule':'both'})
    assert result.json()['email_notification_schedule']=='both'
    assert result.json()['email_notification_times']==['07:00','19:00']
    monkeypatch.setattr(main.email_service,'send_email',Mock(return_value={'success':False,'message':'SMTP unavailable'}))
    assert (await client.post('/api/notifications/email/test',headers=auth,json={})).status_code==403
    await storage_service.users.update_many({},{'$set':{'email_verified':True}})
    assert (await client.post('/api/notifications/email/test',headers=auth,json={})).status_code==502


async def test_delete_requires_password(client,auth):
    assert (await client.request('DELETE','/api/users/me',headers=auth,json={'password':'bad'})).status_code==401
    assert (await client.request('DELETE','/api/users/me',headers=auth,json={'password':'password123'})).status_code==200
    assert (await client.get('/api/auth/me',headers=auth)).status_code==401


@pytest.mark.parametrize('url', ['javascript:alert(1)', 'https://[invalid', 'https:///missing-host'])
async def test_worker_rejects_invalid_links(url):
    assert not await NewsWorker().process_article({'title':'Example news headline','url':url})


async def test_missing_publication_date_not_rewarded_after_rescore(monkeypatch):
    worker=NewsWorker()
    monkeypatch.setattr('app.worker.is_english_article',lambda *args:True)
    await worker.process_article({'title':'City council approves new public transport funding','url':'https://example.com/missing-date',
                                 'source':'Example','author':'Reporter','description':'A city council report','published_at':'invalid date'})
    await worker.rescore_recent_articles()
    article=await storage_service.get_article_by_url('https://example.com/missing-date')
    assert article.publication_date_inferred
    assert article.trust_components['metadata_completeness']==pytest.approx(.75)


def test_digest_escapes_html_and_uses_trust_language():
    result=main.email_service.build_news_digest_email('<script>user</script>',[
        {'title':'<script>title</script>','source':'<b>source</b>','url':'javascript:alert(1)',
         'description':'<img src=x onerror=alert(1)>','trustScore':60}])
    assert '<script>' not in result['html'] and '<img src=x' not in result['html']
    assert 'href="javascript:' not in result['html']
    assert '60/100 trust' in result['html']


async def test_unknown_preference_rejected(client,auth):
    assert (await client.put('/api/users/preferences',headers=auth,json={'preferred_topics':['NotATopic']})).status_code==422
