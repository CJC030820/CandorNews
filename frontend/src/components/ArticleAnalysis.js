import React from 'react';
import './ArticleAnalysis.css';

const labels = {source_reputation:'Configured source reputation',corroboration:'Other-publisher coverage',
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
    {article.trustScoredAt && <p>Last analyzed: {new Date(article.trustScoredAt).toLocaleString()}</p>}
    <h2>Compare related reports</h2>
    <p className="analysis-disclaimer">Similar headlines from distinct other publishers. Compare the claims yourself; matching coverage may repeat a common source.</p>
    {article.relatedReports?.length ? article.relatedReports.map(report => <article className="related-report" key={report.url}>
      <h3><a href={report.url} target="_blank" rel="noopener noreferrer">{report.title}</a></h3>
      <p><strong>{report.source}</strong></p><p>{report.summary}</p>
      <p>Sentiment: {report.sentiment || 'Unavailable'} · Tone: {report.toneLabel || 'Unavailable'}</p>
    </article>) : <p>No matching report from another publisher was found in the current search window.</p>}
  </section>;
}
