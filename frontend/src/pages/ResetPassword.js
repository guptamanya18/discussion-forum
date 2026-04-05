import { useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import api from '../api/api';
import { Container, TextField, Button, Typography, Box, Alert, Card, CardContent } from '@mui/material';
import ForumIcon from '@mui/icons-material/Forum';

function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') || '';
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const passwordValid = newPassword.length >= 5 && /[A-Za-z]/.test(newPassword) && /[0-9]/.test(newPassword);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');

    if (!token) {
      setError('Invalid or missing reset link. Please request a new one from the Forgot Password page.');
      return;
    }

    if (!passwordValid) {
      setError('Password must be at least 5 characters with at least one letter and one number');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    try {
      const res = await api.post('/auth/reset-password', { token, new_password: newPassword });
      setMessage(res.data.message);
      setTimeout(() => navigate('/login'), 2000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to reset password');
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
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5, textAlign: 'center' }}>Reset Password</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3, textAlign: 'center' }}>
              Enter your new password below
            </Typography>

            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            {message && <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert>}

            {!token && !error && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                No reset token found. Please use the link from your email, or <Link to="/forgot-password" style={{ color: '#7C4DFF', fontWeight: 600 }}>request a new one</Link>.
              </Alert>
            )}

            <Box component="form" onSubmit={handleSubmit}>
              <TextField label="New Password" type="password" fullWidth margin="normal" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required size="small" error={newPassword.length > 0 && !passwordValid} helperText={newPassword.length > 0 && !passwordValid ? 'Min 5 chars with at least one letter and one number' : ''} />
              <TextField label="Confirm Password" type="password" fullWidth margin="normal" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required size="small" />
              <Button type="submit" fullWidth variant="contained" disabled={!token} sx={{ mt: 2, mb: 1.5, borderRadius: '20px', py: 1 }}>Reset Password</Button>
              <Typography align="center" variant="body2" color="text.secondary">
                <Link to="/login" style={{ color: '#7C4DFF', textDecoration: 'none', fontWeight: 600 }}>Back to Login</Link>
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Box>
    </Container>
  );
}

export default ResetPassword;
