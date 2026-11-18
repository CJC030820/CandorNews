import React from 'react';
import {render,screen,fireEvent,act} from '@testing-library/react';
import {MemoryRouter,Routes,Route} from 'react-router-dom';
import ArticleCard from './ArticleCard';
jest.mock('../context/BookmarkContext',()=>({useBookmarks:()=>({isBookmarked:()=>false,toggleBookmark:jest.fn()})}));
jest.mock('../context/ReadArticlesContext',()=>({useReadArticles:()=>({isRead:()=>false})}));
const article={id:'42',title:'Transport funding',source:'News outlet',date:'15 Oct 2026',description:'Original report summary',category:'Politics',sentiment:'Neutral',trustScore:70};
test('renders source-linked summary, polarity and heuristic score',()=>{
  render(<MemoryRouter><ArticleCard article={article}/></MemoryRouter>);
  expect(screen.getByText('Sentiment: Neutral')).toBeInTheDocument();
  expect(screen.getByText('70/100 trust')).toBeInTheDocument();
  expect(screen.getByText('Original report summary')).toBeInTheDocument();
});
test('opens a stable article route',()=>{
  render(<MemoryRouter><Routes><Route path="/" element={<ArticleCard article={article}/>}/><Route path="/article/42" element={<p>Article opened</p>}/></Routes></MemoryRouter>);
  fireEvent.click(screen.getByText('Transport funding'));
  expect(screen.getByText('Article opened')).toBeInTheDocument();
});
test('falls back to the stored image copy, then to the placeholder',()=>{
  const {container}=render(<MemoryRouter><ArticleCard article={{...article,image:'https://www.bernama.com/storage/photos/a-medium'}}/></MemoryRouter>);
  const img=()=>container.querySelector('.article-image img');
  expect(img().getAttribute('src')).toBe('https://www.bernama.com/storage/photos/a-medium');
  fireEvent.error(img());
  expect(img().getAttribute('src')).toBe('http://localhost:8080/api/articles/42/image');
  fireEvent.error(img());
  expect(img()).toBeNull();
  expect(container.querySelector('.image-placeholder-card')).not.toBeNull();
});
test('shows the placeholder when an article has no image',()=>{
  const {container}=render(<MemoryRouter><ArticleCard article={article}/></MemoryRouter>);
  expect(container.querySelector('.article-image img')).toBeNull();
});
test('skips an image that hangs without loading or failing',()=>{
  jest.useFakeTimers();
  const {container}=render(<MemoryRouter><ArticleCard article={{...article,image:'https://www.bernama.com/storage/photos/b-medium'}}/></MemoryRouter>);
  const img=()=>container.querySelector('.article-image img');
  act(()=>{jest.advanceTimersByTime(8000);});
  expect(img().getAttribute('src')).toBe('http://localhost:8080/api/articles/42/image');
  fireEvent.load(img());
  act(()=>{jest.advanceTimersByTime(20000);});
  expect(img().getAttribute('src')).toBe('http://localhost:8080/api/articles/42/image');
  jest.useRealTimers();
});
