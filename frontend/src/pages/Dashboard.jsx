import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Activity, Users, Video, Download, HardDrive,
  PlusCircle, Search, Clock, PlayCircle, Image as ImageIcon, Settings as SettingsIcon
} from 'lucide-react';
import { getDashboardStats } from '../api/dashboard';
import { formatNumber, formatDate } from '../utils/formatters';

export default function Dashboard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['dashboard_stats'],
    queryFn: getDashboardStats,
    refetchInterval: 5000 // Polling every 5 seconds to keep active jobs count live
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-8 text-center text-red-500 bg-red-50 rounded-xl border border-red-100 animate-in fade-in duration-300">
        Failed to load dashboard statistics. Please ensure the backend server is running.
      </div>
    );
  }

  const { stats, recent_activity } = data;

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">

      {/* Header */}
      <div>
        <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight flex items-center">
          <Activity className="w-8 h-8 mr-3 text-indigo-600" />
          Dashboard Overview
        </h1>
        <p className="text-gray-500 mt-2">Welcome back to your YouTube Analyzer command center.</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6">
        <StatCard
          title="Tracked Channels"
          value={formatNumber(stats.total_channels)}
          icon={<Users className="w-6 h-6 text-blue-600" />}
          bgColor="bg-blue-50"
          delayClass="delay-75"
        />
        <StatCard
          title="Total Videos"
          value={formatNumber(stats.total_videos)}
          icon={<Video className="w-6 h-6 text-emerald-600" />}
          bgColor="bg-emerald-50"
          delayClass="delay-100"
        />
        <StatCard
          title="Completed Downloads"
          value={formatNumber(stats.total_downloads)}
          icon={<Download className="w-6 h-6 text-purple-600" />}
          bgColor="bg-purple-50"
          delayClass="delay-150"
        />
        <StatCard
          title="Storage Used"
          value={formatBytes(stats.total_storage_bytes)}
          icon={<HardDrive className="w-6 h-6 text-orange-600" />}
          bgColor="bg-orange-50"
          delayClass="delay-200"
        />
        <StatCard
          title="Running Jobs"
          value={formatNumber(stats.active_jobs || 0)}
          icon={<Activity className={`w-6 h-6 text-indigo-600 ${stats.active_jobs > 0 ? 'animate-bounce text-indigo-700' : ''}`} />}
          bgColor="bg-indigo-50"
          delayClass="delay-300"
        />
      </div>

      {/* Quick Actions Command Panel */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200 animate-in fade-in slide-in-from-bottom-6 duration-700">
        <h2 className="text-lg font-bold text-gray-900 mb-5 flex items-center">
          <PlayCircle className="w-5 h-5 mr-2 text-indigo-600 animate-spin-slow" />
          Quick Command Panel
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          <QuickActionCard
            to="/channels"
            icon={<PlusCircle className="w-5 h-5 m-2.5" />}
            title="Add New Channel"
            desc="Crawl videos and track a creator."
            colorClass="text-blue-700 bg-blue-50/40 border-blue-100 hover:bg-blue-50/80 hover:border-blue-300 hover:shadow-lg hover:shadow-blue-50/30"
          />
          <QuickActionCard
            to="/downloader"
            icon={<Download className="w-5 h-5 m-2.5" />}
            title="Download Media"
            desc="Queue new video or audio files."
            colorClass="text-emerald-600 bg-emerald-50/40 border-emerald-100 hover:bg-emerald-50/80 hover:border-emerald-300 hover:shadow-lg hover:shadow-emerald-50/30"
          />
          <QuickActionCard
            to="/videos"
            icon={<Video className="w-5 h-5 m-2.5" />}
            title="Browse Library"
            desc="View crawled stubs and details."
            colorClass="text-purple-700 bg-purple-50/40 border-purple-100 hover:bg-purple-50/80 hover:border-purple-300 hover:shadow-lg hover:shadow-purple-50/30"
          />
          <QuickActionCard
            to="/search"
            icon={<Search className="w-5 h-5 m-2.5" />}
            title="Deep search"
            desc="Query transcripts and comments."
            colorClass="text-orange-600 bg-orange-50/40 border-orange-100 hover:bg-orange-50/80 hover:border-orange-300 hover:shadow-lg hover:shadow-orange-50/30"
          />
          <QuickActionCard
            to="/jobs"
            icon={<Activity className="w-5 h-5 m-2.5" />}
            title="Jobs Monitor"
            desc="Track crawls and scraper queues."
            badge={stats.active_jobs > 0 ? stats.active_jobs : null}
            colorClass="text-indigo-700 bg-indigo-50/40 border-indigo-100 hover:bg-indigo-50/80 hover:border-indigo-300 hover:shadow-lg hover:shadow-indigo-50/30"
          />
          <QuickActionCard
            to="/settings"
            icon={<SettingsIcon className="w-5 h-5 m-2.5" />}
            title="Platform Settings"
            desc="Configure yt-dlp and rate limits."
            colorClass="text-rose-700 bg-rose-50/40 border-rose-100 hover:bg-rose-50/80 hover:border-rose-300 hover:shadow-lg hover:shadow-rose-50/30"
          />
        </div>
      </div>

      {/* Activity Feeds */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

        {/* Recent Videos */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden animate-in fade-in slide-in-from-bottom-8 duration-700 delay-150">
          <div className="p-5 border-b border-gray-100 flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900 flex items-center">
              <Clock className="w-5 h-5 mr-2 text-indigo-600 animate-pulse" />
              Latest Videos
            </h2>
            <Link to="/videos" className="text-sm font-semibold text-indigo-600 hover:text-indigo-800 transition-colors">View All</Link>
          </div>
          <div className="divide-y divide-gray-100">
            {recent_activity.videos.length > 0 ? (
              recent_activity.videos.map((video, idx) => (
                <Link key={video.id} to={`/videos/${video.id}`} className="flex items-start p-4 hover:bg-gray-50/50 transition-colors group">
                  <div className="flex-shrink-0 w-32 aspect-video bg-gray-200 rounded-lg overflow-hidden relative border border-gray-150 shadow-sm transition-transform duration-300 group-hover:scale-95">
                    {video.thumbnail_url ? (
                      <img src={video.thumbnail_url} alt={video.title} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-gray-400">
                        <ImageIcon className="w-6 h-6" />
                      </div>
                    )}
                  </div>
                  <div className="ml-4 flex-1 min-w-0">
                    <p className="text-sm font-bold text-gray-900 line-clamp-2 transition-colors group-hover:text-indigo-600">{video.title}</p>
                    <div className="mt-2 flex items-center text-xs text-gray-500 font-medium">
                      <span>{formatNumber(video.view_count)} views</span>
                      <span className="mx-2">&bull;</span>
                      <span>{formatDate(video.upload_date)}</span>
                    </div>
                  </div>
                </Link>
              ))
            ) : (
              <div className="p-12 text-center text-gray-400">No videos parsed yet.</div>
            )}
          </div>
        </div>

        {/* Recent Channels */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden animate-in fade-in slide-in-from-bottom-8 duration-700 delay-200">
          <div className="p-5 border-b border-gray-100 flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900 flex items-center">
              <Users className="w-5 h-5 mr-2 text-indigo-600" />
              Recently Tracked Channels
            </h2>
            <Link to="/channels" className="text-sm font-semibold text-indigo-600 hover:text-indigo-800 transition-colors">View All</Link>
          </div>
          <div className="divide-y divide-gray-100">
            {recent_activity.channels.length > 0 ? (
              recent_activity.channels.map(channel => (
                <Link key={channel.id} to={`/channels/${channel.id}`} className="flex items-center p-4 hover:bg-gray-50/50 transition-colors group">
                  <div className="flex-shrink-0 w-12 h-12 bg-gray-200 rounded-full overflow-hidden border border-gray-200 shadow-inner transition-transform duration-300 group-hover:scale-95">
                    {channel.thumbnail_url ? (
                      <img src={channel.thumbnail_url} alt={channel.name} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-gray-400">
                        <Users className="w-5 h-5" />
                      </div>
                    )}
                  </div>
                  <div className="ml-4 flex-1 min-w-0">
                    <p className="text-sm font-bold text-gray-900 truncate transition-colors group-hover:text-indigo-600">{channel.name}</p>
                    <p className="text-xs text-gray-400 truncate mt-0.5 font-medium">{channel.custom_url || channel.id}</p>
                  </div>
                  <div className="text-right ml-4">
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-800 border border-gray-200 shadow-sm">
                      {formatNumber(channel.subscriber_count)} subs
                    </span>
                  </div>
                </Link>
              ))
            ) : (
              <div className="p-12 text-center text-gray-400">No channels tracked yet.</div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}

function StatCard({ title, value, icon, bgColor, delayClass }) {
  return (
    <div className={`bg-white p-5 rounded-2xl shadow-sm border border-gray-200 flex items-center transition-all duration-300 hover:scale-[1.02] hover:shadow-md hover:border-gray-300 animate-in fade-in slide-in-from-bottom-4 ${delayClass}`}>
      <div className={`p-3.5 rounded-xl ${bgColor} mr-4`}>
        {icon}
      </div>
      <div>
        <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">{title}</p>
        <p className="text-2xl font-extrabold text-gray-900 mt-1">{value}</p>
      </div>
    </div>
  );
}

function QuickActionCard({ to, icon, title, desc, colorClass, badge }) {
  return (
    <Link
      to={to}
      className={`flex items-start p-4.5 rounded-2xl border transition-all duration-300 hover:scale-[1.02] active:scale-[0.98] relative group ${colorClass}`}
    >
      <div className="mr-3.5 mt-0.5 transition-transform duration-300 group-hover:scale-110">
        {icon}
      </div>
      <div className="min-w-0 pr-2">
        <h3 className="font-bold text-sm tracking-tight">{title}</h3>
        <p className="text-xs opacity-70 font-medium leading-relaxed">{desc}</p>
      </div>
      {badge && (
        <span className="absolute -top-1.5 -right-1.5 inline-flex items-center justify-center px-2 py-0.75 text-xxs font-extrabold text-white bg-indigo-600 rounded-full shadow-md animate-pulse">
          {badge}
        </span>
      )}
    </Link>
  );
}

