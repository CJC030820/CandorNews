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
