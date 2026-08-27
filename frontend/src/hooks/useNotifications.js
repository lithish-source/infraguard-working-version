import { useEffect, useState, useCallback } from 'react';
import { notificationService } from '../services';
import { useAuth } from '../context/AuthContext';

export function useNotifications() {
  const { user } = useAuth();
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchUnreadCount = useCallback(async () => {
    if (!user) return;
    try {
      const data = await notificationService.list(true);
      setUnreadCount(data.length);
    } catch {
      // ignore
    }
  }, [user]);

  const fetchAll = useCallback(async () => {
    if (!user) return [];
    setLoading(true);
    try {
      const data = await notificationService.list(false);
      setNotifications(data);
      setUnreadCount(data.filter((n) => !n.is_read).length);
      return data;
    } finally {
      setLoading(false);
    }
  }, [user]);

  const markRead = useCallback(async (id) => {
    await notificationService.markRead(id);
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
    setUnreadCount((c) => Math.max(0, c - 1));
  }, []);

  const markAllRead = useCallback(async () => {
    await notificationService.markAllRead();
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnreadCount(0);
  }, []);

  useEffect(() => {
    fetchUnreadCount();
    if (user) {
      const interval = setInterval(fetchUnreadCount, 30000);
      return () => clearInterval(interval);
    }
  }, [fetchUnreadCount, user]);

  return { unreadCount, notifications, loading, fetchAll, markRead, markAllRead, fetchUnreadCount };
}
