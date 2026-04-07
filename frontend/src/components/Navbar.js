import { useState } from 'react';
import {
  AppBar, Toolbar, Typography, Button, Box, Badge, Snackbar, Alert,
  IconButton, Slide, Menu, MenuItem, ListItemIcon, ListItemText,
  Divider, Switch, Tooltip, TextField, InputAdornment
} from '@mui/material';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useThemeMode } from '../context/ThemeContext';
import UserAvatar from '../pages/UserAvatar';
import NotificationsIcon from '@mui/icons-material/Notifications';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import ForumIcon from '@mui/icons-material/Forum';
import AddIcon from '@mui/icons-material/Add';
import PersonOutlineIcon from '@mui/icons-material/PersonOutline';
import DashboardIcon from '@mui/icons-material/Dashboard';
import LogoutIcon from '@mui/icons-material/Logout';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import LightModeIcon from '@mui/icons-material/LightMode';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import HomeIcon from '@mui/icons-material/Home';
import ExploreIcon from '@mui/icons-material/Explore';
import SearchIcon from '@mui/icons-material/Search';
import BookmarkIcon from '@mui/icons-material/Bookmark';

function SlideTransition(props) {
  return <Slide {...props} direction="left" />;
}

function Navbar() {
  const { token, user, logout, notification, clearNotification, unreadCount } = useAuth();
  const { mode, toggleTheme } = useThemeMode();
  const navigate = useNavigate();
  const [anchorEl, setAnchorEl] = useState(null);
  const menuOpen = Boolean(anchorEl);

  const handleLogout = () => {
    setAnchorEl(null);
    logout();
    navigate('/login');
  };

  const handleMenuNav = (path) => {
    setAnchorEl(null);
    navigate(path);
  };

  return (
    <>
      <AppBar position="sticky" elevation={0}>
        <Toolbar sx={{ gap: 1, px: { xs: 1, sm: 3 }, minHeight: { xs: 56 } }}>
          {/* Logo */}
          <Box
            sx={{ display: 'flex', alignItems: 'center', cursor: 'pointer', mr: 1 }}
            onClick={() => navigate(token ? '/' : '/login')}
          >
            <ForumIcon sx={{ mr: 0.75, color: 'primary.main', fontSize: 28 }} />
            <Typography
              variant="h6"
              sx={{
                fontWeight: 800,
                color: '#D7DADC',
                display: { xs: 'none', sm: 'block' },
                letterSpacing: '-0.5px',
                fontSize: '1.25rem',
              }}
            >
              thread<Box component="span" sx={{ color: 'primary.main' }}>Hub</Box>
            </Typography>
          </Box>

          {/* Nav Links */}
          {token && (
            <Box sx={{ display: 'flex', gap: 0.25, ml: 1 }}>
              <Tooltip title="Home">
                <Button
                  color="inherit"
                  component={Link}
                  to="/"
                  sx={{
                    minWidth: { xs: 40, md: 'auto' },
                    borderRadius: '20px',
                    px: { xs: 1, md: 2 },
                    '&:hover': { bgcolor: 'action.hover' },
                  }}
                >
                  <HomeIcon sx={{ fontSize: 20, mr: { xs: 0, md: 0.75 } }} />
                  <Box component="span" sx={{ display: { xs: 'none', md: 'inline' }, fontSize: '0.875rem' }}>Home</Box>
                </Button>
              </Tooltip>
              <Tooltip title="Explore Communities">
                <Button
                  color="inherit"
                  component={Link}
                  to="/communities"
                  sx={{
                    minWidth: { xs: 40, md: 'auto' },
                    borderRadius: '20px',
                    px: { xs: 1, md: 2 },
                    '&:hover': { bgcolor: 'action.hover' },
                  }}
                >
                  <ExploreIcon sx={{ fontSize: 20, mr: { xs: 0, md: 0.75 } }} />
                  <Box component="span" sx={{ display: { xs: 'none', md: 'inline' }, fontSize: '0.875rem' }}>Explore</Box>
                </Button>
              </Tooltip>
            </Box>
          )}

          {/* Center Search Bar */}
          {token && (
            <Box sx={{ flex: 1, maxWidth: 480, mx: { xs: 1, md: 3 } }}>
              <TextField
                placeholder="Search ThreadHub"
                size="small"
                fullWidth
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && e.target.value.trim()) {
                    navigate('/?search=' + encodeURIComponent(e.target.value.trim()));
                  }
                }}
                InputProps={{
                  startAdornment: <InputAdornment position="start"><SearchIcon sx={{ fontSize: 20, color: 'text.secondary' }} /></InputAdornment>,
                  sx: {
                    borderRadius: '20px',
                    bgcolor: (theme) => theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
                    fontSize: '0.875rem',
                    '& fieldset': { borderColor: 'transparent' },
                    '&:hover fieldset': { borderColor: 'rgba(255,255,255,0.12) !important' },
                    '&.Mui-focused fieldset': { borderColor: 'primary.main !important' },
                  },
                }}
              />
            </Box>
          )}

          {!token && <Box sx={{ flexGrow: 1 }} />}

          {/* Right Side */}
          {token ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, ml: 'auto' }}>
              {/* Create Post */}
              <Tooltip title="New Post">
                <Button
                  variant="contained"
                  size="small"
                  component={Link}
                  to="/threads/new"
                  startIcon={<AddIcon />}
                  sx={{
                    borderRadius: '20px',
                    px: 2.5,
                    fontSize: '0.825rem',
                    fontWeight: 700,
                    display: { xs: 'none', sm: 'flex' },
                  }}
                >
                  New Post
                </Button>
              </Tooltip>
              <Tooltip title="Create Post">
                <IconButton
                  color="primary"
                  component={Link}
                  to="/threads/new"
                  sx={{ display: { xs: 'flex', sm: 'none' } }}
                >
                  <AddIcon />
                </IconButton>
              </Tooltip>

              {/* Notifications */}
              <Tooltip title="Notifications">
                <IconButton color="inherit" component={Link} to="/notifications">
                  <Badge badgeContent={unreadCount} color="error" max={99}>
                    <NotificationsIcon />
                  </Badge>
                </IconButton>
              </Tooltip>

              {/* User Menu Button */}
              <Button
                onClick={(e) => setAnchorEl(e.currentTarget)}
                sx={{
                  ml: 0.5,
                  textTransform: 'none',
                  color: 'text.primary',
                  borderRadius: '20px',
                  border: '1px solid',
                  borderColor: 'divider',
                  px: 1.5,
                  py: 0.5,
                  minWidth: 'auto',
                  '&:hover': { borderColor: 'primary.main', bgcolor: 'action.hover' },
                }}
              >
                <UserAvatar user={user} size={26} />
                <Box sx={{ ml: 1, display: { xs: 'none', md: 'flex' }, flexDirection: 'column', alignItems: 'flex-start' }}>
                  <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.2, fontSize: '0.8rem' }}>
                    {user?.username || 'User'}
                  </Typography>
                </Box>
                <KeyboardArrowDownIcon sx={{ fontSize: 18, ml: 0.5, color: 'text.secondary' }} />
              </Button>

              {/* User Dropdown Menu */}
              <Menu
                anchorEl={anchorEl}
                open={menuOpen}
                onClose={() => setAnchorEl(null)}
                slotProps={{ paper: { sx: { width: 260, mt: 1, borderRadius: 2 } } }}
                transformOrigin={{ horizontal: 'right', vertical: 'top' }}
                anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
              >
                {/* User Info Header */}
                <Box sx={{ px: 2, py: 1.5 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <UserAvatar user={user} size={44} />
                    <Box sx={{ overflow: 'hidden' }}>
                      <Typography variant="body1" sx={{ fontWeight: 600, lineHeight: 1.3 }}>
                        {user?.name || user?.username}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" noWrap>
                        {user?.username} · {user?.role}
                      </Typography>
                    </Box>
                  </Box>
                </Box>
                <Divider />

                {/* Theme Toggle */}
                <MenuItem onClick={(e) => { e.stopPropagation(); toggleTheme(); }}>
                  <ListItemIcon>
                    {mode === 'dark' ? <LightModeIcon fontSize="small" /> : <DarkModeIcon fontSize="small" />}
                  </ListItemIcon>
                  <ListItemText>{mode === 'dark' ? 'Light Mode' : 'Dark Mode'}</ListItemText>
                  <Switch
                    size="small"
                    checked={mode === 'dark'}
                    onClick={(e) => { e.stopPropagation(); toggleTheme(); }}
                  />
                </MenuItem>

                <Divider sx={{ my: 0.5 }} />

                {/* Navigation Items */}
                <MenuItem onClick={() => handleMenuNav('/profile')}>
                  <ListItemIcon><PersonOutlineIcon fontSize="small" /></ListItemIcon>
                  <ListItemText>Edit Profile</ListItemText>
                </MenuItem>

                <MenuItem onClick={() => handleMenuNav('/dashboard')}>
                  <ListItemIcon><DashboardIcon fontSize="small" /></ListItemIcon>
                  <ListItemText>My Dashboard</ListItemText>
                </MenuItem>

                <MenuItem onClick={() => handleMenuNav('/saved')}>
                  <ListItemIcon><BookmarkIcon fontSize="small" /></ListItemIcon>
                  <ListItemText>Saved Posts</ListItemText>
                </MenuItem>

                <Divider sx={{ my: 0.5 }} />

                <MenuItem onClick={handleLogout} sx={{ color: 'error.main' }}>
                  <ListItemIcon><LogoutIcon fontSize="small" sx={{ color: 'error.main' }} /></ListItemIcon>
                  <ListItemText>Log Out</ListItemText>
                </MenuItem>
              </Menu>
            </Box>
          ) : (
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                variant="outlined"
                component={Link}
                to="/login"
                sx={{ borderRadius: '20px', px: 3, fontSize: '0.85rem' }}
              >
                Log In
              </Button>
              <Button
                variant="contained"
                component={Link}
                to="/register"
                sx={{ borderRadius: '20px', px: 3, fontSize: '0.85rem' }}
              >
                Sign Up
              </Button>
            </Box>
          )}
        </Toolbar>
      </AppBar>

      {/* Real-time notification popup */}
      <Snackbar
        open={!!notification}
        autoHideDuration={6000}
        onClose={clearNotification}
        anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
        TransitionComponent={SlideTransition}
        sx={{ mt: 7 }}
      >
        <Alert
          onClose={(e) => { e.stopPropagation(); clearNotification(); }}
          severity="info"
          variant="filled"
          icon={<NotificationsActiveIcon sx={{ animation: 'shake 0.5s ease-in-out' }} />}
          sx={{
            width: '100%',
            cursor: 'pointer',
            minWidth: 320,
            fontSize: '0.95rem',
            boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
            borderRadius: 2,
            '&:hover': { opacity: 0.9 },
            '@keyframes shake': {
              '0%, 100%': { transform: 'rotate(0deg)' },
              '25%': { transform: 'rotate(-15deg)' },
              '50%': { transform: 'rotate(15deg)' },
              '75%': { transform: 'rotate(-10deg)' },
            },
          }}
          onClick={() => { clearNotification(); navigate('/notifications'); }}
        >
          {notification?.message || 'New notification'}
        </Alert>
      </Snackbar>
    </>
  );
}

export default Navbar;