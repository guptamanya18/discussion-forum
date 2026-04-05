import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api/api';
import { useAuth } from '../context/AuthContext';
import {
  Typography, Box, Card, CardContent, Button, TextField, Chip, Divider,
  IconButton, Dialog, DialogTitle, DialogContent, DialogActions, Snackbar, Alert,
  FormControl, InputLabel, Select, MenuItem
} from '@mui/material';
import ThumbUpIcon from '@mui/icons-material/ThumbUp';
import ThumbUpOutlinedIcon from '@mui/icons-material/ThumbUpOutlined';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutline';
import ReplyIcon from '@mui/icons-material/Reply';
import FlagIcon from '@mui/icons-material/Flag';
import { displayUsername } from '../utils/displayUser';
import { timeAgo } from '../utils/timeAgo';
import UserAvatar from '../components/UserAvatar';
import ConfirmDialog from '../components/ConfirmDialog';

function Comment({ comment, onReply, onLike, onEdit, onDelete, currentUser, depth = 0 }) {
  const [replyText, setReplyText] = useState('');
  const [showReply, setShowReply] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(comment.content);

  const isOwner = currentUser && comment.author?.id === currentUser.id;
  const isStaff = currentUser && (currentUser.role === 'admin' || currentUser.role === 'moderator');

  const handleReply = () => {
    if (replyText.trim()) {
      onReply(comment.id, replyText);
      setReplyText('');
      setShowReply(false);
    }
  };

  const handleEdit = () => {
    if (editText.trim()) {
      onEdit(comment.id, editText);
      setEditing(false);
    }
  };

  return (
    <Box sx={{ ml: depth > 0 ? { xs: 2, sm: 3 } : 0, mt: depth === 0 ? 1.5 : 0.5 }}>
      <Box sx={{ display: 'flex', gap: 1 }}>
        {/* Thread line */}
        {depth > 0 && (
          <Box sx={{ width: 2, bgcolor: 'divider', borderRadius: 1, flexShrink: 0, ml: -1, mr: 0 }} />
        )}

        <Box sx={{ flex: 1 }}>
          {/* Comment Header */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.5 }}>
            <UserAvatar user={comment.author} size={22} />
            <Typography variant="caption" sx={{ fontWeight: 600, fontSize: '0.8rem' }}>
              {displayUsername(comment.author?.username)}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              · {timeAgo(comment.created_at)}
            </Typography>
          </Box>

          {/* Content */}
          {editing ? (
            <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
              <TextField size="small" fullWidth value={editText} onChange={(e) => setEditText(e.target.value)} />
              <Button variant="contained" size="small" onClick={handleEdit}>Save</Button>
              <Button size="small" onClick={() => { setEditing(false); setEditText(comment.content); }}>Cancel</Button>
            </Box>
          ) : (
            <Typography variant="body2" sx={{ mb: 0.5, lineHeight: 1.6, fontSize: '0.875rem' }}>
              {comment.content}
            </Typography>
          )}

          {/* Action Buttons */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.25, mb: 0.5 }}>
            <Button
              size="small"
              startIcon={comment.liked_by_me ? <ThumbUpIcon sx={{ fontSize: 14 }} /> : <ThumbUpOutlinedIcon sx={{ fontSize: 14 }} />}
              onClick={() => onLike(comment.id)}
              sx={{
                fontSize: '0.72rem',
                color: comment.liked_by_me ? 'primary.main' : 'text.secondary',
                minWidth: 'auto',
                px: 0.75,
                borderRadius: '12px',
                '&:hover': { bgcolor: 'action.hover' },
              }}
            >
              {comment.like_count || 0}
            </Button>
            <Button
              size="small"
              startIcon={<ReplyIcon sx={{ fontSize: 14 }} />}
              onClick={() => setShowReply(!showReply)}
              sx={{
                fontSize: '0.72rem',
                color: 'text.secondary',
                minWidth: 'auto',
                px: 0.75,
                borderRadius: '12px',
                '&:hover': { bgcolor: 'action.hover' },
              }}
            >
              Reply{comment.reply_count > 0 ? ` (${comment.reply_count})` : ''}
            </Button>
            {isOwner && (
              <IconButton size="small" onClick={() => setEditing(!editing)} sx={{ p: 0.5 }}>
                <EditIcon sx={{ fontSize: 14 }} />
              </IconButton>
            )}
            {isStaff && (
              <IconButton size="small" color="error" onClick={() => onDelete(comment.id)} sx={{ p: 0.5 }}>
                <DeleteIcon sx={{ fontSize: 14 }} />
              </IconButton>
            )}
          </Box>

          {/* Reply Input */}
          {showReply && (
            <Box sx={{ display: 'flex', gap: 1, mb: 1.5, mt: 0.5 }}>
              <TextField
                size="small"
                fullWidth
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                placeholder="Write a reply..."
                sx={{ '& .MuiOutlinedInput-root': { borderRadius: '20px', fontSize: '0.85rem' } }}
              />
              <Button variant="contained" size="small" onClick={handleReply} sx={{ borderRadius: '20px', px: 2 }}>
                Reply
              </Button>
            </Box>
          )}

          {/* Nested Replies */}
          {comment.replies && comment.replies.map((reply) => (
            <Comment key={reply.id} comment={reply} onReply={onReply} onLike={onLike} onEdit={onEdit} onDelete={onDelete} currentUser={currentUser} depth={depth + 1} />
          ))}
        </Box>
      </Box>
    </Box>
  );
}

