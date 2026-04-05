import { useEffect, useState, useRef } from 'react';
import api from '../api/api';
import { useAuth } from '../context/AuthContext';
import { Typography, Box, TextField, Button, Avatar, Alert, Card, CardContent, IconButton } from '@mui/material';
import PhotoCameraIcon from '@mui/icons-material/PhotoCamera';

function Profile() {
  const { refreshUser } = useAuth();
  const [profile, setProfile] = useState(null);
  const [name, setName] = useState('');
  const [bio, setBio] = useState('');
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const res = await api.get('/users/me/dashboard');
      const u = res.data.user;
      setProfile(u);
      setName(u.name || '');
      setBio(u.bio || '');
    } catch (err) {
      console.error('Failed to fetch profile');
    }
  };

  const handleAvatarUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post('/users/avatar/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setProfile(prev => ({ ...prev, avatar: res.data.avatar }));
      refreshUser();
      setSuccess('Avatar updated!');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to upload avatar');
    } finally {
      setUploading(false);
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      await api.put('/users/profile', { name, bio });
      setSuccess('Profile updated!');
      fetchProfile();
      refreshUser();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update profile');
    }
  };

  if (!profile) return <Box sx={{ maxWidth: 600, mx: 'auto', px: { xs: 1, sm: 2, md: 3 }, mt: 4 }}><Typography>Loading...</Typography></Box>;

  return (
    <Box sx={{ maxWidth: 600, mx: 'auto', px: { xs: 1, sm: 2, md: 3 }, mt: 2.5 }}>
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
            <Box sx={{ position: 'relative', mr: 3 }}>
              <Avatar
                src={profile.avatar ? 'http://localhost:8000' + profile.avatar : ''}
                sx={{ width: 80, height: 80, bgcolor: 'primary.dark', fontSize: '2rem' }}
              >
                {profile.username?.charAt(0).toUpperCase()}
              </Avatar>
              <IconButton
                sx={{
                  position: 'absolute', bottom: -4, right: -4,
                  bgcolor: 'primary.main', color: '#fff', width: 28, height: 28,
                  '&:hover': { bgcolor: 'primary.dark' },
                }}
                size="small"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
              >
                <PhotoCameraIcon sx={{ fontSize: 16 }} />
              </IconButton>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/gif,image/webp"
                hidden
                onChange={handleAvatarUpload}
              />
            </Box>
            <Box>
              <Typography variant="h5">{profile.name || profile.username}</Typography>
              <Typography variant="body2" color="text.secondary">@{profile.username} | {profile.email}</Typography>
              <Typography variant="body2" color="text.secondary">
                Role: {profile.role} | Joined: {new Date(profile.created_at).toLocaleDateString()}
              </Typography>
            </Box>
          </Box>

          {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          <Box component="form" onSubmit={handleUpdate}>
            <TextField
              label="Display Name"
              fullWidth
              margin="normal"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your display name"
            />
            <TextField
              label="Bio"
              fullWidth
              margin="normal"
              multiline
              rows={3}
              value={bio}
              onChange={(e) => setBio(e.target.value)}
            />
            <Button type="submit" fullWidth variant="contained" sx={{ mt: 2, borderRadius: '20px', py: 1 }}>
              Update Profile
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}

export default Profile;
