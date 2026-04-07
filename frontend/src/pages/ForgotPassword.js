/** This page helps users get back into their account if they forgot their password. */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/api';
import { Container, TextField, Button, Typography, Box, Alert, Card, CardContent } from '@mui/material';
import ForumIcon from '@mui/icons-material/Forum';
import MailOutlineIcon from '@mui/icons-material/MailOutline';

function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      await api.post('/auth/forgot-password', { email });
      setSent(true);
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong');
    }
  };

  return (
    <Container maxWidth="xs">
      <Box sx={{ mt: { xs: 4, sm: 8 }, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Card sx={{ width: '100%', overflow: 'hidden' }}>
          <Box sx={{ bgcolor: 'primary.main', py: 3, textAlign: 'center' }}>
            <ForumIcon sx={{ fontSize: 40, color: '#fff', mb: 0.5 }} />
            <Typography variant="h5" sx={{ color: '#fff', fontWeight: 700 }}>ThreadHub</Typography>
          </Box>
          <CardContent sx={{ px: 3, py: 3 }}>
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5, textAlign: 'center' }}>Forgot Password</Typography>

            {sent ? (
              <Box sx={{ textAlign: 'center', mt: 2 }}>
                <MailOutlineIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
                <Alert severity="success" sx={{ mb: 2 }}>
                  If an account with that email exists, a reset link has been sent. Check your inbox!
                </Alert>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  <strong>Dev tip:</strong> View the email at{' '}
                  <a href="http://localhost:8025" target="_blank" rel="noreferrer" style={{ color: '#FF4500', fontWeight: 600 }}>
                    localhost:8025
                  </a>{' '}
                  (Mailpit)
                </Typography>
                <Typography align="center" variant="body2" color="text.secondary">
                  <Link to="/login" style={{ color: '#FF4500', textDecoration: 'none', fontWeight: 600 }}>Back to Login</Link>
                </Typography>
              </Box>
            ) : (
              <>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3, textAlign: 'center' }}>
                  Enter your email and we'll send you a reset link
                </Typography>

                {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

                <Box component="form" onSubmit={handleSubmit}>
                  <TextField label="Email" type="email" fullWidth margin="normal" value={email} onChange={(e) => setEmail(e.target.value)} required size="small" />
                  <Button type="submit" fullWidth variant="contained" sx={{ mt: 2, mb: 1.5, borderRadius: '20px', py: 1 }}>Send Reset Link</Button>
                  <Typography align="center" variant="body2" color="text.secondary">
                    Remember your password? <Link to="/login" style={{ color: '#FF4500', textDecoration: 'none', fontWeight: 600 }}>Log In</Link>
                  </Typography>
                </Box>
              </>
            )}
          </CardContent>
        </Card>
      </Box>
    </Container>
  );
}

export default ForgotPassword;
