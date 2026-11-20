import React from 'react';
import {render,screen,fireEvent} from '@testing-library/react';
import {MemoryRouter,Routes,Route} from 'react-router-dom';
import ArticleDetailPage from './ArticleDetailPage';
const mockGetArticle=jest.fn();
jest.mock('../context/AuthContext',()=>({useAuth:()=>({getArticle:mockGetArticle})}));
jest.mock('../context/BookmarkContext',()=>({useBookmarks:()=>({bookmarks:[],isBookmarked:()=>false,toggleBookmark:jest.fn()})}));
jest.mock('../context/ReadArticlesContext',()=>({useReadArticles:()=>({markAsRead:jest.fn()})}));
beforeEach(()=>{mockGetArticle.mockReset();window.scrollTo=jest.fn();});
const open = () => render(<MemoryRouter initialEntries={['/article/abc']}><Routes><Route path="/article/:id" element={<ArticleDetailPage/>}/></Routes></MemoryRouter>);
test('loads a copied article URL without navigation state or bookmark',async()=>{
 mockGetArticle.mockResolvedValue({id:'abc',title:'Retrieved article',date:'2026-10-15T00:00:00Z',sentiment:'Neutral',description:'Stored summary',source:'Publisher'});
 open();
 expect(await screen.findByRole('heading',{name:'Retrieved article'})).toBeInTheDocument();
 expect(mockGetArticle).toHaveBeenCalledWith('abc');
 expect(screen.getByRole('region',{name:'Article analysis'})).toBeInTheDocument();
});
test('shows an explicit missing-article state',async()=>{
 mockGetArticle.mockRejectedValue({response:{status:404}});
 open();
 expect(await screen.findByText('Article not found.')).toBeInTheDocument();
});
const stored = {id:'abc',title:'Retrieved article',date:'2026-10-15T00:00:00Z',sentiment:'Neutral',description:'Stored summary',source:'Publisher'};
const routes = (entries, index) => render(<MemoryRouter initialEntries={entries} initialIndex={index}><Routes>
  <Route path="/article/:id" element={<ArticleDetailPage/>}/>
  <Route path="/feed" element={<p>Feed page</p>}/>
  <Route path="/bookmarks" element={<p>Bookmarks page</p>}/>
</Routes></MemoryRouter>);
test('Back goes to the feed when the article was opened from a shared link',async()=>{
 mockGetArticle.mockResolvedValue(stored);
 routes(['/article/abc'], 0);
 await screen.findByRole('heading',{name:'Retrieved article'});
 fireEvent.click(screen.getByRole('button',{name:/Back/}));
 expect(await screen.findByText('Feed page')).toBeInTheDocument();
});
test('Back returns to the previous page when opened inside the app',async()=>{
 mockGetArticle.mockResolvedValue(stored);
 routes(['/bookmarks', {pathname:'/article/abc', state:{article:stored}}], 1);
 await screen.findByRole('heading',{name:'Retrieved article'});
 fireEvent.click(screen.getByRole('button',{name:/Back/}));
 expect(await screen.findByText('Bookmarks page')).toBeInTheDocument();
});

test('tone appears only once, inside Article Analysis', async () => {
  mockGetArticle.mockResolvedValue({ ...stored, toneLabel: 'Neutral / Objective', categories: ['Politics'] });
  render(<MemoryRouter initialEntries={['/article/abc']}><Routes><Route path="/article/:id" element={<ArticleDetailPage />} /></Routes></MemoryRouter>);
  await screen.findByText('Retrieved article');
  expect(screen.getAllByText(/Neutral \/ Objective/)).toHaveLength(1);
  expect(screen.getByText(/Neutral \/ Objective/).closest('.article-analysis, section, div')).toBeTruthy();
  expect(document.querySelector('.tone-badge')).toBeNull();
});

test('the original article button just says Read Original Article', async () => {
  mockGetArticle.mockResolvedValue({ ...stored, url: 'https://www.nst.com.my/news/x' });
  render(<MemoryRouter initialEntries={['/article/abc']}><Routes><Route path="/article/:id" element={<ArticleDetailPage />} /></Routes></MemoryRouter>);
  const link = await screen.findByRole('link', { name: /Read Original Article/ });
  expect(link.textContent).toBe('Read Original Article');
  expect(link).toHaveAttribute('href', 'https://www.nst.com.my/news/x');
});
