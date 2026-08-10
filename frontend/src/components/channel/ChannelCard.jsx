import { Link } from 'react-router-dom';
import { Trash2, RefreshCw, BadgeCheck, Activity } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { deleteChannel, refreshChannel } from '../../api/channels';

export default function ChannelCard({ channel }) {
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: () => deleteChannel(channel.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] });
    }
  });

  const refreshMutation = useMutation({
    mutationFn: () => refreshChannel(channel.id),
    onSuccess: () => {
      // Typically we'd poll the job here, but invalidating is fine for simple refresh
      queryClient.invalidateQueries({ queryKey: ['channels'] });
    }
  });

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
      <div className="h-20 bg-gradient-to-r from-indigo-500 to-purple-600 relative">
        {channel.banner_url && (
          <img src={channel.banner_url} alt="Banner" className="w-full h-full object-cover opacity-80" />
        )}
      </div>
      <div className="px-5 pb-5 relative">
        <div className="flex justify-between items-start">
          <div className="relative -mt-10 mb-3">
            {channel.avatar_url ? (
              <img src={channel.avatar_url} alt={channel.display_name} className="w-20 h-20 rounded-full border-4 border-white bg-white object-cover shadow-sm" />
            ) : (
              <div className="w-20 h-20 rounded-full border-4 border-white bg-indigo-100 flex items-center justify-center text-indigo-500 font-bold text-xl shadow-sm">
                {channel.display_name.charAt(0)}
              </div>
            )}
          </div>
          <div className="mt-3 flex space-x-1">
            <button 
              onClick={() => refreshMutation.mutate()} 
              disabled={refreshMutation.isPending}
              className="p-1.5 text-gray-400 hover:text-indigo-600 rounded-lg hover:bg-indigo-50 transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`w-5 h-5 ${refreshMutation.isPending ? 'animate-spin' : ''}`} />
            </button>
            <button 
              onClick={() => {
                if(window.confirm('Delete this channel?')) deleteMutation.mutate();
              }} 
              disabled={deleteMutation.isPending}
              className="p-1.5 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition-colors"
              title="Delete"
            >
              <Trash2 className="w-5 h-5" />
            </button>
          </div>
        </div>
        
        <Link to={`/channels/${channel.id}`} className="block group">
          <div className="flex items-center space-x-1.5">
            <h3 className="font-bold text-lg text-gray-900 group-hover:text-indigo-600 transition-colors truncate">
              {channel.display_name}
            </h3>
            {channel.is_verified && <BadgeCheck className="w-5 h-5 text-indigo-500 shrink-0" />}
          </div>
          <p className="text-sm text-gray-500 truncate">
            {channel.handle || channel.id}
          </p>
        </Link>
        
        <div className="mt-4 flex items-center text-sm text-gray-600 gap-4">
          <div>
            <span className="font-semibold text-gray-900">{channel.subscriber_count?.toLocaleString() || '0'}</span> subs
          </div>
          <div>
            <span className="font-semibold text-gray-900">{channel.video_count?.toLocaleString() || '0'}</span> videos
          </div>
        </div>
        
        {channel.rss_monitoring && (
          <div className="mt-3 flex items-center text-xs text-emerald-600 bg-emerald-50 w-fit px-2 py-1 rounded-md font-medium">
            <Activity className="w-3.5 h-3.5 mr-1" /> Monitoring
          </div>
        )}
      </div>
    </div>
  );
}
