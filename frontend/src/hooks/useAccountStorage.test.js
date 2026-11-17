import React from 'react';
import {renderHook,act} from '@testing-library/react';
import {useAccountStorage} from './useAccountStorage';
let mockUser={email:'first@example.com'};
jest.mock('../context/AuthContext',()=>({useAuth:()=>({user:mockUser})}));
const empty=[];
test('account switching does not overwrite or expose another account records',()=>{
 localStorage.clear(); mockUser={email:'first@example.com'};
 const {result,rerender}=renderHook(()=>useAccountStorage('history',empty));
 act(()=>result.current[1]([{id:'first'}]));
 mockUser={email:'second@example.com'};rerender();
 expect(result.current[0]).toEqual([]);
 act(()=>result.current[1]([{id:'second'}]));
 mockUser={email:'first@example.com'};rerender();
 expect(result.current[0]).toEqual([{id:'first'}]);
 expect(JSON.parse(localStorage.getItem('history:second@example.com'))).toEqual([{id:'second'}]);
});
