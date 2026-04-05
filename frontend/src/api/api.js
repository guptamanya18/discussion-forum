import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:8000',
    withCredentials: true,  // send/receive httpOnly cookies
});

let _onForceLogout = null;
let _logoutTriggered = false;
let _isLoggedIn = false;

export function setLoggedIn(value) {
    _isLoggedIn = value;
    if (value) _logoutTriggered = false;
}

export function setForceLogout(fn) {
    _onForceLogout = fn;
}

// If any API call returns 401, force logout (deleted/expired user)
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401 && _isLoggedIn && !_logoutTriggered) {
            _logoutTriggered = true;
            if (_onForceLogout) _onForceLogout();
        }
        return Promise.reject(error);
    }
);

export default api;