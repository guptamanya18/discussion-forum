export function displayUsername(username) {
  if (!username) return 'Unknown';
  if (username.startsWith('[deleted_')) return '[deleted user]';
  return username;
}
