/** This is the first page people see, showing popular discussions. */
import { useEffect, useState, useMemo } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import api from '../api/api';
import { useAuth } from '../context/AuthContext';
import {
  Typography, Card, CardContent, Button, Box, Chip,
  Pagination, Avatar
} from '@mui/material';
import ThumbUpAltOutlinedIcon from '@mui/icons-material/ThumbUpAltOutlined';
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutline';
import WhatshotIcon from '@mui/icons-material/Whatshot';
import NewReleasesIcon from '@mui/icons-material/NewReleases';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import BoltIcon from '@mui/icons-material/Bolt';
import StarBorderIcon from '@mui/icons-material/StarBorder';
import BookmarkIcon from '@mui/icons-material/Bookmark';
import BookmarkBorderIcon from '@mui/icons-material/BookmarkBorder';
import BarChartIcon from '@mui/icons-material/BarChart';
import HistoryIcon from '@mui/icons-material/History';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { timeAgo } from '../utils/timeAgo';
import UserAvatar from './UserAvatar';

const parseTags = (tags) => {
  if (!tags) return [];
  if (Array.isArray(tags)) return tags;
  return tags.split(',').map((t) => t.trim()).filter(Boolean);
};

function Home() {
  const PAGE_SIZE = 10;
  const [threads, setThreads] = useState([]);
  const [sortBy, setSortBy] = useState('newest');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [trendingTags, setTrendingTags] = useState([]);
  const [topContributors, setTopContributors] = useState([]);
  const [forumStats, setForumStats] = useState(null);
  const [recentActive, setRecentActive] = useState([]);
  const { broadcastEvent } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Saved posts (localStorage)
  const [savedPosts, setSavedPosts] = useState(() => {
    try { return JSON.parse(localStorage.getItem('savedPosts') || '[]'); } catch { return []; }
  });

  const toggleSave = (thread, e) => {
    e.stopPropagation();
    setSavedPosts(prev => {
      const exists = prev.some(p => p.id === thread.id);
      const next = exists ? prev.filter(p => p.id !== thread.id) : [...prev, {
        id: thread.id,
        title: thread.title,
        author: thread.author,
        community_name: thread.community_name,
        like_count: thread.like_count,
        reply_count: thread.reply_count,
        tags: thread.tags,
        created_at: thread.created_at,
        savedAt: new Date().toISOString(),
      }];
      localStorage.setItem('savedPosts', JSON.stringify(next));
      return next;
    });
  };

  // Read search query from URL params (set by Navbar search)
  const debouncedSearch = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return params.get('search') || '';
  }, [location.search]);

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

  // Fetch sidebar data (trending tags + top contributors) from a larger thread set
  useEffect(() => {
    const fetchSidebarData = async () => {
      try {
        const res = await api.get('/threads', { params: { limit: 100, sort_by: 'most_liked' } });
        const allThreads = res.data.items || [];

        // Aggregate tags
        const tagMap = {};
        allThreads.forEach(t => {
          parseTags(t.tags).forEach(tag => {
            tagMap[tag] = (tagMap[tag] || 0) + 1;
          });
        });
        const sorted = Object.entries(tagMap)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 6)
          .map(([tag, count]) => ({ tag, count }));
        setTrendingTags(sorted);

        // Aggregate top contributors by total likes
        const authorMap = {};
        allThreads.forEach(t => {
          if (!t.author?.id) return;
          if (!authorMap[t.author.id]) {
            authorMap[t.author.id] = {
              id: t.author.id,
              username: t.author.username,
              name: t.author.name || t.author.username,
              avatar: t.author.avatar,
              rep: 0,
            };
          }
          authorMap[t.author.id].rep += (t.like_count || 0) + (t.reply_count || 0);
        });
        const topUsers = Object.values(authorMap)
          .sort((a, b) => b.rep - a.rep)
          .slice(0, 5);
        setTopContributors(topUsers);

        // Forum stats
        const totalLikes = allThreads.reduce((s, t) => s + (t.like_count || 0), 0);
        const totalComments = allThreads.reduce((s, t) => s + (t.reply_count || 0), 0);
        const uniqueAuthors = new Set(allThreads.map(t => t.author?.id).filter(Boolean)).size;
        const communities = new Set(allThreads.map(t => t.community_name).filter(Boolean)).size;
        setForumStats({ threads: res.data.total || allThreads.length, likes: totalLikes, comments: totalComments, authors: uniqueAuthors, communities });

        // Recent active threads (latest 3)
        const recentSorted = [...allThreads].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 3);
        setRecentActive(recentSorted);
      } catch (err) {
        console.error('Failed to fetch sidebar data');
      }
    };
    fetchSidebarData();
  }, []);

  const sortOptions = [
    { value: 'newest', label: 'New', icon: <NewReleasesIcon sx={{ fontSize: 18 }} /> },
    { value: 'most_liked', label: 'Top', icon: <TrendingUpIcon sx={{ fontSize: 18 }} /> },
    { value: 'oldest', label: 'Old', icon: <HistoryIcon sx={{ fontSize: 18 }} /> },
  ];

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', px: { xs: 1, sm: 2, md: 3 }, mt: 2.5 }}>
      <Box sx={{ display: 'flex', gap: 3, alignItems: 'flex-start' }}>
        {/* Main Content */}
        <Box sx={{ flex: 1, minWidth: 0 }}>
          {/* Sort Tabs */}
          <Card sx={{ mb: 2, borderRadius: 2 }}>
            <Box sx={{ display: 'flex', gap: 0.5, p: 1.5, alignItems: 'center' }}>
              {sortOptions.map((opt) => (
                <Button
                  key={opt.value}
                  size="small"
                  startIcon={opt.icon}
                  onClick={() => setSortBy(opt.value)}
                  sx={{
                    borderRadius: '20px',
                    px: 2,
                    fontSize: '0.85rem',
                    fontWeight: sortBy === opt.value ? 700 : 500,
                    color: sortBy === opt.value ? 'primary.main' : 'text.secondary',
                    bgcolor: sortBy === opt.value ? (theme) => theme.palette.mode === 'dark' ? 'rgba(255,69,0,0.1)' : 'rgba(255,69,0,0.06)' : 'transparent',
                    border: sortBy === opt.value ? '1px solid' : '1px solid transparent',
                    borderColor: sortBy === opt.value ? 'primary.main' : 'transparent',
                    '&:hover': {
                      bgcolor: sortBy === opt.value ? (theme) => theme.palette.mode === 'dark' ? 'rgba(255,69,0,0.15)' : 'rgba(255,69,0,0.1)' : 'action.hover',
                    },
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
                  <ThumbUpAltOutlinedIcon sx={{ fontSize: 20, color: 'text.secondary', cursor: 'pointer', '&:hover': { color: 'primary.main' } }} />
                  <Typography variant="body2" sx={{ fontWeight: 700, fontSize: '0.85rem', mt: 0.5 }}>
                    {thread.like_count || 0}
                  </Typography>
                </Box>

                {/* Content */}
                <CardContent sx={{ flex: 1, py: 1.25, px: 1.5, '&:last-child': { pb: 1.25 } }}>
                  {/* Meta Line */}
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5, flexWrap: 'wrap' }}>
                    <UserAvatar user={thread.author} size={20} />
                    <Typography variant="caption" sx={{ fontWeight: 600, fontSize: '0.75rem', color: 'text.primary' }}>
                      {thread.author?.username || 'unknown'}
                    </Typography>
                    {thread.community_name && (
                      <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>·</Typography>
                    )}
                    {thread.community_name && (
                      <Typography variant="caption" sx={{ fontWeight: 600, fontSize: '0.75rem', color: 'text.secondary' }}>
                        {thread.community_name}
                      </Typography>
                    )}
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>·</Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                      {timeAgo(thread.created_at)}
                    </Typography>
                  </Box>

                  {/* Title */}
                  <Typography
                    variant="subtitle1"
                    sx={{ fontWeight: 600, lineHeight: 1.35, mb: 0.5, fontSize: '1rem', color: 'text.primary' }}
                  >
                    {thread.title}
                  </Typography>

                  {/* Tags */}
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

                  {/* Footer Actions */}
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
                      startIcon={savedPosts.some(p => p.id === thread.id) ? <BookmarkIcon sx={{ fontSize: 16 }} /> : <BookmarkBorderIcon sx={{ fontSize: 16 }} />}
                      sx={{
                        color: savedPosts.some(p => p.id === thread.id) ? 'primary.main' : 'text.secondary',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        borderRadius: '4px',
                        px: 1,
                        minWidth: 'auto',
                        '&:hover': { bgcolor: 'action.hover' },
                      }}
                      onClick={(e) => toggleSave(thread, e)}
                    >
                      {savedPosts.some(p => p.id === thread.id) ? 'Saved' : 'Save'}
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
          {/* Trending Tags */}
          <Card sx={{ mb: 2, borderRadius: 2 }}>
            <CardContent>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
                <BoltIcon sx={{ color: '#FFA726' }} /> Trending Tags
              </Typography>
              <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap' }}>
                {trendingTags.length === 0 && (
                  <Typography variant="caption" color="text.secondary">No tags yet</Typography>
                )}
                {trendingTags.map(({ tag, count }) => (
                  <Chip
                    key={tag}
                    label={`#${tag} ${count >= 1000 ? (count / 1000).toFixed(1) + 'k' : count}`}
                    size="small"
                    onClick={() => navigate('/?search=' + encodeURIComponent(tag))}
                    sx={{
                      fontSize: '0.8rem',
                      fontWeight: 500,
                      borderRadius: '16px',
                      cursor: 'pointer',
                      bgcolor: (theme) => theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
                      '&:hover': {
                        bgcolor: (theme) => theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.08)',
                      },
                    }}
                  />
                ))}
              </Box>
            </CardContent>
          </Card>

          {/* Top Contributors */}
          <Card sx={{ mb: 2, borderRadius: 2 }}>
            <CardContent>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                <StarBorderIcon sx={{ color: '#FFA726' }} /> Top Contributors
              </Typography>
              {topContributors.length === 0 && (
                <Typography variant="caption" color="text.secondary">No data yet</Typography>
              )}
              {topContributors.map((contributor, index) => (
                <Box
                  key={contributor.id}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1.5,
                    py: 1.25,
                    borderBottom: index < topContributors.length - 1 ? '1px solid' : 'none',
                    borderColor: 'divider',
                  }}
                >
                  <Typography variant="body2" sx={{ fontWeight: 700, color: 'text.secondary', minWidth: 16, textAlign: 'center' }}>
                    {index + 1}
                  </Typography>
                  <Avatar
                    src={contributor.avatar ? `http://localhost:8000${contributor.avatar}` : undefined}
                    sx={{
                      width: 36,
                      height: 36,
                      bgcolor: ['#5C6BC0', '#42A5F5', '#26A69A', '#AB47BC', '#EF5350'][index % 5],
                      fontSize: '0.9rem',
                      fontWeight: 700,
                    }}
                  >
                    {contributor.name?.charAt(0).toUpperCase()}
                  </Avatar>
                  <Box sx={{ minWidth: 0 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.3 }} noWrap>
                      {contributor.name}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'primary.main', fontWeight: 600 }}>
                      {contributor.rep >= 1000 ? (contributor.rep / 1000).toFixed(1) + 'k' : contributor.rep.toLocaleString()} rep
                    </Typography>
                  </Box>
                </Box>
              ))}
            </CardContent>
          </Card>

          {/* Forum Stats */}
          {forumStats && (
            <Card sx={{ mb: 2, borderRadius: 2 }}>
              <CardContent>
                <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
                  <BarChartIcon sx={{ color: '#42A5F5' }} /> Forum Stats
                </Typography>
                <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5 }}>
                  {[
                    { label: 'Threads', value: forumStats.threads, color: '#FF4500' },
                    { label: 'Comments', value: forumStats.comments, color: '#42A5F5' },
                    { label: 'Likes', value: forumStats.likes, color: '#FFA726' },
                    { label: 'Authors', value: forumStats.authors, color: '#26A69A' },
                  ].map((stat) => (
                    <Box
                      key={stat.label}
                      sx={{
                        textAlign: 'center',
                        py: 1.25,
                        borderRadius: 1.5,
                        bgcolor: (theme) => theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
                      }}
                    >
                      <Typography variant="h6" sx={{ fontWeight: 800, color: stat.color, lineHeight: 1.2 }}>
                        {stat.value >= 1000 ? (stat.value / 1000).toFixed(1) + 'k' : stat.value}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500 }}>
                        {stat.label}
                      </Typography>
                    </Box>
                  ))}
                </Box>
                {forumStats.communities > 0 && (
                  <Box sx={{ mt: 1.5, textAlign: 'center', py: 0.75, borderRadius: 1.5, bgcolor: (theme) => theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)' }}>
                    <Typography variant="body2" sx={{ fontWeight: 700, color: '#AB47BC' }}>
                      {forumStats.communities}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500 }}>
                      Active Communities
                    </Typography>
                  </Box>
                )}
              </CardContent>
            </Card>
          )}

          {/* Recently Active */}
          {recentActive.length > 0 && (
            <Card sx={{ mb: 2, borderRadius: 2 }}>
              <CardContent>
                <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                  <HistoryIcon sx={{ color: '#26A69A' }} /> Recently Active
                </Typography>
                {recentActive.map((thread, i) => (
                  <Box
                    key={thread.id}
                    onClick={() => navigate('/threads/' + thread.id)}
                    sx={{
                      py: 1,
                      cursor: 'pointer',
                      borderBottom: i < recentActive.length - 1 ? '1px solid' : 'none',
                      borderColor: 'divider',
                      '&:hover': { bgcolor: 'action.hover', borderRadius: 1 },
                      px: 0.5,
                    }}
                  >
                    <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.3, mb: 0.25 }} noWrap>
                      {thread.title}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                      <Typography variant="caption" color="text.secondary">
                        u/{thread.author?.username || 'unknown'}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">·</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {timeAgo(thread.created_at)}
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'primary.main', ml: 'auto', fontWeight: 600 }}>
                        {thread.reply_count || 0} replies
                      </Typography>
                    </Box>
                  </Box>
                ))}
              </CardContent>
            </Card>
          )}

          {/* About ThreadHub */}
          <Card sx={{ borderRadius: 2 }}>
            <CardContent>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                <InfoOutlinedIcon sx={{ color: '#78909C' }} /> About ThreadHub
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.7, mb: 1.5 }}>
                A community-driven discussion platform where ideas meet conversations. Create threads, join communities, and connect with fellow members.
              </Typography>
              <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap' }}>
                {['Open Source', 'Real-time', 'Community-first'].map(badge => (
                  <Chip
                    key={badge}
                    label={badge}
                    size="small"
                    sx={{
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      borderRadius: '12px',
                      bgcolor: (theme) => theme.palette.mode === 'dark' ? 'rgba(255,69,0,0.1)' : 'rgba(255,69,0,0.06)',
                      color: 'primary.main',
                      border: '1px solid',
                      borderColor: (theme) => theme.palette.mode === 'dark' ? 'rgba(255,69,0,0.25)' : 'rgba(255,69,0,0.2)',
                    }}
                  />
                ))}
              </Box>
            </CardContent>
          </Card>
        </Box>
      </Box>
    </Box>
  );
}

export default Home;