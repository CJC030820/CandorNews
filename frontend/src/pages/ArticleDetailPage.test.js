import React from 'react';
import {render,screen} from '@testing-library/react';
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
