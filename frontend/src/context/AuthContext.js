/** This file keeps track of whether you are logged in or not. */
import { createContext, useContext, useState, useEffect, useRef, useCallback } from "react";

import api, { setLoggedIn, setForceLogout } from '../api/api';


// creates global context to store authentication-related data like : isLoggedIn, user info, notifications, unreadcount
const AuthContext = createContext();

export function AuthProvider({children}) {
    // One-time cleanup: remove leftover localStorage token from old code
    useState(() => { localStorage.removeItem('token'); });

    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [initializing, setInitializing] = useState(true);
    const [user,setUser]=useState(null);
    const [notification, setNotification] = useState(null);
    const [unreadCount, setUnreadCount] = useState(0);
    const [broadcastEvent, setBroadcastEvent] = useState(null);

    const wsRef = useRef(null);
    const refreshUnreadCountRef = useRef(null);
    const userRef = useRef(null);


    // fetch unread notification count from backend run after every 15s 
    const refreshUnreadCount = useCallback(() => {
        if (isLoggedIn) {
            api.get('/notifications/unread-count')
                .then((res) => setUnreadCount(res.data.count))
                .catch(() => {});
        } else {
            setUnreadCount(0);
        }
    }, [isLoggedIn]);

    // Keep ref always pointing to latest refreshUnreadCount
    useEffect(() => {
        refreshUnreadCountRef.current = refreshUnreadCount;
    }, [refreshUnreadCount]);

    // Keep userRef always pointing to latest user
    useEffect(() => {
        userRef.current = user;
    }, [user]);

    useEffect(() => {
        refreshUnreadCount();
        if (isLoggedIn) {
            const interval = setInterval(refreshUnreadCount, 15000);
            return () => clearInterval(interval);
        }
    }, [isLoggedIn, refreshUnreadCount]);

    // when app starts -- it call auth/me -- check if cookie exist means user is logged in else logged out
    useEffect(() => {
        api.get('/auth/me')
            .then((res) => {
                setUser(res.data);   // if cookie found stores user data
                setIsLoggedIn(true);
                setLoggedIn(true);
            })
            .catch(() => {
                setUser(null);
                setIsLoggedIn(false);
                setLoggedIn(false);
            })
            .finally(() => setInitializing(false));
    }, []); // eslint-disable-line react-hooks/exhaustive-deps


    // used when role changes or profile updates  so it fetches user again 

    const fetchUser = useCallback(() => {
        if(isLoggedIn){
            api.get('/auth/me')
            .then((res)=>setUser(res.data))
            .catch(()=>{
                setIsLoggedIn(false);
                setLoggedIn(false);
                setUser(null);
            });
        } else {
            setUser(null);
        }
    }, [isLoggedIn]);


    // used when account deleted , token expired , 401 response
    
    const forceLogout = useCallback(() => {
        setLoggedIn(false);
        setIsLoggedIn(false);
        setUser(null);
    }, []);
    const forceLogoutRef = useRef(forceLogout);
    useEffect(() => { forceLogoutRef.current = forceLogout; }, [forceLogout]);

    const fetchUserRef = useRef(fetchUser);
    useEffect(() => { fetchUserRef.current = fetchUser; }, [fetchUser]);

    // Register force logout with axios 401 interceptor
    useEffect(() => {
        setForceLogout(forceLogout);
    }, [forceLogout]);



    // WebSocket for real-time notifications with auto-reconnect
    useEffect(() => {
        if (!isLoggedIn) {

            // close the existing websocket if logged out

            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
            return;
        }

        let reconnectTimer = null;
        let reconnectDelay = 1000;
        let stopped = false;

        function connect() {
            if (stopped) return;
            // Cookie is sent automatically by the browser
            const ws = new WebSocket('ws://localhost:8007/ws');
            wsRef.current = ws;

            ws.onopen = () => {
                reconnectDelay = 1000; // reset backoff on successful connect
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'ping') return; // ignore keepalive pings
                    // Force logout if account was deleted by admin
                    if (data.type === 'account_deleted' || data.type === 'account_deactivated') {
                        setNotification({ type: data.type, message: data.message + '. Logging out in 3s...' });
                        setTimeout(() => forceLogoutRef.current(), 3000);
                        return;
                    }
                    if (data.type === 'account_activated') {
                        setNotification(data);
                        return;
                    }
                    // Refresh user profile when role is changed by admin
                    if (data.type === 'role_change') {
                        fetchUserRef.current();
                    }
                    // Refresh user profile when avatar is updated
                    if (data.type === 'avatar_update' && userRef.current && data.user_id === userRef.current.id) {
                        fetchUserRef.current();
                    }
                    // Broadcast events go to broadcastEvent state
                    if (['thread_like_update', 'comment_like_update', 'new_thread', 'new_comment_broadcast', 'thread_deleted', 'comment_deleted', 'thread_edited', 'comment_edited', 'avatar_update'].includes(data.type)) {
                        setBroadcastEvent({...data, _ts: Date.now()});
                        return;
                    }
                    // Skip notification popup if current user is the actor (e.g. liker)
                    if (data.actor_id && userRef.current && data.actor_id === userRef.current.id) {
                        if (refreshUnreadCountRef.current) refreshUnreadCountRef.current();
                        return;
                    }
                    setNotification(data);
                    if (refreshUnreadCountRef.current) refreshUnreadCountRef.current();
                    // Clear notification after 6 seconds
                    setTimeout(() => setNotification(null), 6000);
                } catch (e) {}
            };

            ws.onerror = () => {};

            ws.onclose = () => {
                wsRef.current = null;
                if (!stopped) {
                    reconnectTimer = setTimeout(() => {
                        connect();
                        reconnectDelay = Math.min(reconnectDelay * 2, 30000);
                    }, reconnectDelay);
                }
            };
        }

        connect();

        return () => {
            stopped = true;
            if (reconnectTimer) clearTimeout(reconnectTimer);
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
        };
    }, [isLoggedIn]);

    const login = async () => {
        // Cookie is set by the gateway — fetch user data and update local state
        setLoggedIn(true);
        setIsLoggedIn(true);
        try {
            const res = await api.get('/auth/me');
            setUser(res.data);
        } catch (e) {}
    };

    const logout = async () =>{
        try {
            await api.post('/auth/logout');
        } catch (e) {
            // best-effort — clear local state regardless
        }
        setLoggedIn(false);
        setIsLoggedIn(false);
        setUser(null);
    };

    const refreshUser = () => {
        fetchUser();
    };

    const clearNotification = () => setNotification(null);

    if (initializing) return null; // avoid flash while checking cookie session

    return (
        <AuthContext.Provider value={{ token: isLoggedIn, user, login, logout, refreshUser, notification, clearNotification, unreadCount, refreshUnreadCount, broadcastEvent }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth(){
    return useContext(AuthContext);
}