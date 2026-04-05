import { useEffect, useState } from 'react';
import api from '../api/api';
import { useAuth } from '../context/AuthContext';
import {
  Container, Typography, Box, Button, Alert,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, Select, MenuItem, TextField, Chip
} from '@mui/material';
import UserAvatar from '../components/UserAvatar';

function AdminPanel() {
  const { user, refreshUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [stats, setStats] = useState(null);
  const [search, setSearch] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (user?.role === 'admin') {
      fetchUsers();
      fetchStats();
    }
  }, [user, search]);

  const fetchUsers = async () => {
    try {
      const params = {};
      if (search) params.search = search;
      const res = await api.get('/users/admin/users', { params });
      setUsers(res.data);
    } catch (err) {
      console.error('Failed to fetch users');
    }
  };

  const fetchStats = async () => {
    try {
      const res = await api.get('/users/admin/stats');
      setStats(res.data);
    } catch (err) {
      console.error('Failed to fetch stats');
    }
  };

  const handleRoleChange = async (userId, newRole) => {
    setMessage('');
    setError('');
    try {
      await api.put('/users/' + userId, { role: newRole });
      setMessage('Role updated successfully');
      fetchUsers();
      fetchStats();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update role');
    }
  };

  const handleStatusChange = async (userId, isActive) => {
    setMessage('');
    setError('');
    try {
      await api.post(`/users/admin/users/${userId}/status`, null, {
        params: { is_active: isActive }
      });
      setMessage(`User ${isActive ? 'activated' : 'deactivated'} successfully`);
      fetchUsers();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update user status');
    }
  };

  const handleDelete = async (userId, username) => {
    if (!window.confirm('Delete user "' + username + '"? This cannot be undone.')) return;
    setMessage('');
    setError('');
    try {
      await api.delete('/users/admin/users/' + userId);
      setMessage('User deleted');
      fetchUsers();
      fetchStats();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete user');
    }
  };

  const handleInitAdmin = async () => {
    setMessage('');
    setError('');
    try {
      const res = await api.post('/users/init-admin');
      setMessage(res.data.message);
      refreshUser();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to initialize admin');
    }
  };

  // If user is not admin, deny access
  if (user?.role !== 'admin') {
    return (
      <Box sx={{ maxWidth: 600, mx: 'auto', px: { xs: 1, sm: 2, md: 3 }, mt: 4, textAlign: 'center' }}>
        <Typography variant="h5" gutterBottom>Admin Panel</Typography>
        <Typography color="text.secondary" sx={{ mb: 3 }}>
          You do not have admin access. Contact an administrator to get promoted.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', px: { xs: 1, sm: 2, md: 3 }, mt: 2.5 }}>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 700 }}>Admin Panel</Typography>

      {message && <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert>}
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {stats && (
        <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
          <Chip label={'Total Users: ' + stats.total_users} color="primary" />
          {Object.entries(stats.roles || {}).map(([role, count]) => (
            <Chip key={role} label={role + ': ' + count} variant="outlined" />
          ))}
        </Box>
      )}

      <TextField
        label="Search users..."
        size="small"
        fullWidth
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        sx={{ mb: 3 }}
      />

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell></TableCell>
              <TableCell>Username</TableCell>
              <TableCell>Email</TableCell>
              <TableCell>Role</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Joined</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {users.map((u) => (
              <TableRow key={u.id} sx={{ opacity: u.is_active ? 1 : 0.6 }}>
                <TableCell>{u.id}</TableCell>
                <TableCell><UserAvatar user={u} size={32} /></TableCell>
                <TableCell>
                  {u.username}
                  {!u.is_active && <Chip label="Deactivated" color="error" size="small" sx={{ ml: 1, height: 20, fontSize: '0.65rem' }} />}
                </TableCell>
                <TableCell>{u.email}</TableCell>
                <TableCell>
                  <Select
                    value={u.role}
                    size="small"
                    onChange={(e) => handleRoleChange(u.id, e.target.value)}
                    disabled={u.id === user.id || !u.is_active}
                  >
                    <MenuItem value="member">member</MenuItem>
                    <MenuItem value="moderator">moderator</MenuItem>
                    <MenuItem value="admin">admin</MenuItem>
                  </Select>
                </TableCell>
                <TableCell>
                  <Button
                    size="small"
                    variant="outlined"
                    color={u.is_active ? "warning" : "success"}
                    onClick={() => handleStatusChange(u.id, !u.is_active)}
                    disabled={u.id === user.id}
                  >
                    {u.is_active ? 'Deactivate' : 'Activate'}
                  </Button>
                </TableCell>
                <TableCell>{new Date(u.created_at).toLocaleDateString()}</TableCell>
                <TableCell>
                  <Button
                    size="small"
                    color="error"
                    onClick={() => handleDelete(u.id, u.username)}
                    disabled={u.id === user.id}
                  >
                    Delete
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

export default AdminPanel;
