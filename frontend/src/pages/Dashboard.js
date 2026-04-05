import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../api/api';
import { useAuth } from '../context/AuthContext';
import {
  Typography, Box, Card, CardContent, CardActions, Button, Chip,
  Grid, Divider,
  Tabs, Tab, TextField, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Paper, Select, MenuItem, IconButton, Alert
} from '@mui/material';
import UserAvatar from '../components/UserAvatar';
import ForumIcon from '@mui/icons-material/Forum';
import GroupsIcon from '@mui/icons-material/Groups';
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutline';
import NotificationsIcon from '@mui/icons-material/Notifications';
import AddIcon from '@mui/icons-material/Add';
import ThumbUpAltOutlinedIcon from '@mui/icons-material/ThumbUpAltOutlined';
import PeopleIcon from '@mui/icons-material/People';
import VisibilityIcon from '@mui/icons-material/Visibility';
import DeleteIcon from '@mui/icons-material/Delete';
import SettingsIcon from '@mui/icons-material/Settings';
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings';
import FlagIcon from '@mui/icons-material/Flag';
import ConfirmDialog from '../components/ConfirmDialog';

function Dashboard() {
  const { user, unreadCount } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState(0);

  // Overview state
  const [dashboardData, setDashboardData] = useState(null);

  // My Communities state
  const [ownedCommunities, setOwnedCommunities] = useState([]);
  const [memberCommunities, setMemberCommunities] = useState([]);

  // My Threads state
  const [myThreads, setMyThreads] = useState([]);

  // Manage Platform state (staff only)
  const [platformStats, setPlatformStats] = useState(null);
  const [platformUsers, setPlatformUsers] = useState([]);
  const [platformThreads, setPlatformThreads] = useState([]);
  const [userSearch, setUserSearch] = useState('');
  const [threadSearch, setThreadSearch] = useState('');

  // Reports state (staff only)
  const [reports, setReports] = useState([]);
  const [reportsTotal, setReportsTotal] = useState(0);
  const [reportFilter, setReportFilter] = useState('pending');

  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmData, setConfirmData] = useState({ title: '', message: '', onConfirm: null });

  const isAdmin = user?.role === 'admin';
  const isMod = user?.role === 'moderator';
  const isStaff = isAdmin || isMod;

  // Build tabs dynamically
  const tabs = [
    { label: 'Overview', icon: <ForumIcon /> },
    { label: 'My Communities', icon: <GroupsIcon /> },
    { label: 'My Threads', icon: <ChatBubbleOutlineIcon /> },
  ];
  if (isStaff) tabs.push({ label: 'Manage Platform', icon: <AdminPanelSettingsIcon /> });
  if (isStaff) tabs.push({ label: 'Reports', icon: <FlagIcon /> });

  // Fetch data based on active tab
  useEffect(() => {
    const tabLabel = tabs[tab]?.label;
    if (tabLabel === 'Overview') fetchDashboard();
    if (tabLabel === 'My Communities') fetchMyCommunities();
    if (tabLabel === 'My Threads') fetchMyThreads();
    if (tabLabel === 'Manage Platform') { fetchPlatformStats(); fetchPlatformUsers(); fetchPlatformThreads(); }
    if (tabLabel === 'Reports') fetchReports();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  // Re-fetch on search change
  useEffect(() => {
    if (tabs[tab]?.label === 'Manage Platform') fetchPlatformUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userSearch]);
  useEffect(() => {
    if (tabs[tab]?.label === 'Manage Platform') fetchPlatformThreads();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threadSearch]);
  useEffect(() => {
    if (tabs[tab]?.label === 'Reports') fetchReports();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportFilter]);

  // ── Fetchers ───────────────────────────────────────────────────
  const fetchDashboard = async () => {
    try {
      const res = await api.get('/users/me/dashboard');
      setDashboardData(res.data);
    } catch (err) { console.error('Failed to fetch dashboard'); }
  };

  const fetchMyCommunities = async () => {
    try {
      const res = await api.get('/communities/my');
      setOwnedCommunities(res.data.owned || []);
      setMemberCommunities(res.data.member_of || []);
    } catch (err) { console.error('Failed to fetch my communities'); }
  };

  const fetchMyThreads = async () => {
    try {
      const res = await api.get('/threads', { params: { limit: 50 } });
      const mine = (res.data.items || []).filter(t => t.author?.id === user?.id);
      setMyThreads(mine);
    } catch (err) { console.error('Failed to fetch threads'); }
  };

  const fetchPlatformStats = async () => {
    try {
      const endpoint = isAdmin ? '/users/admin/stats' : '/users/mod/stats';
      const res = await api.get(endpoint);
      setPlatformStats(res.data);
    } catch (err) { console.error('Failed to fetch stats'); }
  };

  const fetchPlatformUsers = async () => {
    try {
      const params = {};
      if (userSearch) params.search = userSearch;
      const endpoint = isAdmin ? '/users/admin/users' : '/users/mod/users';
      const res = await api.get(endpoint, { params });
      setPlatformUsers(isAdmin ? res.data : (res.data.users || []));
    } catch (err) { console.error('Failed to fetch users'); }
  };

  const fetchPlatformThreads = async () => {
    try {
      const params = { limit: 20 };
      if (threadSearch) params.search = threadSearch;
      const res = await api.get('/threads', { params });
      setPlatformThreads(res.data.items || []);
    } catch (err) { console.error('Failed to fetch threads'); }
  };

  const fetchReports = async () => {
    try {
      const params = { limit: 50 };
      if (reportFilter) params.status = reportFilter;
      const res = await api.get('/reports', { params });
      setReports(res.data.items || []);
      setReportsTotal(res.data.total || 0);
    } catch (err) { console.error('Failed to fetch reports'); }
  };

  const handleReportStatus = async (reportId, newStatus) => {
    setMessage(''); setError('');
    try {
      await api.put('/reports/' + reportId + '/status?status=' + newStatus);
      setMessage('Report ' + newStatus);
      fetchReports();
    } catch (err) { setError(err.response?.data?.detail || 'Failed to update report'); }
  };

  // ── Actions ────────────────────────────────────────────────────
  const askConfirm = (title, message, onConfirm, confirmText, confirmColor) => {
    setConfirmData({ title, message, onConfirm, confirmText, confirmColor });
    setConfirmOpen(true);
  };

  const handleDeleteThread = (threadId, title) => {
    askConfirm('Delete Thread', `Delete thread "${title}"? This is a soft delete.`, async () => {
      setConfirmOpen(false);
      setMessage(''); setError('');
      try {
        await api.delete('/threads/' + threadId);
        setMessage('Thread deleted');
        fetchPlatformThreads();
        fetchMyThreads();
      } catch (err) { setError(err.response?.data?.detail || 'Failed to delete thread'); }
    });
  };

  const handleRoleChange = async (userId, newRole) => {
    setMessage(''); setError('');
    try {
      await api.put('/users/' + userId, { role: newRole });
      setMessage('Role updated');
      fetchPlatformUsers();
      fetchPlatformStats();
    } catch (err) { setError(err.response?.data?.detail || 'Failed to update role'); }
  };

  const handleDeleteUser = (userId, username) => {
    askConfirm('Delete User', `Delete user "${username}"? Their threads and comments will remain but show as "[deleted]". This cannot be undone.`, async () => {
      setConfirmOpen(false);
      setMessage(''); setError('');
      try {
        await api.delete('/users/admin/users/' + userId);
        setMessage('User deleted');
        fetchPlatformUsers();
        fetchPlatformStats();
      } catch (err) { setError(err.response?.data?.detail || 'Failed to delete user'); }
    });
  };

  const handleToggleStatus = (userId, username, currentlyActive) => {
    const action = currentlyActive ? 'Deactivate' : 'Activate';
    const detail = currentlyActive
      ? `Deactivate user "${username}"? They will be logged out and unable to use the platform. Their content will remain. You can reactivate later.`
      : `Activate user "${username}"? They will be able to log in and use the platform again.`;
    askConfirm(`${action} User`, detail, async () => {
      setConfirmOpen(false);
      setMessage(''); setError('');
      try {
        await api.post('/users/admin/users/' + userId + '/status?is_active=' + !currentlyActive);
        setMessage(`User ${action.toLowerCase()}d`);
        fetchPlatformUsers();
      } catch (err) { setError(err.response?.data?.detail || `Failed to ${action.toLowerCase()} user`); }
    }, action, currentlyActive ? 'warning' : 'success');
  };

  const profile = dashboardData?.user;
  const tabLabel = tabs[tab]?.label;

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', px: { xs: 1, sm: 2, md: 3 }, mt: 2.5 }}>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 700 }}>My Dashboard</Typography>

      {message && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage('')}>{message}</Alert>}
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

      <ConfirmDialog
        open={confirmOpen}
        title={confirmData.title}
        message={confirmData.message}
        onConfirm={confirmData.onConfirm}
        onCancel={() => setConfirmOpen(false)}
        confirmText={confirmData.confirmText || 'Delete'}
        confirmColor={confirmData.confirmColor || 'error'}
      />

      <Tabs
        value={tab}
        onChange={(e, v) => setTab(v)}
        variant="scrollable"
        scrollButtons="auto"
        sx={{ mb: 3, borderBottom: 1, borderColor: 'divider' }}
      >
        {tabs.map((t, i) => (
          <Tab key={i} icon={t.icon} label={t.label} iconPosition="start" />
        ))}
      </Tabs>

      {/* ═══════════════ OVERVIEW TAB ═══════════════ */}
      {tabLabel === 'Overview' && (
        <Box>
          {/* User Info Card */}
          {profile && (
            <Card sx={{ mb: 3, display: 'flex', alignItems: 'center', p: 2, flexWrap: 'wrap', gap: 2 }}>
              <UserAvatar user={profile} size={64} />
              <Box sx={{ flex: 1, minWidth: 200 }}>
                <Typography variant="h5">{profile.name || profile.username}</Typography>
                <Typography variant="body2" color="text.secondary">{profile.email}</Typography>
                <Box sx={{ display: 'flex', gap: 1, mt: 0.5, alignItems: 'center' }}>
                  <Chip label={profile.role} size="small" color={profile.role === 'admin' ? 'error' : profile.role === 'moderator' ? 'warning' : 'primary'} />
                  <Typography variant="caption" color="text.secondary">
                    Joined {new Date(profile.created_at).toLocaleDateString()}
                  </Typography>
                </Box>
                {profile.bio && <Typography variant="body2" sx={{ mt: 0.5 }}>{profile.bio}</Typography>}
              </Box>
              <Button component={Link} to="/profile" variant="outlined" size="small">Edit Profile</Button>
            </Card>
          )}

          {/* Quick Actions */}
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={6} sm={3}>
              <Card sx={{ textAlign: 'center', cursor: 'pointer' }} component={Link} to="/threads/new" style={{ textDecoration: 'none' }}>
                <CardContent>
                  <AddIcon color="primary" sx={{ fontSize: 40 }} />
                  <Typography variant="body2">New Thread</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card sx={{ textAlign: 'center', cursor: 'pointer' }} component={Link} to="/communities" style={{ textDecoration: 'none' }}>
                <CardContent>
                  <GroupsIcon color="primary" sx={{ fontSize: 40 }} />
                  <Typography variant="body2">Communities</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card sx={{ textAlign: 'center', cursor: 'pointer' }} component={Link} to="/" style={{ textDecoration: 'none' }}>
                <CardContent>
                  <ForumIcon color="primary" sx={{ fontSize: 40 }} />
                  <Typography variant="body2">Browse Threads</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card sx={{ textAlign: 'center', cursor: 'pointer' }} component={Link} to="/notifications" style={{ textDecoration: 'none' }}>
                <CardContent>
                  <NotificationsIcon color={unreadCount > 0 ? 'error' : 'primary'} sx={{ fontSize: 40 }} />
                  <Typography variant="body2">
                    Notifications {unreadCount > 0 && `(${unreadCount})`}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Box>
      )}

      {/* ═══════════════ MY COMMUNITIES TAB ═══════════════ */}
      {tabLabel === 'My Communities' && (
        <Box>
          {/* Communities I Own */}
          <Typography variant="h6" sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
            <SettingsIcon fontSize="small" /> Communities I Own
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            You created these communities and can manage their settings, members, and threads.
          </Typography>
          {ownedCommunities.length === 0 ? (
            <Card sx={{ mb: 3, p: 2 }}>
              <Typography color="text.secondary">You haven't created any communities yet.</Typography>
              <Button size="small" component={Link} to="/communities" sx={{ mt: 1 }}>Create One</Button>
            </Card>
          ) : (
            <Grid container spacing={2} sx={{ mb: 3 }}>
              {ownedCommunities.map(c => (
                <Grid item xs={12} sm={6} md={4} key={c.id}>
                  <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                    <CardContent sx={{ flex: 1 }}>
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>{c.name}</Typography>
                      <Chip label={`${c.member_count} members`} size="small" sx={{ mt: 0.5, mb: 1 }} />
                      <Typography variant="body2" color="text.secondary">
                        {c.description ? c.description.substring(0, 100) : 'No description'}
                      </Typography>
                    </CardContent>
                    <CardActions sx={{ justifyContent: 'space-between' }}>
                      <Button size="small" component={Link} to={'/communities/' + c.slug}>View</Button>
                      <Button size="small" variant="outlined" component={Link} to={'/communities/' + c.slug}>
                        Manage
                      </Button>
                    </CardActions>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}

          <Divider sx={{ my: 3 }} />

          {/* Communities I'm a Member of */}
          <Typography variant="h6" sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
            <GroupsIcon fontSize="small" /> Communities I Joined
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Communities you are a member of (created by someone else).
          </Typography>
          {memberCommunities.length === 0 ? (
            <Card sx={{ p: 2 }}>
              <Typography color="text.secondary">You haven't joined any other communities yet.</Typography>
              <Button size="small" component={Link} to="/communities" sx={{ mt: 1 }}>Browse Communities</Button>
            </Card>
          ) : (
            <Grid container spacing={2}>
              {memberCommunities.map(c => (
                <Grid item xs={12} sm={6} md={4} key={c.id}>
                  <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                    <CardContent sx={{ flex: 1 }}>
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>{c.name}</Typography>
                      <Chip label={`${c.member_count} members`} size="small" sx={{ mt: 0.5, mb: 1 }} />
                      <Typography variant="body2" color="text.secondary">
                        {c.description ? c.description.substring(0, 100) : 'No description'}
                      </Typography>
                    </CardContent>
                    <CardActions>
                      <Button size="small" component={Link} to={'/communities/' + c.slug}>View</Button>
                    </CardActions>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}
        </Box>
      )}

      {/* ═══════════════ MY THREADS TAB ═══════════════ */}
      {tabLabel === 'My Threads' && (
        <Box>
          {myThreads.length === 0 ? (
            <Card sx={{ p: 3 }}>
              <Typography color="text.secondary">You haven't created any threads yet.</Typography>
              <Button component={Link} to="/threads/new" variant="contained" sx={{ mt: 1 }}>Create Thread</Button>
            </Card>
          ) : (
            <TableContainer component={Paper}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Title</TableCell>
                    <TableCell align="center">Likes</TableCell>
                    <TableCell align="center">Comments</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {myThreads.map(t => (
                    <TableRow key={t.id} hover>
                      <TableCell>
                        <Typography
                          component={Link}
                          to={'/threads/' + t.id}
                          sx={{ textDecoration: 'none', color: 'primary.main', fontWeight: 500 }}
                        >
                          {t.title}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5 }}>
                          <ThumbUpAltOutlinedIcon sx={{ fontSize: 16 }} /> {t.like_count || 0}
                        </Box>
                      </TableCell>
                      <TableCell align="center">
                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5 }}>
                          <ChatBubbleOutlineIcon sx={{ fontSize: 16 }} /> {t.reply_count || 0}
                        </Box>
                      </TableCell>
                      <TableCell>{new Date(t.created_at).toLocaleDateString()}</TableCell>
                      <TableCell>
                        <IconButton size="small" onClick={() => navigate('/threads/' + t.id)}>
                          <VisibilityIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Box>
      )}

      {/* ═══════════════ MANAGE PLATFORM TAB (staff only) ═══════════════ */}
      {tabLabel === 'Manage Platform' && isStaff && (
        <Box>
          {/* Platform Stats */}
          {platformStats && (
            <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
              <Card sx={{ minWidth: 130 }}>
                <CardContent sx={{ textAlign: 'center', py: 1.5 }}>
                  <Typography variant="h4" color="primary">{platformStats.total_users}</Typography>
                  <Typography variant="body2" color="text.secondary">Total Users</Typography>
                </CardContent>
              </Card>
              {Object.entries(platformStats.roles || {}).map(([role, count]) => (
                <Card key={role} sx={{ minWidth: 100 }}>
                  <CardContent sx={{ textAlign: 'center', py: 1.5 }}>
                    <Typography variant="h4">{count}</Typography>
                    <Typography variant="body2" color="text.secondary">{role}s</Typography>
                  </CardContent>
                </Card>
              ))}
            </Box>
          )}

          {/* ── Users Section ── */}
          <Typography variant="h6" sx={{ mb: 1 }}>
            <PeopleIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
            Manage Users
          </Typography>
          <TextField
            label="Search users..."
            size="small"
            fullWidth
            value={userSearch}
            onChange={(e) => setUserSearch(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TableContainer component={Paper} sx={{ mb: 4 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell></TableCell>
                  <TableCell>Username</TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>Role</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Joined</TableCell>
                  {isAdmin && <TableCell>Actions</TableCell>}
                </TableRow>
              </TableHead>
              <TableBody>
                {platformUsers.map(u => (
                  <TableRow key={u.id} sx={{ opacity: u.is_active === false ? 0.6 : 1 }}>
                    <TableCell><UserAvatar user={u} size={28} /></TableCell>
                    <TableCell>{u.username}</TableCell>
                    <TableCell>{u.email}</TableCell>
                    <TableCell>
                      {isAdmin ? (
                        <Select
                          value={u.role}
                          size="small"
                          onChange={(e) => handleRoleChange(u.id, e.target.value)}
                          disabled={u.id === user.id}
                        >
                          <MenuItem value="member">member</MenuItem>
                          <MenuItem value="moderator">moderator</MenuItem>
                          <MenuItem value="admin">admin</MenuItem>
                        </Select>
                      ) : (
                        <Chip label={u.role} size="small" color={u.role === 'admin' ? 'error' : u.role === 'moderator' ? 'warning' : 'default'} />
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={u.is_active !== false ? 'Active' : 'Inactive'}
                        size="small"
                        color={u.is_active !== false ? 'success' : 'default'}
                        variant={u.is_active !== false ? 'filled' : 'outlined'}
                      />
                    </TableCell>
                    <TableCell>{new Date(u.created_at).toLocaleDateString()}</TableCell>
                    {isAdmin && (
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 0.5 }}>
                          <Button
                            size="small"
                            color={u.is_active !== false ? 'warning' : 'success'}
                            variant="outlined"
                            onClick={() => handleToggleStatus(u.id, u.username, u.is_active !== false)}
                            disabled={u.id === user.id}
                          >
                            {u.is_active !== false ? 'Deactivate' : 'Activate'}
                          </Button>
                          <Button
                            size="small"
                            color="error"
                            onClick={() => handleDeleteUser(u.id, u.username)}
                            disabled={u.id === user.id}
                          >
                            Delete
                          </Button>
                        </Box>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          {/* ── Threads Section ── */}
          <Typography variant="h6" sx={{ mb: 1 }}>
            <ForumIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
            Manage Threads
          </Typography>
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
                  <TableCell>Title</TableCell>
                  <TableCell>Author</TableCell>
                  <TableCell align="center">Likes</TableCell>
                  <TableCell align="center">Comments</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {platformThreads.map(t => (
                  <TableRow key={t.id}>
                    <TableCell>{t.title}</TableCell>
                    <TableCell>{t.author?.username || 'Unknown'}</TableCell>
                    <TableCell align="center">{t.like_count}</TableCell>
                    <TableCell align="center">{t.reply_count}</TableCell>
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

      {/* ═══════════════ REPORTS TAB (staff only) ═══════════════ */}
      {tabLabel === 'Reports' && isStaff && (
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
            <Typography variant="h6">
              <FlagIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
              Thread Reports ({reportsTotal})
            </Typography>
            <Select
              value={reportFilter}
              size="small"
              onChange={(e) => setReportFilter(e.target.value)}
              sx={{ minWidth: 140 }}
            >
              <MenuItem value="pending">Pending</MenuItem>
              <MenuItem value="reviewed">Reviewed</MenuItem>
              <MenuItem value="dismissed">Dismissed</MenuItem>
              <MenuItem value="">All</MenuItem>
            </Select>
          </Box>

          {reports.length === 0 ? (
            <Card sx={{ p: 3 }}>
              <Typography color="text.secondary">No {reportFilter || ''} reports found.</Typography>
            </Card>
          ) : (
            <TableContainer component={Paper}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Thread</TableCell>
                    <TableCell>Reported By</TableCell>
                    <TableCell>Reason</TableCell>
                    <TableCell>Details</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Date</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {reports.map(r => (
                    <TableRow key={r.id} hover>
                      <TableCell>
                        <Typography
                          component={Link}
                          to={'/threads/' + r.thread_id}
                          sx={{ textDecoration: 'none', color: 'primary.main', fontWeight: 500 }}
                        >
                          {r.thread_title || `Thread #${r.thread_id}`}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <UserAvatar user={r.reporter} size={24} />
                          {r.reporter?.username || 'Unknown'}
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={r.reason.replace('_', ' ')}
                          size="small"
                          color={r.reason === 'spam' ? 'default' : r.reason === 'harassment' ? 'error' : 'warning'}
                        />
                      </TableCell>
                      <TableCell sx={{ maxWidth: 200 }}>
                        <Typography variant="body2" noWrap>{r.details || '—'}</Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={r.status}
                          size="small"
                          color={r.status === 'pending' ? 'warning' : r.status === 'reviewed' ? 'success' : 'default'}
                        />
                      </TableCell>
                      <TableCell>{new Date(r.created_at).toLocaleDateString()}</TableCell>
                      <TableCell>
                        {r.status === 'pending' && (
                          <Box sx={{ display: 'flex', gap: 0.5 }}>
                            <Button size="small" variant="outlined" color="success" onClick={() => handleReportStatus(r.id, 'reviewed')}>
                              Reviewed
                            </Button>
                            <Button size="small" variant="outlined" color="inherit" onClick={() => handleReportStatus(r.id, 'dismissed')}>
                              Dismiss
                            </Button>
                          </Box>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Box>
      )}
    </Box>
  );
}

export default Dashboard;
