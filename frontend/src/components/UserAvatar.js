import { Avatar } from '@mui/material';

const API_BASE = 'http://localhost:8000';

export function getAvatarUrl(avatar) {
  if (!avatar) return null;
  if (avatar.startsWith('http')) return avatar;
  return API_BASE + avatar;
}

function UserAvatar({ user, size = 28, sx = {} }) {
  const username = user?.username || '?';
  const src = getAvatarUrl(user?.avatar);

  return (
    <Avatar
      src={src || undefined}
      sx={{
        width: size,
        height: size,
        fontSize: size * 0.45,
        bgcolor: 'primary.dark',
        ...sx,
      }}
    >
      {username.charAt(0).toUpperCase()}
    </Avatar>
  );
}

export default UserAvatar;
