import { useEffect, useState, useCallback, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../api/api';
import { useAuth } from '../context/AuthContext';
import {
  Typography, Card, CardContent, Button, Box, Chip,
  TextField, InputAdornment, Pagination
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import ThumbUpAltOutlinedIcon from '@mui/icons-material/ThumbUpAltOutlined';
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutline';
import WhatshotIcon from '@mui/icons-material/Whatshot';
import NewReleasesIcon from '@mui/icons-material/NewReleases';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import AddIcon from '@mui/icons-material/Add';
import GroupsIcon from '@mui/icons-material/Groups';
import ForumIcon from '@mui/icons-material/Forum';
import { displayUsername } from '../utils/displayUser';
import { timeAgo } from '../utils/timeAgo';
import UserAvatar from '../components/UserAvatar';

const parseTags = (tags) => {
  if (!tags) return [];
  if (Array.isArray(tags)) return tags;
  return tags.split(',').map((t) => t.trim()).filter(Boolean);
};

function Home() {
  const PAGE_SIZE = 10;
  const [threads, setThreads] = useState([]);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [sortBy, setSortBy] = useState('newest');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const { broadcastEvent } = useAuth();
  const navigate = useNavigate();
  const debounceRef = useRef(null);

  // Debounce search input — only search after 400ms of no typing
  const handleSearchChange = useCallback((e) => {
    const value = e.target.value;
    setSearch(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(value.trim());
    }, 400);
  }, []);

  useEffect(() => {
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, []);

  useEffect(() => {
    fetchThreads();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch, sortBy, page]);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, sortBy]);

  useEffect(() => {
    if (!broadcastEvent) return;
    if (broadcastEvent.type === 'thread_like_update') {
      setThreads(prev => prev.map(t =>
        t.id === broadcastEvent.thread_id ? { ...t, like_count: broadcastEvent.like_count } : t
      ));
    }
    if (broadcastEvent.type === 'new_thread' && broadcastEvent.thread) {
      setThreads(prev => {
        if (prev.some(t => t.id === broadcastEvent.thread.id)) return prev;
        return [{ ...broadcastEvent.thread, like_count: 0, reply_count: 0 }, ...prev];
      });
    }
    if (broadcastEvent.type === 'thread_deleted') {
      setThreads(prev => prev.filter(t => t.id !== broadcastEvent.thread_id));
      setTotalPages(prev => Math.max(0, Math.ceil(((prev * PAGE_SIZE) - 1) / PAGE_SIZE)));
    }
    if (broadcastEvent.type === 'comment_deleted') {
      const count = broadcastEvent.deleted_count || 1;
      setThreads(prev => prev.map(t =>
        t.id === broadcastEvent.thread_id ? { ...t, reply_count: Math.max(0, (t.reply_count || 0) - count) } : t
      ));
    }
    if (broadcastEvent.type === 'new_comment_broadcast' && broadcastEvent.comment) {
      setThreads(prev => prev.map(t =>
        t.id === broadcastEvent.comment.thread_id ? { ...t, reply_count: (t.reply_count || 0) + 1 } : t
      ));
    }
    if (broadcastEvent.type === 'thread_edited' && broadcastEvent.thread_id) {
      setThreads(prev => prev.map(t => {
        if (t.id !== broadcastEvent.thread_id) return t;
        const updated = { ...t };
        if (broadcastEvent.title !== undefined) updated.title = broadcastEvent.title;
        if (broadcastEvent.description !== undefined) updated.description = broadcastEvent.description;
        if (broadcastEvent.tags !== undefined) updated.tags = broadcastEvent.tags;
        return updated;
      }));
    }
    if (broadcastEvent.type === 'avatar_update' && broadcastEvent.user_id) {
      setThreads(prev => prev.map(t => {
        if (t.author?.id === broadcastEvent.user_id) {
          return { ...t, author: { ...t.author, avatar: broadcastEvent.avatar } };
        }
        return t;
      }));
    }
  }, [broadcastEvent]);

  const fetchThreads = async () => {
    try {
      const params = { sort_by: sortBy, skip: (page - 1) * PAGE_SIZE, limit: PAGE_SIZE };
      if (debouncedSearch) params.search = debouncedSearch;
      const res = await api.get('/threads', { params });
      setThreads(res.data.items);
      setTotalPages(Math.ceil(res.data.total / PAGE_SIZE));
    } catch (err) {
      console.error('Failed to fetch threads');
    }
  };

  const sortOptions = [
    { value: 'newest', label: 'New', icon: <NewReleasesIcon sx={{ fontSize: 18 }} /> },
    { value: 'most_liked', label: 'Top', icon: <TrendingUpIcon sx={{ fontSize: 18 }} /> },
    { value: 'oldest', label: 'Old', icon: <WhatshotIcon sx={{ fontSize: 18 }} /> },
  ];

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', px: { xs: 1, sm: 2, md: 3 }, mt: 2.5 }}>
      <Box sx={{ display: 'flex', gap: 3, alignItems: 'flex-start' }}>
        {/* Main Content */}
        <Box sx={{ flex: 1, minWidth: 0 }}>
          {/* Search Bar */}
          <Card sx={{ mb: 2, overflow: 'visible' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, p: 1.5 }}>
              <UserAvatar user={{ username: '?' }} size={36} />
              <TextField
                placeholder="Search threads or create a post..."
                size="small"
                fullWidth
                value={search}
                onChange={handleSearchChange}
                InputProps={{
                  startAdornment: <InputAdornment position="start"><SearchIcon sx={{ fontSize: 20 }} /></InputAdornment>,
                  sx: { borderRadius: '20px', bgcolor: 'action.hover', fontSize: '0.875rem' },
                }}
              />
            </Box>
          </Card>

          {/* Sort Tabs */}
          <Card sx={{ mb: 2 }}>
            <Box sx={{ display: 'flex', gap: 0.5, p: 1.5 }}>
              {sortOptions.map((opt) => (
                <Button
                  key={opt.value}
                  size="small"
                  variant={sortBy === opt.value ? 'contained' : 'text'}
                  startIcon={opt.icon}
                  onClick={() => setSortBy(opt.value)}
                  sx={{
                    borderRadius: '20px',
                    px: 2,
                    fontSize: '0.8rem',
                    color: sortBy === opt.value ? '#fff' : 'text.secondary',
                    bgcolor: sortBy === opt.value ? 'primary.main' : 'transparent',
                    '&:hover': { bgcolor: sortBy === opt.value ? 'primary.dark' : 'action.hover' },
                  }}
                >
                  {opt.label}
                </Button>
              ))}
            </Box>
          </Card>

          {/* Thread List */}
          {threads.length === 0 && (
            <Card sx={{ p: 4, textAlign: 'center' }}>
              <Typography color="text.secondary">No threads found. Be the first to post!</Typography>
            </Card>
          )}

          {threads.map((thread) => {
            const tags = parseTags(thread.tags);
            return (
              <Card
                key={thread.id}
                sx={{
                  mb: 1.5,
                  cursor: 'pointer',
                  display: 'flex',
                  overflow: 'hidden',
                }}
                onClick={() => navigate('/threads/' + thread.id)}
              >
                {/* Vote Column */}
                <Box
                  sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'flex-start',
                    pt: 1.5,
                    px: 1,
                    minWidth: 48,
                    bgcolor: (theme) => theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.02)',
                  }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <ThumbUpAltOutlinedIcon sx={{ fontSize: 20, color: 'text.secondary', mb: 0.25 }} />
                  <Typography variant="body2" sx={{ fontWeight: 700, fontSize: '0.8rem' }}>
                    {thread.like_count || 0}
                  </Typography>
                </Box>

                {/* Content */}
                <CardContent sx={{ flex: 1, py: 1.5, px: 1.5, '&:last-child': { pb: 1.5 } }}>
                  {/* Meta */}
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.5 }}>
                    <UserAvatar user={thread.author} size={20} />
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                      {displayUsername(thread.author?.username)} · {timeAgo(thread.created_at)}
                      {thread.community_name && ` · in ${thread.community_name}`}
                    </Typography>
                  </Box>

                  {/* Title */}
                  <Typography
                    variant="subtitle1"
                    sx={{ fontWeight: 600, lineHeight: 1.3, mb: 0.5, fontSize: '1rem' }}
                  >
                    {thread.title}
                  </Typography>

                  {/* Description Preview */}
                  {thread.description && (
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{
                        mb: 0.75,
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                        lineClamp: 2,
                        overflow: 'hidden',
                        fontSize: '0.85rem',
                        lineHeight: 1.5,
                      }}
                    >
                      {thread.description}
                    </Typography>
                  )}

                  {/* Tags */}
                  {tags.length > 0 && (
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 0.75 }}>
                      {tags.map((tag) => (
                        <Chip
                          key={tag}
                          label={tag}
                          size="small"
                          variant="outlined"
                          color="primary"
                          sx={{ height: 22, fontSize: '0.7rem' }}
                        />
                      ))}
                    </Box>
                  )}

                  {/* Footer Actions */}
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Button
                      size="small"
                      startIcon={<ChatBubbleOutlineIcon sx={{ fontSize: 16 }} />}
                      sx={{
                        color: 'text.secondary',
                        fontSize: '0.75rem',
                        borderRadius: '12px',
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
                  </Box>
                </CardContent>
              </Card>
            );
          })}

          {/* Pagination */}
          {totalPages > 1 && (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3, mb: 3 }}>
              <Pagination count={totalPages} page={page} onChange={(e, v) => setPage(v)} color="primary" />
            </Box>
          )}
        </Box>

        {/* Sidebar */}
        <Box sx={{ width: 300, flexShrink: 0, display: { xs: 'none', md: 'block' } }}>
          {/* About Card */}
          <Card sx={{ mb: 2, overflow: 'hidden' }}>
            <Box sx={{ bgcolor: 'primary.main', px: 2, py: 3 }}>
              <Typography variant="subtitle1" sx={{ color: '#fff', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 1 }}>
                <ForumIcon /> Home
              </Typography>
            </Box>
            <CardContent sx={{ pt: 2 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2, lineHeight: 1.6 }}>
                Your personal ThreadHub frontpage. Come here to check in with your favorite communities.
              </Typography>
              <Button
                fullWidth
                variant="contained"
                component={Link}
                to="/threads/new"
                startIcon={<AddIcon />}
                sx={{ borderRadius: '20px', mb: 1 }}
              >
                Create Post
              </Button>
              <Button
                fullWidth
                variant="outlined"
                component={Link}
                to="/communities"
                startIcon={<GroupsIcon />}
                sx={{ borderRadius: '20px' }}
              >
                Browse Communities
              </Button>
            </CardContent>
          </Card>

          {/* Forum Rules */}
          <Card>
            <CardContent>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5 }}>
                Forum Rules
              </Typography>
              {['Be respectful to others', 'No spam or self-promotion', 'Use appropriate tags', 'Keep discussions on topic', 'Report rule violations'].map((rule, i) => (
                <Box key={i} sx={{ display: 'flex', gap: 1, mb: 1, alignItems: 'flex-start' }}>
                  <Typography variant="caption" sx={{ color: 'primary.main', fontWeight: 700, minWidth: 16 }}>
                    {i + 1}.
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {rule}
                  </Typography>
                </Box>
              ))}
            </CardContent>
          </Card>
        </Box>
      </Box>
    </Box>
  );
}

export default Home;