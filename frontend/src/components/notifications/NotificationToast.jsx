import { useEffect, useState } from 'react';
import { CheckCircle, Info, AlertTriangle, XCircle, X } from 'lucide-react';
import useNotificationStore from '../../stores/notificationStore';

const ICONS = {
  success: CheckCircle,
  info: Info,
  warning: AlertTriangle,
  error: XCircle,
};

const STYLES = {
  success: {
    bg: 'bg-emerald-50 border-emerald-300',
    icon: 'text-emerald-500',
    title: 'text-emerald-800',
    msg: 'text-emerald-700',
    bar: 'bg-emerald-400',
  },
  info: {
    bg: 'bg-blue-50 border-blue-300',
    icon: 'text-blue-500',
    title: 'text-blue-800',
    msg: 'text-blue-700',
    bar: 'bg-blue-400',
  },
  warning: {
    bg: 'bg-amber-50 border-amber-300',
    icon: 'text-amber-500',
    title: 'text-amber-800',
    msg: 'text-amber-700',
    bar: 'bg-amber-400',
  },
  error: {
    bg: 'bg-red-50 border-red-300',
    icon: 'text-red-500',
    title: 'text-red-800',
    msg: 'text-red-700',
    bar: 'bg-red-400',
  },
};

function Toast({ notification, onDismiss }) {
  const [visible, setVisible] = useState(false);
  const [exiting, setExiting] = useState(false);

  useEffect(() => {
    // Trigger enter animation
    const frame = requestAnimationFrame(() => setVisible(true));
    return () => cancelAnimationFrame(frame);
  }, []);

  const handleDismiss = () => {
    setExiting(true);
    setTimeout(() => onDismiss(notification.id), 300);
  };

  const style = STYLES[notification.type] || STYLES.info;
  const Icon = ICONS[notification.type] || ICONS.info;

  return (
    <div
      className={`
        relative overflow-hidden w-80 rounded-xl border shadow-lg backdrop-blur-sm
        transition-all duration-300 ease-out
        ${style.bg}
        ${visible && !exiting ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}
      `}
      role="alert"
    >
      <div className="flex items-start gap-3 p-4">
        <Icon className={`w-5 h-5 mt-0.5 flex-shrink-0 ${style.icon}`} />
        <div className="flex-1 min-w-0">
          {notification.title && (
            <p className={`text-sm font-semibold ${style.title}`}>{notification.title}</p>
          )}
          <p className={`text-sm ${notification.title ? 'mt-0.5' : ''} ${style.msg}`}>
            {notification.message}
          </p>
        </div>
        <button
          onClick={handleDismiss}
          className="flex-shrink-0 p-0.5 rounded-md hover:bg-black/5 transition-colors"
          aria-label="Dismiss"
        >
          <X className="w-4 h-4 text-gray-400" />
        </button>
      </div>
    </div>
  );
}

export default function NotificationToast() {
  const notifications = useNotificationStore((s) => s.notifications);
  const removeNotification = useNotificationStore((s) => s.removeNotification);

  if (notifications.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-[9999] flex flex-col-reverse gap-3 pointer-events-none">
      {notifications.slice(-5).map((n) => (
        <div key={n.id} className="pointer-events-auto">
          <Toast notification={n} onDismiss={removeNotification} />
        </div>
      ))}
    </div>
  );
}
