/** This page is for moderators to review reported threads and manage things. */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/api';
import { useAuth } from '../context/AuthContext';
import {
  Container, Typography, Box, TextField, Chip, Card, CardContent,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, Button, Alert, Tabs, Tab, List, ListItem, ListItemText, ListItemAvatar, IconButton
} from '@mui/material';
import UserAvatar from '../components/UserAvatar';
import DeleteIcon from '@mui/icons-material/Delete';
import VisibilityIcon from '@mui/icons-material/Visibility';
import PeopleIcon from '@mui/icons-material/People';
import ForumIcon from '@mui/icons-material/Forum';
import ChatBubbleIcon from '@mui/icons-material/ChatBubble';

function ModeratorPanel() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState(0);
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [threads, setThreads] = useState([]);
  const [search, setSearch] = useState('');
  const [threadSearch, setThreadSearch] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (user?.role === 'moderator' || user?.role === 'admin') {
      fetchStats();
    }
  }, [user]);

  useEffect(() => {
    if (tab === 0) fetchStats();
    if (tab === 1) fetchUsers();
    if (tab === 2) fetchThreads();
  }, [tab, search, threadSearch]);

  const fetchStats = async () => {
    try {
      const res = await api.get('/users/mod/stats');
      setStats(res.data);
    } catch (err) {
      console.error('Failed to fetch stats');
    }
  };

  const fetchUsers = async () => {
    try {
      const params = {};
      if (search) params.search = search;
      const res = await api.get('/users/mod/users', { params });
      setUsers(res.data.users || []);
    } catch (err) {
      console.error('Failed to fetch users');
    }
  };

  const fetchThreads = async () => {
    try {
      const params = { limit: 20 };
      if (threadSearch) params.search = threadSearch;
      const res = await api.get('/threads', { params });
      setThreads(res.data.items);
    } catch (err) {
      console.error('Failed to fetch threads');
    }
  };

  const handleDeleteThread = async (threadId, title) => {
    if (!window.confirm(`Delete thread "${title}"? This is a soft delete.`)) return;
    setMessage('');
    setError('');
    try {
      await api.delete('/threads/' + threadId);
      setMessage('Thread deleted successfully');
      fetchThreads();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete thread');
    }
  };

  if (user?.role !== 'moderator' && user?.role !== 'admin') {
    return (
      <Box sx={{ maxWidth: 600, mx: 'auto', px: { xs: 1, sm: 2, md: 3 }, mt: 4, textAlign: 'center' }}>
        <Typography variant="h5">Moderator Panel</Typography>
        <Typography color="text.secondary" sx={{ mt: 2 }}>
          You do not have moderator access.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', px: { xs: 1, sm: 2, md: 3 }, mt: 2.5 }}>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 700 }}>Moderator Dashboard</Typography>

      {message && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage('')}>{message}</Alert>}
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

      <Tabs value={tab} onChange={(e, v) => setTab(v)} sx={{ mb: 3 }}>
        <Tab icon={<ForumIcon />} label="Overview" />
        <Tab icon={<PeopleIcon />} label="Users" />
        <Tab icon={<ChatBubbleIcon />} label="Threads" />
      </Tabs>

      {/* Overview Tab */}
      {tab === 0 && stats && (
        <Box>
          <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
            <Card sx={{ minWidth: 150 }}>
              <CardContent>
                <Typography variant="h3" color="primary">{stats.total_users}</Typography>
                <Typography variant="body2" color="text.secondary">Total Users</Typography>
              </CardContent>
            </Card>
            {Object.entries(stats.roles || {}).map(([role, count]) => (
              <Card key={role} sx={{ minWidth: 120 }}>
                <CardContent>
                  <Typography variant="h4">{count}</Typography>
                  <Typography variant="body2" color="text.secondary">{role}s</Typography>
                </CardContent>
              </Card>
            ))}
          </Box>

          <Typography variant="h6" sx={{ mb: 1 }}>Recently Joined Users</Typography>
          <List>
            {(stats.recent_users || []).map(u => (
              <ListItem key={u.id}>
                <ListItemAvatar>
                  <UserAvatar user={u} size={32} />
                </ListItemAvatar>
                <ListItemText
                  primary={u.username}
                  secondary={`${u.role} · Joined ${new Date(u.created_at).toLocaleDateString()}`}
                />
              </ListItem>
            ))}
          </List>
        </Box>
      )}

      {/* Users Tab */}
      {tab === 1 && (
        <Box>
          <TextField
            label="Search users..."
            size="small"
            fullWidth
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell></TableCell>
                  <TableCell>Username</TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>Role</TableCell>
                  <TableCell>Joined</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users.map(u => (
                  <TableRow key={u.id}>
                    <TableCell>{u.id}</TableCell>
                    <TableCell><UserAvatar user={u} size={28} /></TableCell>
                    <TableCell>{u.username}</TableCell>
                    <TableCell>{u.email}</TableCell>
                    <TableCell><Chip label={u.role} size="small" color={u.role === 'admin' ? 'error' : u.role === 'moderator' ? 'warning' : 'default'} /></TableCell>
                    <TableCell>{new Date(u.created_at).toLocaleDateString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {/* Threads Tab */}
      {tab === 2 && (
        <Box>
          <TextField
            label="Search threads..."
            size="small"
            fullWidth
            value={threadSearch}
            onChange={(e) => setThreadSearch(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell>Title</TableCell>
                  <TableCell>Author</TableCell>
                  <TableCell>Likes</TableCell>
                  <TableCell>Comments</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {threads.map(t => (
                  <TableRow key={t.id}>
                    <TableCell>{t.id}</TableCell>
                    <TableCell>{t.title}</TableCell>
                    <TableCell>{t.author?.username || 'Unknown'}</TableCell>
                    <TableCell>{t.like_count}</TableCell>
                    <TableCell>{t.reply_count}</TableCell>
                    <TableCell>
                      <IconButton size="small" onClick={() => navigate('/threads/' + t.id)}>
                        <VisibilityIcon fontSize="small" />
                      </IconButton>
                      <IconButton size="small" color="error" onClick={() => handleDeleteThread(t.id, t.title)}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}
    </Box>
  );
}

export default ModeratorPanel;
