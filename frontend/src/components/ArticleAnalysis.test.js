import React from 'react';
import {render,screen} from '@testing-library/react';
import ArticleAnalysis from './ArticleAnalysis';
test('explains components and preserves linked evidence',()=>{
 render(<ArticleAnalysis article={{sentiment:'Neutral',toneLabel:'Neutral / Objective',trustScore:60,
 trustComponents:{source_reputation:.9},trustWeights:{source_reputation:.4},
 relatedReports:[{title:'Another report',url:'https://other.com/story',source:'Other outlet',summary:'Their own summary'}]}}/>);
 expect(screen.getByRole('link',{name:'Another report'})).toHaveAttribute('href','https://other.com/story');
 expect(screen.getByText('36.00')).toBeInTheDocument();
 expect(screen.getByText(/not a probability/)).toBeInTheDocument();
});
test('shows absence of corroboration explicitly',()=>{
 render(<ArticleAnalysis article={{relatedReports:[]}}/>);
 expect(screen.getByText(/No matching report/)).toBeInTheDocument();
 expect(screen.getByText(/Awaiting analysis update/)).toBeInTheDocument();
});

test('while the full article loads it says so instead of "no related reports"',()=>{
 const {rerender}=render(<ArticleAnalysis article={{sentiment:'Neutral',trustScore:70}} loading/>);
 expect(screen.getByText(/Loading the full analysis/)).toBeInTheDocument();
 expect(screen.queryByText(/No matching report/)).not.toBeInTheDocument();
 rerender(<ArticleAnalysis article={{sentiment:'Neutral',trustScore:70}} loading={false}/>);
 expect(screen.getByText(/could not be loaded/)).toBeInTheDocument();
});

test('lists the content quality checks with their reasons',()=>{
 render(<ArticleAnalysis article={{trustScore:80,relatedReports:[],
 trustComponents:{source_reputation:.92,content_quality:.85},trustWeights:{source_reputation:.3,content_quality:.2},
 contentChecks:[{key:'attribution',label:'Attribution',score:.85,reason:'Sources shown: a direct quote.'},
  {key:'verified_language',label:'Verified language',score:1,reason:'No rumour or unverified wording.'}]}}/>);
 expect(screen.getByText('Content quality')).toBeInTheDocument();
 expect(screen.getByText('Content quality checks')).toBeInTheDocument();
 expect(screen.getByText('Sources shown: a direct quote.')).toBeInTheDocument();
 expect(screen.getByText('85%')).toBeInTheDocument();
 expect(screen.getByText(/does not check whether the claims are true/)).toBeInTheDocument();
});
