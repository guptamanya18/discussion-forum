/** This page shows all the communities you can browse and join. */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/api';
import { useAuth } from '../context/AuthContext';
import {
  Typography, Card, CardContent, CardActions, Button,
  Box, TextField, Dialog, DialogTitle, DialogContent, DialogActions, Alert, Pagination,
  InputAdornment, Grid, Chip, Snackbar
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import GroupsIcon from '@mui/icons-material/Groups';
import AddIcon from '@mui/icons-material/Add';
import PeopleIcon from '@mui/icons-material/People';

function Communities() {
  const PAGE_SIZE = 12;
  const { token, user } = useAuth();
  const [communities, setCommunities] = useState([]);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState('');
  const [snack, setSnack] = useState({ open: false, message: '', severity: 'error' });

  useEffect(() => {
    fetchCommunities();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, page]);

  useEffect(() => {
    setPage(1);
  }, [search]);

  const fetchCommunities = async () => {
    try {
      const params = { skip: (page - 1) * PAGE_SIZE, limit: PAGE_SIZE };
      if (search) params.search = search;
      const res = await api.get('/communities', { params });
      setCommunities(res.data.items);
      setTotalPages(Math.ceil(res.data.total / PAGE_SIZE));
    } catch (err) {
      console.error('Failed to fetch communities');
    }
  };

  const handleCreate = async () => {
    setError('');
    try {
      await api.post('/communities', { name, description });
      setOpen(false);
      setName('');
      setDescription('');
      fetchCommunities();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create community');
    }
  };

  const handleJoin = async (communityId) => {
    try {
      await api.post('/communities/' + communityId + '/join');
      fetchCommunities();
    } catch (err) {
      setSnack({ open: true, message: err.response?.data?.detail || 'Failed to join', severity: 'error' });
    }
  };

  return (
    <Box sx={{ maxWidth: '1400px', mx: 'auto', px: { xs: 2, sm: 3, md: 4 }, mt: 3, width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'stretch' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <GroupsIcon sx={{ fontSize: 36, color: 'primary.main' }} />
          <Typography variant="h4" sx={{ fontWeight: 800, letterSpacing: '-0.02em' }}>Explore Communities</Typography>
        </Box>
        {token && (
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setOpen(true)} sx={{ borderRadius: '24px', px: 4, py: 1, textTransform: 'none', fontWeight: 600, boxShadow: 2 }}>
            Create New
          </Button>
        )}
      </Box>

      <TextField
        placeholder="Search for a community..."
        size="medium"
        fullWidth
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        sx={{ mb: 4 }}
        InputProps={{
          startAdornment: <InputAdornment position="start"><SearchIcon sx={{ fontSize: 24, color: 'text.secondary', ml: 1 }} /></InputAdornment>,
          sx: { borderRadius: '28px', fontSize: '1rem', bgcolor: 'background.paper', '& fieldset': { borderColor: 'divider' } },
        }}
      />

      {communities.length === 0 && (
        <Card sx={{ p: 8, textAlign: 'center', borderRadius: 4, border: '1px dashed', borderColor: 'divider', bgcolor: 'transparent' }}>
          <GroupsIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
          <Typography variant="h6" color="text.secondary">No communities found matching your search.</Typography>
        </Card>
      )}

      <Grid container spacing={3} sx={{ width: '100%', m: 0 }}>
        {communities.map((c) => (
          <Grid item xs={12} sm={6} md={4} lg={3} xl={2.4} key={c.id}>
            <Card sx={{ 
              height: '100%', 
              display: 'flex', 
              flexDirection: 'column', 
              borderRadius: 3, 
              transition: 'transform 0.2s, box-shadow 0.2s',
              '&:hover': { transform: 'translateY(-4px)', boxShadow: 6 },
              border: '1px solid',
              borderColor: 'divider'
            }}>
              <Box sx={{ p: 2.5, pb: 1 }}>
                <Typography variant="h6" sx={{ color: 'text.primary', fontWeight: 700, lineHeight: 1.2 }}>{c.name}</Typography>
              </Box>
              <CardContent sx={{ flex: 1, p: 2.5, pt: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1.5 }}>
                  <PeopleIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                  <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary' }}>
                    {c.member_count || 0} members
                  </Typography>
                </Box>
                {c.description && (
                  <Typography variant="body2" color="text.secondary" sx={{ 
                    display: '-webkit-box', 
                    WebkitLineClamp: 3, 
                    WebkitBoxOrient: 'vertical', 
                    overflow: 'hidden',
                    lineHeight: 1.6
                  }}>
                    {c.description}
                  </Typography>
                )}
              </CardContent>
              <CardActions sx={{ px: 2.5, pb: 2.5, pt: 0, gap: 1 }}>
                <Button 
                  size="small" 
                  component={Link} 
                  to={'/communities/' + c.slug} 
                  variant="outlined" 
                  sx={{ borderRadius: '12px', flex: 1, textTransform: 'none', fontWeight: 600 }}
                >
                  View
                </Button>
                {token && user?.id !== c.created_by && (
                  <Button 
                    size="small" 
                    onClick={() => handleJoin(c.id)} 
                    variant="contained" 
                    sx={{ borderRadius: '12px', flex: 1, textTransform: 'none', fontWeight: 600 }}
                  >
                    Join
                  </Button>
                )}
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      {totalPages > 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
          <Pagination count={totalPages} page={page} onChange={(e, v) => setPage(v)} color="primary" />
        </Box>
      )}

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle sx={{ fontWeight: 700 }}>Create Community</DialogTitle>
        <DialogContent>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          <TextField label="Name" fullWidth margin="normal" value={name} onChange={(e) => setName(e.target.value)} required />
          <TextField label="Description" fullWidth margin="normal" multiline rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreate} sx={{ borderRadius: '20px', px: 3 }}>Create</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={snack.open} autoHideDuration={4000} onClose={() => setSnack(s => ({ ...s, open: false }))} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert severity={snack.severity} onClose={() => setSnack(s => ({ ...s, open: false }))} variant="filled">{snack.message}</Alert>
      </Snackbar>
    </Box>
  );
}

export default Communities;
