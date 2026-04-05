import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api/api';
import { Container, TextField, Button, Typography, Box, Alert, Snackbar, Card, CardContent } from '@mui/material';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import ForumIcon from '@mui/icons-material/Forum';

function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [notifPopup, setNotifPopup] = useState(null);
  const { login } = useAuth();
  const navigate = useNavigate();


  // when user clicks login

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    try {
      await api.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      await login(); // cookie is set by the gateway, this fetches user data

      // Check for unread notifications
      try {
        const notifRes = await api.get('/notifications/unread-count');
        const count = notifRes.data.count;
        if (count > 0) {
          setNotifPopup(count);
          setTimeout(() => navigate('/'), 3000);
          return;
        }
      } catch (_) {}  //ignore notification count

      navigate('/');  //redirect to home page
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        setError(detail.map(e => e.msg).join('. '));
      } else {
        setError(detail || 'Login failed');
      }
    }
  };

  return (
    <Container maxWidth="xs">
      <Box sx={{ mt: { xs: 4, sm: 8 }, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Card sx={{ width: '100%', overflow: 'hidden' }}>
          {/* Header Band */}
          <Box sx={{ bgcolor: 'primary.main', py: 3, textAlign: 'center' }}>
            <ForumIcon sx={{ fontSize: 40, color: '#fff', mb: 0.5 }} />
            <Typography variant="h5" sx={{ color: '#fff', fontWeight: 700 }}>
              ThreadHub
            </Typography>
          </Box>

          <CardContent sx={{ px: 3, py: 3 }}>
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5, textAlign: 'center' }}>
              Welcome Back
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3, textAlign: 'center' }}>
              Sign in to continue to ThreadHub
            </Typography>

            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

            <Box component="form" onSubmit={handleSubmit}>
              <TextField
                label="Username"
                fullWidth
                margin="normal"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                size="small"
              />
              <TextField
                label="Password"
                type="password"
                fullWidth
                margin="normal"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                size="small"
              />
              <Button type="submit" fullWidth variant="contained" sx={{ mt: 2, mb: 1.5, borderRadius: '20px', py: 1 }}>
                Log In
              </Button>
              <Typography align="right" sx={{ mb: 1 }}>
                <Link to="/forgot-password" style={{ color: 'inherit', textDecoration: 'none', fontSize: '0.8rem', opacity: 0.7 }}>
                  Forgot Password?
                </Link>
              </Typography>
              <Typography align="center" variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                New to ThreadHub?{' '}
                <Link to="/register" style={{ color: '#7C4DFF', textDecoration: 'none', fontWeight: 600 }}>
                  Sign Up
                </Link>
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Box>

      <Snackbar
        open={!!notifPopup}
        autoHideDuration={3000}
        onClose={() => { setNotifPopup(null); navigate('/'); }}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          onClose={() => { setNotifPopup(null); navigate('/'); }}
          severity="info"
          variant="filled"
          icon={<NotificationsActiveIcon />}
          sx={{ width: '100%', cursor: 'pointer' }}
          onClick={() => { setNotifPopup(null); navigate('/notifications'); }}
        >
          You have {notifPopup} unread notification{notifPopup > 1 ? 's' : ''}! Click to view.
        </Alert>
      </Snackbar>
    </Container>
  );
}

export default Login;
