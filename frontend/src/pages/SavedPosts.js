/** This page shows all the discussion threads that the user has saved. */
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Typography, Card, CardContent, Button, Box, Chip, Snackbar, Alert,
} from '@mui/material';
import ThumbUpAltOutlinedIcon from '@mui/icons-material/ThumbUpAltOutlined';
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutline';
import BookmarkIcon from '@mui/icons-material/Bookmark';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import BookmarkBorderIcon from '@mui/icons-material/BookmarkBorder';
import { timeAgo } from '../utils/timeAgo';

const parseTags = (tags) => {
  if (!tags) return [];
  if (Array.isArray(tags)) return tags;
  return tags.split(',').map((t) => t.trim()).filter(Boolean);
};

function SavedPosts() {
  const navigate = useNavigate();
  const [savedPosts, setSavedPosts] = useState(() => {
    try { return JSON.parse(localStorage.getItem('savedPosts') || '[]'); } catch { return []; }
  });
  const [snackbar, setSnackbar] = useState({ open: false, message: '' });

  const removeSaved = (threadId, e) => {
    e.stopPropagation();
    setSavedPosts(prev => {
      const next = prev.filter(p => p.id !== threadId);
      localStorage.setItem('savedPosts', JSON.stringify(next));
      return next;
    });
    setSnackbar({ open: true, message: 'Post removed from saved' });
  };

  const clearAll = () => {
    setSavedPosts([]);
    localStorage.setItem('savedPosts', JSON.stringify([]));
    setSnackbar({ open: true, message: 'All saved posts cleared' });
  };

  return (
    <Box sx={{ maxWidth: 900, mx: 'auto', px: { xs: 1, sm: 2, md: 3 }, mt: 2.5 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>
          <BookmarkIcon sx={{ mr: 1, verticalAlign: 'middle', color: 'primary.main' }} />
          Saved Posts
        </Typography>
        {savedPosts.length > 0 && (
          <Button size="small" color="error" onClick={clearAll} startIcon={<DeleteOutlineIcon />}>
            Clear All
          </Button>
        )}
      </Box>

      {savedPosts.length === 0 ? (
        <Card sx={{ p: 4, textAlign: 'center' }}>
          <BookmarkBorderIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
          <Typography color="text.secondary" sx={{ mb: 1 }}>No saved posts yet.</Typography>
          <Typography variant="body2" color="text.secondary">
            Click the Save button on any post to bookmark it here.
          </Typography>
        </Card>
      ) : (
        savedPosts.slice().reverse().map((thread) => {
          const tags = parseTags(thread.tags);
          return (
            <Card
              key={thread.id}
              sx={{
                mb: 1,
                cursor: 'pointer',
                display: 'flex',
                overflow: 'hidden',
                borderRadius: 1,
              }}
              onClick={() => navigate('/threads/' + thread.id)}
            >
              {/* Like Column */}
              <Box
                sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'flex-start',
                  pt: 1.5,
                  px: 0.75,
                  minWidth: 44,
                  bgcolor: (theme) => theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.015)' : 'rgba(0,0,0,0.02)',
                }}
                onClick={(e) => e.stopPropagation()}
              >
                <ThumbUpAltOutlinedIcon sx={{ fontSize: 20, color: 'text.secondary' }} />
                <Typography variant="body2" sx={{ fontWeight: 700, fontSize: '0.85rem', mt: 0.5 }}>
                  {thread.like_count || 0}
                </Typography>
              </Box>

              {/* Content */}
              <CardContent sx={{ flex: 1, py: 1.25, px: 1.5, '&:last-child': { pb: 1.25 } }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5, flexWrap: 'wrap' }}>
                  {thread.community_name && (
                    <Typography variant="caption" sx={{ fontWeight: 700, fontSize: '0.75rem', color: 'text.primary' }}>
                      c/{thread.community_name}
                    </Typography>
                  )}
                  {thread.community_name && (
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>·</Typography>
                  )}
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                    Posted by u/{thread.author?.username || 'unknown'}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>·</Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                    {timeAgo(thread.created_at)}
                  </Typography>
                </Box>

                <Typography
                  variant="subtitle1"
                  sx={{ fontWeight: 600, lineHeight: 1.35, mb: 0.5, fontSize: '1rem', color: 'text.primary' }}
                >
                  {thread.title}
                </Typography>

                {tags.length > 0 && (
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 0.75 }}>
                    {tags.map((tag) => (
                      <Chip
                        key={tag}
                        label={tag}
                        size="small"
                        sx={{
                          height: 22,
                          fontSize: '0.7rem',
                          fontWeight: 500,
                          bgcolor: (theme) => theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
                          color: 'text.secondary',
                          border: 'none',
                          borderRadius: '4px',
                        }}
                      />
                    ))}
                  </Box>
                )}

                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.25, mt: 0.5 }}>
                  <Button
                    size="small"
                    startIcon={<ChatBubbleOutlineIcon sx={{ fontSize: 16 }} />}
                    sx={{
                      color: 'text.secondary',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      borderRadius: '4px',
                      px: 1,
                      minWidth: 'auto',
                      '&:hover': { bgcolor: 'action.hover' },
                    }}
                    onClick={(e) => e.stopPropagation()}
                    component={Link}
                    to={'/threads/' + thread.id}
                  >
                    {thread.reply_count || 0} Comments
                  </Button>
                  <Button
                    size="small"
                    startIcon={<BookmarkIcon sx={{ fontSize: 16 }} />}
                    sx={{
                      color: 'primary.main',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      borderRadius: '4px',
                      px: 1,
                      minWidth: 'auto',
                      '&:hover': { bgcolor: 'action.hover' },
                    }}
                    onClick={(e) => removeSaved(thread.id, e)}
                  >
                    Unsave
                  </Button>
                </Box>
              </CardContent>
            </Card>
          );
        })
      )}

      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity="success" onClose={() => setSnackbar({ ...snackbar, open: false })}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default SavedPosts;
