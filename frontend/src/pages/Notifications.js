/** This page lists all the notifications for the logged-in user. */
import { useEffect, useState } from 'react';
import api from '../api/api';
import { useAuth } from '../context/AuthContext';
import {
  Typography, List, ListItem, ListItemText, ListItemIcon,
  Button, Box, Badge, Chip, Pagination
} from '@mui/material';
import NotificationsIcon from '@mui/icons-material/Notifications';
import DoneAllIcon from '@mui/icons-material/DoneAll';

function Notifications() {
  const PAGE_SIZE = 15;
  const [notifications, setNotifications] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const { notification, unreadCount, refreshUnreadCount } = useAuth();

  useEffect(() => {
    fetchNotifications();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  // Auto-refresh when a WebSocket notification arrives
  useEffect(() => {
    if (notification) {
      fetchNotifications();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notification]);

  const fetchNotifications = async () => {
    try {
      const params = { skip: (page - 1) * PAGE_SIZE, limit: PAGE_SIZE };
      const res = await api.get('/notifications', { params });
      setNotifications(res.data.items);
      setTotalPages(Math.ceil(res.data.total / PAGE_SIZE));
    } catch (err) {
      console.error('Failed to fetch notifications');
    }
  };

  const handleMarkRead = async (notifId) => {
    try {
      await api.put('/notifications/' + notifId + '/read');
      fetchNotifications();
      refreshUnreadCount();
    } catch (err) {
      console.error('Failed to mark as read');
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.put('/notifications/read-all');
      fetchNotifications();
      refreshUnreadCount();
    } catch (err) {
      console.error('Failed to mark all as read');
    }
  };

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', px: { xs: 1, sm: 2, md: 3 }, mt: 2.5 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="h4">Notifications</Typography>
          {unreadCount > 0 && (
            <Chip label={unreadCount + ' unread'} color="primary" size="small" />
          )}
        </Box>
        {notifications.length > 0 && (
          <Button startIcon={<DoneAllIcon />} onClick={handleMarkAllRead}>
            Mark All Read
          </Button>
        )}
      </Box>

      {notifications.length === 0 && (
        <Typography color="text.secondary">No notifications yet.</Typography>
      )}

      <List>
        {notifications.map((n) => (
          <ListItem
            key={n.id}
            sx={{
              bgcolor: n.is_read ? 'transparent' : 'action.hover',
              borderRadius: 1,
              mb: 1
            }}
            secondaryAction={
              !n.is_read && (
                <Button size="small" onClick={() => handleMarkRead(n.id)}>Mark Read</Button>
              )
            }
          >
            <ListItemIcon>
              <Badge color="primary" variant="dot" invisible={n.is_read}>
                <NotificationsIcon />
              </Badge>
            </ListItemIcon>
            <ListItemText
              primary={n.message}
              secondary={
                n.type + ' | ' + new Date(n.created_at).toLocaleString()
              }
            />
          </ListItem>
        ))}
      </List>

      {totalPages > 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3, mb: 3 }}>
          <Pagination count={totalPages} page={page} onChange={(e, v) => setPage(v)} color="primary" />
        </Box>
      )}
    </Box>
  );
}

export default Notifications;
