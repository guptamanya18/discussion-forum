import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/api';
import { useAuth } from '../context/AuthContext';
import {
  Container, Typography, Box, Card, CardContent, CardActions, Button, Chip,
  Grid, List, ListItem, ListItemText, Divider
} from '@mui/material';
import UserAvatar from '../components/UserAvatar';
import ForumIcon from '@mui/icons-material/Forum';
import GroupsIcon from '@mui/icons-material/Groups';
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutline';
import NotificationsIcon from '@mui/icons-material/Notifications';
import AddIcon from '@mui/icons-material/Add';
import ThumbUpAltOutlinedIcon from '@mui/icons-material/ThumbUpAltOutlined';

function MemberDashboard() {
  const { user, unreadCount } = useAuth();
  const [dashboardData, setDashboardData] = useState(null);
  const [myThreads, setMyThreads] = useState([]);
  const [myCommunities, setMyCommunities] = useState([]);

  useEffect(() => {
    fetchDashboard();
    fetchMyThreads();
    fetchMyCommunities();
  }, []);

  const fetchDashboard = async () => {
    try {
      const res = await api.get('/users/me/dashboard');
      setDashboardData(res.data);
    } catch (err) {
      console.error('Failed to fetch dashboard');
    }
  };

  const fetchMyThreads = async () => {
    try {
      const res = await api.get('/threads', { params: { limit: 5 } });
      // Filter to only show threads by current user
      const mine = res.data.items.filter(t => t.author?.id === user?.id);
      setMyThreads(mine.slice(0, 5));
    } catch (err) {
      console.error('Failed to fetch threads');
    }
  };

  const fetchMyCommunities = async () => {
    try {
      const res = await api.get('/communities');
      setMyCommunities(res.data.items.slice(0, 5));
    } catch (err) {
      console.error('Failed to fetch communities');
    }
  };

  const profile = dashboardData?.user;

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', px: { xs: 1, sm: 2, md: 3 }, mt: 2.5 }}>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 700 }}>My Dashboard</Typography>

      {/* User Info Card */}
      {profile && (
        <Card sx={{ mb: 3, display: 'flex', alignItems: 'center', p: 2 }}>
          <UserAvatar user={profile} size={64} sx={{ mr: 2 }} />
          <Box sx={{ flex: 1 }}>
            <Typography variant="h5">{profile.name || profile.username}</Typography>
            <Typography variant="body2" color="text.secondary">{profile.email}</Typography>
            <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
              <Chip label={profile.role} size="small" color={profile.role === 'admin' ? 'error' : profile.role === 'moderator' ? 'warning' : 'primary'} />
              <Typography variant="caption" color="text.secondary" sx={{ alignSelf: 'center' }}>
                Joined {new Date(profile.created_at).toLocaleDateString()}
              </Typography>
            </Box>
            {profile.bio && <Typography variant="body2" sx={{ mt: 0.5 }}>{profile.bio}</Typography>}
          </Box>
          <Button component={Link} to="/profile" variant="outlined" size="small">Edit Profile</Button>
        </Card>
      )}

      {/* Quick Actions */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={6} sm={3}>
          <Card sx={{ textAlign: 'center', cursor: 'pointer' }} component={Link} to="/threads/new" style={{ textDecoration: 'none' }}>
            <CardContent>
              <AddIcon color="primary" sx={{ fontSize: 40 }} />
              <Typography variant="body2">New Thread</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Card sx={{ textAlign: 'center', cursor: 'pointer' }} component={Link} to="/communities" style={{ textDecoration: 'none' }}>
            <CardContent>
              <GroupsIcon color="primary" sx={{ fontSize: 40 }} />
              <Typography variant="body2">Communities</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Card sx={{ textAlign: 'center', cursor: 'pointer' }} component={Link} to="/" style={{ textDecoration: 'none' }}>
            <CardContent>
              <ForumIcon color="primary" sx={{ fontSize: 40 }} />
              <Typography variant="body2">Browse Threads</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Card sx={{ textAlign: 'center', cursor: 'pointer' }} component={Link} to="/notifications" style={{ textDecoration: 'none' }}>
            <CardContent>
              <NotificationsIcon color={unreadCount > 0 ? 'error' : 'primary'} sx={{ fontSize: 40 }} />
              <Typography variant="body2">
                Notifications {unreadCount > 0 && `(${unreadCount})`}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* My Threads */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <ForumIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
                My Recent Threads
              </Typography>
              {myThreads.length === 0 ? (
                <Typography color="text.secondary">No threads yet. Create one!</Typography>
              ) : (
                <List dense>
                  {myThreads.map(t => (
                    <ListItem key={t.id} component={Link} to={'/threads/' + t.id} sx={{ textDecoration: 'none', color: 'inherit' }}>
                      <ListItemText
                        primary={t.title}
                        secondary={
                          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                            <ThumbUpAltOutlinedIcon sx={{ fontSize: 14 }} /> {t.like_count || 0}
                            <ChatBubbleOutlineIcon sx={{ fontSize: 14, ml: 1 }} /> {t.reply_count || 0}
                          </Box>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              )}
            </CardContent>
            <CardActions>
              <Button size="small" component={Link} to="/">View All Threads</Button>
            </CardActions>
          </Card>
        </Grid>

        {/* My Communities */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <GroupsIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
                Communities
              </Typography>
              {myCommunities.length === 0 ? (
                <Typography color="text.secondary">No communities yet.</Typography>
              ) : (
                <List dense>
                  {myCommunities.map(c => (
                    <ListItem key={c.id} component={Link} to={'/communities/' + c.slug} sx={{ textDecoration: 'none', color: 'inherit' }}>
                      <ListItemText
                        primary={c.name}
                        secondary={c.description?.substring(0, 60)}
                      />
                    </ListItem>
                  ))}
                </List>
              )}
            </CardContent>
            <CardActions>
              <Button size="small" component={Link} to="/communities">View All Communities</Button>
            </CardActions>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

export default MemberDashboard;
