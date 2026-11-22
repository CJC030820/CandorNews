import React from 'react';
import { Link } from 'react-router-dom';
import './ArticleAnalysis.css';

const when = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? (value || '') : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
};

// Side-by-side view of each publisher's version of the same story.
function CompareCoverage({ article }) {
  const versions = [
    { ...article, current: true, first: article.reportedFirst, uniqueDetails: article.uniqueDetails || [] },
    ...article.storyVersions,
  ];
  const cell = (render) => versions.map((v) => <td key={v.id}>{render(v)}</td>);
  return <div className="compare-coverage">
    <p className="analysis-disclaimer">
      {versions.length} publishers reported this story. Each column is one publisher's version, judged from the text
      its news feed provides (some feeds give only a sentence, so fewer details can show up for them).
    </p>
    <div className="analysis-table-scroll"><table className="compare-table">
      <thead><tr><th scope="col"><span className="visually-hidden">Detail</span></th>
        {versions.map((v) => <th scope="col" key={v.id}>{v.source}{v.current && <span className="compare-tag">This version</span>}</th>)}
      </tr></thead>
      <tbody>
        <tr><th scope="row">Headline</th>{cell((v) => v.title)}</tr>
        <tr><th scope="row">Published</th>{cell((v) => <>{when(v.rawDate || v.date)}{v.first && <span className="compare-tag first">Reported first</span>}</>)}</tr>
        <tr><th scope="row">Trust score</th>{cell((v) => v.trustScore == null ? 'Awaiting update' : `${v.trustScore}/100`)}</tr>
        <tr><th scope="row">Tone</th>{cell((v) => `${v.toneLabel || 'Unavailable'} · ${v.sentiment || 'Unavailable'}`)}</tr>
        <tr><th scope="row">Only in this version</th>{cell((v) => v.uniqueDetails?.length
          ? <ul className="compare-details">{v.uniqueDetails.map((d) => <li key={d}>{d}</li>)}</ul>
          : <span className="analysis-disclaimer">Nothing the others do not mention</span>)}</tr>
        <tr><th scope="row"><span className="visually-hidden">Open</span></th>{cell((v) => v.current
          ? <span className="analysis-disclaimer">You are reading this</span>
          : <Link to={`/article/${v.id}`}>Read this version</Link>)}</tr>
      </tbody>
    </table></div>
    {/* Phones: one block per version instead of side-by-side columns. */}
    <ul className="compare-cards">{versions.map((v) => <li key={v.id}>
      <p className="compare-card-head"><strong>{v.source}</strong>
        {v.current && <span className="compare-tag">This version</span>}
        {v.first && <span className="compare-tag">Reported first</span>}</p>
      <p className="compare-card-title">{v.title}</p>
      <p className="analysis-disclaimer">{when(v.rawDate || v.date)} · {v.trustScore == null ? 'Trust awaiting update' : `${v.trustScore}/100 trust`} · {v.toneLabel || 'Tone unavailable'}</p>
      {v.uniqueDetails?.length > 0 && <><p className="compare-card-label">Only in this version</p>
        <ul className="compare-details">{v.uniqueDetails.map((d) => <li key={d}>{d}</li>)}</ul></>}
      {!v.current && <Link to={`/article/${v.id}`}>Read this version</Link>}
    </li>)}</ul>
  </div>;
}

const labels = {source_reputation:'Configured source reputation',content_quality:'Content quality',corroboration:'Other-publisher coverage',
  metadata_completeness:'Metadata completeness',sentiment_neutrality:'Sentiment neutrality'};
export default function ArticleAnalysis({article, loading = false}) {
  const components = article.trustComponents || {};
  const weights = article.trustWeights || {};
  // News lists carry only a summary of the analysis; the article page loads the rest.
  const hasDetail = article.relatedReports !== undefined || article.trustExplanation !== undefined;
  if (!hasDetail) {
    return <section className="article-analysis" aria-label="Article analysis">
      <h2>Article analysis</h2>
      <p><strong>Sentiment:</strong> {article.sentiment || 'Unavailable'} · <strong>Tone:</strong> {article.toneLabel || 'Unavailable'}</p>
      <p><strong>Trust:</strong> {article.trustScore == null ? 'Awaiting analysis update' : `${article.trustScore}/100`} {article.trustLabel && `— ${article.trustLabel}`}</p>
      <p className="analysis-disclaimer" role="status">
        {loading ? 'Loading the full analysis and related reports...' : 'The full analysis could not be loaded. Please try again.'}
      </p>
    </section>;
  }
  return <section className="article-analysis" aria-label="Article analysis">
    <h2>Article analysis</h2>
    <p><strong>Sentiment:</strong> {article.sentiment || 'Unavailable'} · <strong>Tone:</strong> {article.toneLabel || 'Unavailable'}</p>
    <p><strong>Trust:</strong> {article.trustScore == null ? 'Awaiting analysis update' : `${article.trustScore}/100`} {article.trustLabel && `— ${article.trustLabel}`}</p>
    <p className="analysis-disclaimer">{article.trustExplanation || 'An updated explanation will be available after the next collection cycle.'}</p>
    {Object.keys(components).length > 0 && <div className="analysis-table-scroll"><table>
      <caption>How the trust score is calculated</caption>
      <thead><tr><th>Factor</th><th>Value</th><th>Weight</th><th>Points</th></tr></thead>
      <tbody>{Object.entries(components).map(([key,value]) => <tr key={key}>
        <th scope="row">{labels[key] || key}</th><td>{(value * 100).toFixed(1)}%</td>
        <td>{((weights[key] || 0) * 100).toFixed(0)}%</td><td>{(value * (weights[key] || 0) * 100).toFixed(2)}</td>
      </tr>)}</tbody>
    </table><p className="analysis-disclaimer">The weighted total is capped at 95. This is not a probability that an article is true.</p></div>}
    {article.contentChecks?.length > 0 && <div className="content-checks">
      <h3>Content quality checks</h3>
      <p className="analysis-disclaimer">How this article is reported, judged from its headline and text. It does not check whether the claims are true.</p>
      <ul>{article.contentChecks.map(check => <li key={check.key}>
        <span className="content-check-head"><strong>{check.label}</strong>
          <span className="content-check-score">{Math.round(check.score * 100)}%</span></span>
        <span className="content-check-reason">{check.reason}</span>
      </li>)}</ul>
    </div>}
    {article.trustScoredAt && <p>Last analyzed: {new Date(article.trustScoredAt).toLocaleString()}</p>}
    {article.storyVersions?.length > 0 ? <>
      <h2 id="compare">Compare coverage</h2>
      <CompareCoverage article={article} />
    </> : <>
    <h2 id="compare">Compare related reports</h2>
    <p className="analysis-disclaimer">Similar headlines from distinct other publishers. Compare the claims yourself; matching coverage may repeat a common source.</p>
    {article.relatedReports?.length ? article.relatedReports.map(report => <article className="related-report" key={report.url}>
      <h3><a href={report.url} target="_blank" rel="noopener noreferrer">{report.title}</a></h3>
      <p><strong>{report.source}</strong></p><p>{report.summary}</p>
      <p>Sentiment: {report.sentiment || 'Unavailable'} · Tone: {report.toneLabel || 'Unavailable'}</p>
    </article>) : <p>No matching report from another publisher was found in the current search window.</p>}
    </>}
  </section>;
}
