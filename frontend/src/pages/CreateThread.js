import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../api/api';
import { TextField, Button, Typography, Box, Alert, Chip, Select, MenuItem, InputLabel, FormControl } from '@mui/material';

function CreateThread() {
const [title, setTitle] = useState('');
const [description, setDescription] = useState('');
const [tagInput, setTagInput] = useState('');
const [tags, setTags] = useState([]);
const [communityId, setCommunityId] = useState('');
const [communities, setCommunities] = useState([]);
const [communityLocked, setCommunityLocked] = useState(false);
const [error, setError] = useState('');
const navigate = useNavigate();
const [searchParams] = useSearchParams();

useEffect(() => {
  const cid = searchParams.get('community_id');
  if (cid) {
    setCommunityId(parseInt(cid));
    setCommunityLocked(true);
    // Fetch just the selected community name
    api.get('/communities').then((res) => setCommunities(res.data.items)).catch(() => {});
  } else {
    api.get('/communities').then((res) => setCommunities(res.data.items)).catch(() => {});
  }
}, [searchParams]);

const addTags = (input, currentTags) => {
const newTags = input.split(',').map((t) => t.trim()).filter((t) => t && !currentTags.includes(t));
return [...currentTags, ...newTags];
};

const handleAddTag = (e) => {
if (e.key === 'Enter' && tagInput.trim()) {
e.preventDefault();
setTags(addTags(tagInput, tags));
setTagInput('');
}
};

const handleRemoveTag = (tagToRemove) => {
setTags(tags.filter((t) => t !== tagToRemove));
};

const handleSubmit = async (e) => {
e.preventDefault();
setError('');
try {
const finalTags = tagInput.trim() ? addTags(tagInput, tags) : tags;
const body = { title, description, tags: finalTags };
if (communityId) body.community_id = communityId;
const res = await api.post('/threads', body);
navigate('/threads/' + res.data.id);
} catch (err) {
setError(err.response?.data?.detail || 'Failed to create thread');
}
};
return (
<Box sx={{ maxWidth: 700, mx: 'auto', px: { xs: 1, sm: 2, md: 3 }, mt: 2.5 }}>
<Typography variant="h4" gutterBottom sx={{ fontWeight: 700 }}>Create a Post</Typography>
{error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
<Box component="form" onSubmit={handleSubmit}>
<TextField label="Title" fullWidth margin="normal" value={title} onChange={(e) => setTitle(e.target.value)} required />
<TextField label="Description" fullWidth margin="normal" multiline rows={4} value={description} onChange={(e) => setDescription(e.target.value)} required />
{communityLocked ? (
  <TextField
    label="Community"
    fullWidth
    margin="normal"
    value={communities.find(c => c.id === communityId)?.name || 'Loading...'}
    InputProps={{ readOnly: true }}
  />
) : (
<FormControl fullWidth margin="normal">
  <InputLabel>Community (optional)</InputLabel>
  <Select value={communityId} onChange={(e) => setCommunityId(e.target.value)} label="Community (optional)">
    <MenuItem value="">None</MenuItem>
    {communities.map((c) => (
      <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>
    ))}
  </Select>
</FormControl>
)}
<TextField label="Tags (press Enter or use commas)" fullWidth margin="normal" value={tagInput} onChange={(e) => setTagInput(e.target.value)} onKeyDown={handleAddTag} />
<Box sx={{ mb: 2 }}>
{tags.map((tag) => (
<Chip key={tag} label={tag} onDelete={() => handleRemoveTag(tag)} sx={{ mr: 0.5, mb: 0.5 }} />
))}
</Box>
<Button type="submit" fullWidth variant="contained" sx={{ borderRadius: '20px', py: 1 }}>Post</Button>
</Box>
</Box>
);
}

export default CreateThread;