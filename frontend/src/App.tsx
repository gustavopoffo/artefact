import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ChatClient from './components/ChatClient';
import AdminLayout from './layouts/AdminLayout';
import AdminConversations from './components/AdminConversations';
import AdminDashboard from './components/AdminDashboard';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Cliente - Chat */}
        <Route path="/" element={<ChatClient />} />
        
        {/* Admin */}
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<AdminConversations />} />
          <Route path="dashboard" element={<AdminDashboard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
