import { create } from 'zustand';

let nextId = 1;

const useNotificationStore = create((set, get) => ({
  notifications: [],

  /**
   * Push a notification toast.
   * @param {{ type: 'success'|'info'|'warning'|'error', title?: string, message: string, duration?: number }} n
   * @returns {number} notification id
   */
  addNotification: (n) => {
    const id = nextId++;
    const entry = {
      id,
      type: n.type || 'info',
      title: n.title || null,
      message: n.message,
      timestamp: Date.now(),
    };
    set((s) => ({ notifications: [...s.notifications, entry] }));

    const duration = n.duration ?? 5000;
    if (duration > 0) {
      setTimeout(() => get().removeNotification(id), duration);
    }
    return id;
  },

  removeNotification: (id) => {
    set((s) => ({
      notifications: s.notifications.filter((n) => n.id !== id),
    }));
  },

  clearAll: () => set({ notifications: [] }),
}));

export default useNotificationStore;
