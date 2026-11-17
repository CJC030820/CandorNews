import React from 'react';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import TopicSelectionPage from './TopicSelectionPage';
const mockComplete=jest.fn().mockResolvedValue({});
jest.mock('../context/AuthContext',()=>({useAuth:()=>({completeTopicSelection:mockComplete})}));
test('persists selected topics',async()=>{
 render(<MemoryRouter><TopicSelectionPage/></MemoryRouter>);
 fireEvent.click(screen.getByRole('button',{name:/technology/i}));
 fireEvent.click(screen.getByRole('button',{name:/sports/i}));
 fireEvent.click(screen.getByRole('button',{name:/continue/i}));
 await waitFor(()=>expect(mockComplete).toHaveBeenCalledWith(['Technology','Sports']));
});
