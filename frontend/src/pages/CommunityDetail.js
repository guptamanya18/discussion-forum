import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import api from '../api/api';
import { useAuth } from '../context/AuthContext';
import {
  Typography, Box, Button, Card, CardContent, CardActions,
  List, ListItem, ListItemText, ListItemAvatar, Chip, Divider, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField, Select, MenuItem, IconButton, Snackbar, Alert
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import UserAvatar from '../components/UserAvatar';
import { displayUsername } from '../utils/displayUser';
import ConfirmDialog from '../components/ConfirmDialog';

function CommunityDetail() {
  const { slug } = useParams();
  const { token, user, broadcastEvent } = useAuth();
  const navigate = useNavigate();
  const [community, setCommunity] = useState(null);
  const [members, setMembers] = useState([]);
  const [threads, setThreads] = useState([]);
  const [editOpen, setEditOpen] = useState(false);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [snack, setSnack] = useState({ open: false, message: '', severity: 'success' });
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmData, setConfirmData] = useState({ title: '', message: '', onConfirm: null });

  useEffect(() => {
    fetchCommunity();
    fetchMembers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug]);

  // Fetch threads once community is loaded (thread service needs numeric id)
  useEffect(() => {
    if (community?.id) {
      fetchThreads();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [community?.id]);

  // Real-time updates for threads within this community
  useEffect(() => {
    if (!broadcastEvent) return;
    if (broadcastEvent.type === 'new_thread' && broadcastEvent.thread && String(broadcastEvent.thread.community_id) === String(community?.id)) {
      setThreads(prev => {
        if (prev.some(t => t.id === broadcastEvent.thread.id)) return prev;
        return [{ ...broadcastEvent.thread, like_count: 0, reply_count: 0 }, ...prev];
      });
    }
    if (broadcastEvent.type === 'thread_deleted') {
      setThreads(prev => prev.filter(t => t.id !== broadcastEvent.thread_id));
    }
    if (broadcastEvent.type === 'thread_like_update') {
      setThreads(prev => prev.map(t =>
        t.id === broadcastEvent.thread_id ? { ...t, like_count: broadcastEvent.like_count } : t
      ));
    }
    if (broadcastEvent.type === 'thread_edited' && broadcastEvent.thread_id) {
      setThreads(prev => prev.map(t => {
        if (t.id !== broadcastEvent.thread_id) return t;
        const updated = { ...t };
        if (broadcastEvent.title !== undefined) updated.title = broadcastEvent.title;
        return updated;
      }));
    }
  }, [broadcastEvent, community?.id]);

  const fetchCommunity = async () => {
    try {
      const res = await api.get('/communities/' + slug);
      setCommunity(res.data);
    } catch (err) {
      console.error('Failed to fetch community');
    }
  };

  const fetchMembers = async () => {
    try {
      const res = await api.get('/communities/' + slug + '/members');
      setMembers(res.data);
    } catch (err) {
      console.error('Failed to fetch members');
    }
  };

  const fetchThreads = async () => {
    try {
      const res = await api.get('/threads', { params: { community_id: community.id } });
      setThreads(res.data.items);
    } catch (err) {
      console.error('Failed to fetch community threads');
    }
  };

  const handleJoin = async () => {
    try {
      await api.post('/communities/' + slug + '/join');
      fetchCommunity();
      fetchMembers();
    } catch (err) {
      setSnack({ open: true, message: err.response?.data?.detail || 'Failed to join', severity: 'error' });
    }
  };

  const handleLeave = async () => {
    try {
      await api.delete('/communities/' + slug + '/leave');
      fetchCommunity();
      fetchMembers();
    } catch (err) {
      setSnack({ open: true, message: err.response?.data?.detail || 'Failed to leave', severity: 'error' });
    }
  };

  const handleEditCommunity = async () => {
    try {
      const res = await api.put('/communities/' + slug, { name: editName, description: editDescription });
      setEditOpen(false);
      if (res.data.slug !== slug) {
        navigate('/communities/' + res.data.slug, { replace: true });
      } else {
        fetchCommunity();
      }
    } catch (err) {
      setSnack({ open: true, message: err.response?.data?.detail || 'Failed to update community', severity: 'error' });
    }
  };

  const handleDeleteCommunity = () => {
    setConfirmData({
      title: 'Delete Community',
      message: 'Are you sure you want to delete this community? This cannot be undone.',
      onConfirm: async () => {
        setConfirmOpen(false);
        try {
          await api.delete('/communities/' + slug);
          navigate('/communities');
        } catch (err) {
          setSnack({ open: true, message: err.response?.data?.detail || 'Failed to delete community', severity: 'error' });
        }
      },
    });
    setConfirmOpen(true);
  };

  const handleChangeRole = async (userId, newRole) => {
    try {
      await api.put('/communities/' + slug + '/members/' + userId + '/role', null, { params: { role: newRole } });
      fetchMembers();
    } catch (err) {
      setSnack({ open: true, message: err.response?.data?.detail || 'Failed to change role', severity: 'error' });
    }
  };

  if (!community) return <Box sx={{ maxWidth: 900, mx: 'auto', px: { xs: 1, sm: 2, md: 3 }, mt: 4 }}><Typography>Loading...</Typography></Box>;

  const isMember = members.some((m) => m.user_id === user?.id);
  const isCreator = community.created_by === user?.id;
  const isAdmin = user?.role === 'admin';
  const canManage = isCreator || isAdmin;

  return (
    <Box sx={{ maxWidth: 900, mx: 'auto', px: { xs: 1, sm: 2, md: 3 }, mt: 2.5 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="h4">{community.name}</Typography>
          {canManage && (
            <>
              <IconButton onClick={() => { setEditName(community.name); setEditDescription(community.description || ''); setEditOpen(true); }}><EditIcon /></IconButton>
              <IconButton color="error" onClick={handleDeleteCommunity}><DeleteIcon /></IconButton>
            </>
          )}
        </Box>
        {token && (
          isMember
            ? (!isCreator && <Button variant="outlined" color="error" onClick={handleLeave}>Leave</Button>)
            : <Button variant="contained" onClick={handleJoin}>Join</Button>
        )}
      </Box>

      {community.description && (
        <Typography variant="body1" sx={{ mb: 2 }}>{community.description}</Typography>
      )}
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {community.member_count || 0} members | Created {new Date(community.created_at).toLocaleDateString()}
      </Typography>

      <Divider sx={{ my: 2 }} />
      <Typography variant="h5" gutterBottom>Members</Typography>
      <List dense>
        {members.map((m) => (
          <ListItem key={m.id}>
            <ListItemAvatar>
              <UserAvatar user={m} size={32} />
            </ListItemAvatar>
            <ListItemText primary={m.username} />
            {canManage && m.user_id !== user?.id ? (
              <Select
                value={m.role}
                size="small"
                onChange={(e) => handleChangeRole(m.user_id, e.target.value)}
                sx={{ minWidth: 120 }}
              >
                <MenuItem value="member">member</MenuItem>
                <MenuItem value="moderator">moderator</MenuItem>
              </Select>
            ) : (
              <Chip label={m.role} size="small" color={m.role === 'moderator' ? 'primary' : 'default'} />
            )}
          </ListItem>
        ))}
      </List>

      <Divider sx={{ my: 2 }} />
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h5" gutterBottom>Threads</Typography>
        {token && isMember && (
          <Button variant="contained" size="small" onClick={() => navigate('/threads/new?community_id=' + community.id)}>
            New Thread
          </Button>
        )}
      </Box>
      {threads.length === 0 && <Typography color="text.secondary">No threads in this community yet.</Typography>}
      {threads.map((thread) => (
        <Card key={thread.id} sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6">{thread.title}</Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <UserAvatar user={thread.author} size={22} />
              <Typography variant="body2" color="text.secondary">
                {displayUsername(thread.author?.username)} | Likes: {thread.like_count || 0}
              </Typography>
            </Box>
          </CardContent>
          <CardActions>
            <Button size="small" component={Link} to={'/threads/' + thread.id}>View</Button>
          </CardActions>
        </Card>
      ))}

      <Dialog open={editOpen} onClose={() => setEditOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Edit Community</DialogTitle>
        <DialogContent>
          <TextField label="Name" fullWidth margin="normal" value={editName} onChange={(e) => setEditName(e.target.value)} />
          <TextField label="Description" fullWidth margin="normal" multiline rows={3} value={editDescription} onChange={(e) => setEditDescription(e.target.value)} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleEditCommunity}>Save</Button>
        </DialogActions>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        title={confirmData.title}
        message={confirmData.message}
        onConfirm={confirmData.onConfirm}
        onCancel={() => setConfirmOpen(false)}
        confirmText="Delete"
      />

      <Snackbar open={snack.open} autoHideDuration={4000} onClose={() => setSnack(s => ({ ...s, open: false }))} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert severity={snack.severity} onClose={() => setSnack(s => ({ ...s, open: false }))} variant="filled">{snack.message}</Alert>
      </Snackbar>
    </Box>
  );
}

export default CommunityDetail;
