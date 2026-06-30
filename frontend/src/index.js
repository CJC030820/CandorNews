import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { LDProvider } from "ldclient-react";
import { LDClient } from "ldclient-js";

const clientSideId = process.env.REACT_APP_LD_CLIENT_SIDE_ID;
const ldClient = LDClient.init(clientSideId);

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <LDProvider client={ldClient}>
      <App />
    </LDProvider>
  </React.StrictMode>
);