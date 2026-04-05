import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../api/api';

// mui components for designing

import { Container, TextField, Button, Typography, Box, Alert, Card, CardContent } from '@mui/material';
import ForumIcon from '@mui/icons-material/Forum';

function Register() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();


  // frontend validation 

  const passwordValid = password.length >= 5 && /[A-Za-z]/.test(password) && /[0-9]/.test(password);
  const usernameValid = username.length >= 3 && /^[A-Za-z0-9_]+$/.test(username);

  // when signup is clicked

  const handleSubmit = async (e) => {
    e.preventDefault();  //prevent page refresh
    setError('');
    setSuccess('');

    if (!usernameValid) {
      setError('Username must be at least 3 characters and contain only letters, numbers, and underscores');
      return;
    }
    if (!passwordValid) {
      setError('Password must be at least 5 characters with at least one letter and one number');
      return;
    }

    try {

      // axios sent request through gateway

      await api.post('/users/register', { username, email, password });
      setSuccess('Account created! Redirecting to login...');
      setTimeout(() => navigate('/login'), 1500);

    } catch (err) {

      // if there are too many errors send a list
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        setError(detail.map(e => e.msg).join('. '));
      } else {
        setError(detail || 'Registration failed');
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
              Create Account
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2, textAlign: 'center' }}>
              Join the ThreadHub community
            </Typography>

            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}

            <Box component="form" onSubmit={handleSubmit}>
              <TextField
                label="Username"
                fullWidth
                margin="normal"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                size="small"
                error={username.length > 0 && !usernameValid}
                helperText={username.length > 0 && !usernameValid ? 'Min 3 chars, letters, numbers, underscores only' : ''}
              />
              <TextField
                label="Email"
                type="email"
                fullWidth
                margin="normal"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
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
                error={password.length > 0 && !passwordValid}
                helperText={password.length > 0 && !passwordValid ? 'Min 5 chars with at least one letter and one number' : ''}
              />
              <Button type="submit" fullWidth variant="contained" sx={{ mt: 2, mb: 1.5, borderRadius: '20px', py: 1 }}>
                Sign Up
              </Button>
              <Typography align="center" variant="body2" color="text.secondary">
                Already have an account?{' '}
                <Link to="/login" style={{ color: '#7C4DFF', textDecoration: 'none', fontWeight: 600 }}>
                  Log In
                </Link>
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Box>
    </Container>
  );
}

export default Register;
