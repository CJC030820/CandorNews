import React from 'react';
import {render,screen,fireEvent} from '@testing-library/react';
import {MemoryRouter,Routes,Route} from 'react-router-dom';
import ArticleCard from './ArticleCard';
jest.mock('../context/BookmarkContext',()=>({useBookmarks:()=>({isBookmarked:()=>false,toggleBookmark:jest.fn()})}));
jest.mock('../context/ReadArticlesContext',()=>({useReadArticles:()=>({isRead:()=>false})}));
const article={id:'42',title:'Transport funding',source:'News outlet',date:'15 Oct 2026',description:'Original report summary',category:'Politics',sentiment:'Neutral',trustScore:70};
test('renders source-linked summary, polarity and heuristic score',()=>{
  render(<MemoryRouter><ArticleCard article={article}/></MemoryRouter>);
  expect(screen.getByText('Sentiment: Neutral')).toBeInTheDocument();
  expect(screen.getByText('70/100 indicator')).toBeInTheDocument();
  expect(screen.getByText('Original report summary')).toBeInTheDocument();
});
test('opens a stable article route',()=>{
  render(<MemoryRouter><Routes><Route path="/" element={<ArticleCard article={article}/>}/><Route path="/article/42" element={<p>Article opened</p>}/></Routes></MemoryRouter>);
  fireEvent.click(screen.getByText('Transport funding'));
  expect(screen.getByText('Article opened')).toBeInTheDocument();
});