function ThreadDetail() {
const { id } = useParams();
const { token, user, broadcastEvent } = useAuth();
const navigate = useNavigate();
const [thread, setThread] = useState(null);
const [comments, setComments] = useState([]);
const [newComment, setNewComment] = useState('');
const [editOpen, setEditOpen] = useState(false);
const [editTitle, setEditTitle] = useState('');
const [editDescription, setEditDescription] = useState('');
const [confirmOpen, setConfirmOpen] = useState(false);
const [confirmData, setConfirmData] = useState({ title: '', message: '', onConfirm: null });
const [snack, setSnack] = useState({ open: false, message: '', severity: 'error' });
const [reportOpen, setReportOpen] = useState(false);
const [reportReason, setReportReason] = useState('');
const [reportDetails, setReportDetails] = useState('');

const isThreadOwner = user && thread && thread.author?.id === user.id;
const isStaff = user && (user.role === 'admin' || user.role === 'moderator');

useEffect(() => {
fetchThread();
fetchComments();
// eslint-disable-next-line react-hooks/exhaustive-deps
}, [id]);

// Real-time like count updates via WebSocket broadcast
useEffect(() => {
if (!broadcastEvent) return;
if (broadcastEvent.type === 'thread_like_update' && String(broadcastEvent.thread_id) === String(id)) {
    setThread(prev => prev ? { ...prev, like_count: broadcastEvent.like_count } : prev);
}
if (broadcastEvent.type === 'comment_like_update' && String(broadcastEvent.thread_id) === String(id)) {
    const updateCommentLikes = (commentList) => commentList.map(c => {
        const updated = c.id === broadcastEvent.comment_id
            ? { ...c, like_count: broadcastEvent.like_count }
            : c;
        if (updated.replies && updated.replies.length > 0) {
            updated.replies = updateCommentLikes(updated.replies);
        }
        return updated;
    });
    setComments(prev => updateCommentLikes(prev));
}
// Thread deleted — redirect to home
if (broadcastEvent.type === 'thread_deleted' && String(broadcastEvent.thread_id) === String(id)) {
    navigate('/');
    return;
}
// Comment deleted — remove from comment tree
if (broadcastEvent.type === 'comment_deleted' && String(broadcastEvent.thread_id) === String(id)) {
    const deletedCount = broadcastEvent.deleted_count || 1;
    const removeComment = (list) => list
        .filter(c => c.id !== broadcastEvent.comment_id)
        .map(c => c.replies ? { ...c, replies: removeComment(c.replies) } : c);
    setComments(prev => removeComment(prev));
    // Decrement thread reply_count by total deleted (parent + descendants)
    setThread(prev => prev ? { ...prev, reply_count: Math.max(0, (prev.reply_count || 0) - deletedCount) } : prev);
}
// New comment posted — add to comment tree in real-time
if (broadcastEvent.type === 'new_comment_broadcast' && broadcastEvent.comment) {
    const newComment = broadcastEvent.comment;
    if (String(newComment.thread_id) === String(id)) {
        setComments(prev => {
            // Check if comment already exists (we posted it ourselves)
            const exists = (list) => list.some(c => c.id === newComment.id) || list.some(c => c.replies && exists(c.replies));
            if (exists(prev)) return prev;
            // Top-level comment — prepend
            if (!newComment.parent_comment_id) {
                return [newComment, ...prev];
            }
            // Nested reply — insert into parent's replies
            const addReply = (list) => list.map(c => {
                if (c.id === newComment.parent_comment_id) {
                    return { ...c, replies: [...(c.replies || []), newComment], reply_count: (c.reply_count || 0) + 1 };
                }
                if (c.replies && c.replies.length > 0) {
                    return { ...c, replies: addReply(c.replies) };
                }
                return c;
            });
            return addReply(prev);
        });
        // Update thread reply count
        setThread(prev => prev ? { ...prev, reply_count: (prev.reply_count || 0) + 1 } : prev);
    }
}
// Thread edited — update title/description/tags in real-time
if (broadcastEvent.type === 'thread_edited' && String(broadcastEvent.thread_id) === String(id)) {
    setThread(prev => {
        if (!prev) return prev;
        const updated = { ...prev };
        if (broadcastEvent.title !== undefined) updated.title = broadcastEvent.title;
        if (broadcastEvent.description !== undefined) updated.description = broadcastEvent.description;
        if (broadcastEvent.tags !== undefined) updated.tags = broadcastEvent.tags;
        return updated;
    });
}
// Comment edited — update content in real-time
if (broadcastEvent.type === 'comment_edited' && String(broadcastEvent.thread_id) === String(id)) {
    const updateContent = (list) => list.map(c => {
        const updated = c.id === broadcastEvent.comment_id ? { ...c, content: broadcastEvent.content } : c;
        if (updated.replies && updated.replies.length > 0) {
            return { ...updated, replies: updateContent(updated.replies) };
        }
        return updated;
    });
    setComments(prev => updateContent(prev));
}

// Global Avatar Update
if (broadcastEvent.type === 'avatar_update' && broadcastEvent.user_id) {
    if (thread?.author?.id === broadcastEvent.user_id) {
        setThread(prev => ({ ...prev, author: { ...prev.author, avatar: broadcastEvent.avatar } }));
    }
    const updateAuthorAvatar = (list) => list.map(c => {
        const updated = { ...c };
        if (updated.author?.id === broadcastEvent.user_id) {
            updated.author = { ...updated.author, avatar: broadcastEvent.avatar };
        }
        if (updated.replies && updated.replies.length > 0) {
            updated.replies = updateAuthorAvatar(updated.replies);
        }
        return updated;
    });
    setComments(prev => updateAuthorAvatar(prev));
}
}, [broadcastEvent, id, navigate, thread?.author?.id]);

const fetchThread = async () => {
    try {
const res = await api.get('/threads/' + id);
setThread(res.data);
} catch (err) {
console.error('Failed to fetch thread');
}
};

const fetchComments = async () => {
try {
const res = await api.get('/threads/' + id + '/comments');
setComments(res.data);
} catch (err) {
console.error('Failed to fetch comments');
}
};

const handleLikeThread = async () => {
try {
const res = await api.post('/threads/' + id + '/like');
setThread(prev => ({ ...prev, liked_by_me: res.data.liked, like_count: res.data.like_count }));
} catch (err) {
console.error('Failed to toggle thread like');
}
};
const handleAddComment = async () => {
if (!newComment.trim()) return;
try {
await api.post('/comments', { thread_id: parseInt(id), content: newComment });
setNewComment('');
fetchComments();
} catch (err) {
console.error('Failed to add comment');
}
};

const handleReply = async (parentCommentId, content) => {
try {
await api.post('/comments', { thread_id: parseInt(id), content, parent_comment_id: parentCommentId });
fetchComments();
} catch (err) {
console.error('Failed to reply');
}
};

const handleLikeComment = async (commentId) => {
try {
    const res = await api.post('/comments/' + commentId + '/like');
    const { liked, like_count } = res.data;
    const updateLike = (list) => list.map(c => {
        const updated = c.id === commentId ? { ...c, liked_by_me: liked, like_count } : c;
        if (updated.replies && updated.replies.length > 0) {
            return { ...updated, replies: updateLike(updated.replies) };
        }
        return updated;
    });
    setComments(prev => updateLike(prev));
} catch (err) {
console.error('Failed to toggle comment like');
}
};

const handleEditThread = async () => {
try {
await api.put('/threads/' + id, { title: editTitle, description: editDescription });
setEditOpen(false);
fetchThread();
} catch (err) {
console.error('Failed to edit thread');
}
};

const handleDeleteThread = () => {
  setConfirmData({
    title: 'Delete Thread',
    message: 'Are you sure you want to delete this thread?',
    onConfirm: async () => {
      setConfirmOpen(false);
      try {
        await api.delete('/threads/' + id);
        navigate('/');
      } catch (err) {
        setSnack({ open: true, message: err.response?.data?.detail || 'Failed to delete thread', severity: 'error' });
      }
    },
  });
  setConfirmOpen(true);
};

const handleEditComment = async (commentId, content) => {
try {
await api.put('/comments/' + commentId, { content });
fetchComments();
} catch (err) {
console.error('Failed to edit comment');
}
};

const handleDeleteComment = (commentId) => {
  setConfirmData({
    title: 'Delete Comment',
    message: 'Delete this comment and all its replies?',
    onConfirm: async () => {
      setConfirmOpen(false);
      try {
        await api.delete('/comments/' + commentId);
        fetchComments();
      } catch (err) {
        setSnack({ open: true, message: err.response?.data?.detail || 'Failed to delete comment', severity: 'error' });
      }
    },
  });
  setConfirmOpen(true);
};

const handleReportThread = async () => {
  if (!reportReason) return;
  try {
    await api.post('/threads/' + id + '/report', { reason: reportReason, details: reportDetails || undefined });
    setReportOpen(false);
    setReportReason('');
    setReportDetails('');
    setSnack({ open: true, message: 'Thread reported. Admins have been notified.', severity: 'success' });
  } catch (err) {
    const msg = err.response?.data?.detail || 'Failed to report thread';
    setSnack({ open: true, message: msg, severity: 'error' });
  }
};

if (!thread) return (
    <Box sx={{ maxWidth: 800, mx: 'auto', px: { xs: 1, sm: 2, md: 3 }, mt: 4 }}>
      <Typography>Loading...</Typography>
    </Box>
  );

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', px: { xs: 1, sm: 2, md: 3 }, mt: 2.5 }}>
      {/* Thread Card */}
      <Card sx={{ mb: 2, overflow: 'hidden' }}>
        <Box sx={{ display: 'flex' }}>
          {/* Vote Column */}
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              pt: 2,
              px: 1.5,
              minWidth: 52,
              bgcolor: (theme) => theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.02)',
            }}
          >
            <IconButton
              size="small"
              onClick={handleLikeThread}
              sx={{ color: thread.liked_by_me ? 'primary.main' : 'text.secondary' }}
            >
              {thread.liked_by_me ? <ThumbUpIcon sx={{ fontSize: 22 }} /> : <ThumbUpOutlinedIcon sx={{ fontSize: 22 }} />}
            </IconButton>
            <Typography variant="body2" sx={{ fontWeight: 700 }}>
              {thread.like_count || 0}
            </Typography>
          </Box>

          {/* Content */}
          <CardContent sx={{ flex: 1, pt: 2 }}>
            {/* Meta */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 1 }}>
              <UserAvatar user={thread.author} size={24} />
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.8rem' }}>
                Posted by {displayUsername(thread.author?.username)} · {timeAgo(thread.created_at)}
              </Typography>
              {(isThreadOwner || isStaff) && (
                <Box sx={{ ml: 'auto', display: 'flex' }}>
                  {(isThreadOwner || isStaff) && (
                    <IconButton size="small" onClick={() => { setEditTitle(thread.title); setEditDescription(thread.description || ''); setEditOpen(true); }}>
                      <EditIcon sx={{ fontSize: 18 }} />
                    </IconButton>
                  )}
                  <IconButton size="small" color="error" onClick={handleDeleteThread}>
                    <DeleteIcon sx={{ fontSize: 18 }} />
                  </IconButton>
                </Box>
              )}
            </Box>

            {/* Title */}
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 1, lineHeight: 1.3 }}>
              {thread.title}
            </Typography>

            {/* Tags */}
            {thread.tags && (
              <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 1.5 }}>
                {(Array.isArray(thread.tags) ? thread.tags : thread.tags.split(',')).map((tag) => (
                  <Chip key={tag} label={tag.trim()} size="small" variant="outlined" color="primary" sx={{ height: 22, fontSize: '0.72rem' }} />
                ))}
              </Box>
            )}

            {/* Description */}
            <Typography variant="body1" sx={{ mb: 2, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
              {thread.description}
            </Typography>

            {/* Footer */}
            <Divider sx={{ mb: 1 }} />
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Button
                size="small"
                startIcon={<ChatBubbleOutlineIcon sx={{ fontSize: 16 }} />}
                sx={{ color: 'text.secondary', fontSize: '0.8rem', borderRadius: '12px' }}
              >
                {thread.reply_count || 0} Comments
              </Button>
              {token && user && thread.author?.id !== user.id && user.role !== 'admin' && (
                <Button
                  size="small"
                  startIcon={<FlagIcon sx={{ fontSize: 16 }} />}
                  onClick={() => setReportOpen(true)}
                  sx={{ color: 'text.secondary', fontSize: '0.8rem', borderRadius: '12px', '&:hover': { color: 'error.main' } }}
                >
                  Report
                </Button>
              )}
            </Box>
          </CardContent>
        </Box>
      </Card>

      {/* Add Comment */}
      {token && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="body2" sx={{ mb: 1, fontWeight: 600, fontSize: '0.8rem' }}>
              Comment as {user?.username}
            </Typography>
            <TextField
              fullWidth
              multiline
              rows={3}
              size="small"
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              placeholder="What are your thoughts?"
              sx={{
                mb: 1,
                '& .MuiOutlinedInput-root': { borderRadius: 2, fontSize: '0.875rem' },
              }}
            />
            <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Button
                variant="contained"
                size="small"
                onClick={handleAddComment}
                disabled={!newComment.trim()}
                sx={{ borderRadius: '20px', px: 3 }}
              >
                Comment
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Comments Section */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          {comments.length === 0 && (
            <Typography color="text.secondary" sx={{ textAlign: 'center', py: 3 }}>
              No comments yet. Be the first to share your thoughts!
            </Typography>
          )}
          {comments.map((comment) => (
            <Comment key={comment.id} comment={comment} onReply={handleReply} onLike={handleLikeComment} onEdit={handleEditComment} onDelete={handleDeleteComment} currentUser={user} />
          ))}
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <Dialog open={editOpen} onClose={() => setEditOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Edit Thread</DialogTitle>
        <DialogContent>
          <TextField label="Title" fullWidth margin="normal" value={editTitle} onChange={(e) => setEditTitle(e.target.value)} />
          <TextField label="Description" fullWidth margin="normal" multiline rows={4} value={editDescription} onChange={(e) => setEditDescription(e.target.value)} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleEditThread}>Save</Button>
        </DialogActions>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        title={confirmData.title}
        message={confirmData.message}
        onConfirm={confirmData.onConfirm}
        onCancel={() => setConfirmOpen(false)}
        confirmText="Delete"
      />

      <Snackbar open={snack.open} autoHideDuration={4000} onClose={() => setSnack(s => ({ ...s, open: false }))} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert severity={snack.severity} onClose={() => setSnack(s => ({ ...s, open: false }))} variant="filled">{snack.message}</Alert>
      </Snackbar>

      {/* Report Dialog */}
      <Dialog open={reportOpen} onClose={() => setReportOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Report Thread</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Why are you reporting this thread? Admins will be notified and review the report.
          </Typography>
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Reason</InputLabel>
            <Select
              value={reportReason}
              label="Reason"
              onChange={(e) => setReportReason(e.target.value)}
            >
              <MenuItem value="spam">Spam</MenuItem>
              <MenuItem value="harassment">Harassment or Bullying</MenuItem>
              <MenuItem value="hate_speech">Hate Speech</MenuItem>
              <MenuItem value="misinformation">Misinformation</MenuItem>
              <MenuItem value="inappropriate">Inappropriate Content</MenuItem>
              <MenuItem value="off_topic">Off Topic</MenuItem>
              <MenuItem value="other">Other</MenuItem>
            </Select>
          </FormControl>
          <TextField
            label="Additional details (optional)"
            fullWidth
            multiline
            rows={3}
            value={reportDetails}
            onChange={(e) => setReportDetails(e.target.value)}
            placeholder="Provide any additional context..."
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setReportOpen(false); setReportReason(''); setReportDetails(''); }}>Cancel</Button>
          <Button variant="contained" color="error" onClick={handleReportThread} disabled={!reportReason}>Report</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default ThreadDetail;

