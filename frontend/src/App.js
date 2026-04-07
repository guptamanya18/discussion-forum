/** This is the big file that shows different pages of our website. */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import Login from './pages/Login';
import Register from './pages/Register';
import Home from './pages/Home';
import CreateThread from './pages/CreateThread';
import ThreadDetail from './pages/ThreadDetail';
import Communities from './pages/Communities';
import CommunityDetail from './pages/CommunityDetail';
import Profile from './pages/Profile';
import Notifications from './pages/Notifications';
import Dashboard from './pages/Dashboard';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import SavedPosts from './pages/SavedPosts';

function App() {
const { token } = useAuth();

return (
  <BrowserRouter>
<Navbar />
<Routes>
<Route path="/login" element={!token ? <Login /> : <Navigate to="/" />} />
<Route path="/register" element={!token ? <Register /> : <Navigate to="/" />} />
<Route path="/forgot-password" element={!token ? <ForgotPassword /> : <Navigate to="/" />} />
<Route path="/reset-password" element={!token ? <ResetPassword /> : <Navigate to="/" />} />
<Route path="/" element={token ? <Home /> : <Navigate to="/login" />} />
<Route path="/threads/new" element={token ? <CreateThread /> : <Navigate to="/login" />} />
<Route path="/threads/:id" element={token ? <ThreadDetail /> : <Navigate to="/login" />} />
<Route path="/communities" element={token ? <Communities /> : <Navigate to="/login" />} />
<Route path="/communities/:slug" element={token ? <CommunityDetail /> : <Navigate to="/login" />} />
<Route path="/profile" element={token ? <Profile /> : <Navigate to="/login" />} />
<Route path="/notifications" element={token ? <Notifications /> : <Navigate to="/login" />} />
<Route path="/dashboard" element={token ? <Dashboard /> : <Navigate to="/login" />} />
<Route path="/saved" element={token ? <SavedPosts /> : <Navigate to="/login" />} />
</Routes>
</BrowserRouter>
);
}

export default App;