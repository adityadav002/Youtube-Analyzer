import { Link } from 'react-router-dom';
import { formatDuration, formatRelativeTime, formatNumber } from '../../utils/formatters';
import { Clock, PlayCircle, Loader2 } from 'lucide-react';

import { API_BASE_URL } from '../../constants';

export default function VideoCard({ video }) {
  // Use a fallback thumbnail from YouTube if we haven't downloaded it, or if it's a stub
  const BACKEND_BASE_URL = API_BASE_URL.replace(/\/api\/?$/, '');
  const thumbnail = video.thumbnail_url?.startsWith('/') 
    ? `${BACKEND_BASE_URL}${video.thumbnail_url}` 
    : video.thumbnail_url || `https://i.ytimg.com/vi/${video.id}/hqdefault.jpg`;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-all group flex flex-col h-full">
      <Link to={`/videos/${video.id}`} className="relative aspect-video bg-gray-100 overflow-hidden block">
        <img 
          src={thumbnail} 
          alt={video.title} 
          className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
        />
        {video.duration > 0 && (
          <div className="absolute bottom-2 right-2 bg-black/80 text-white text-xs font-medium px-1.5 py-0.5 rounded flex items-center">
            {formatDuration(video.duration)}
          </div>
        )}
        {video.is_live && (
          <div className="absolute top-2 left-2 bg-red-600 text-white text-xs font-bold px-2 py-0.5 rounded flex items-center uppercase">
            Live
          </div>
        )}
        {!video.upload_date && !video.is_live && (
          <div className="absolute top-2 left-2 bg-yellow-500/90 text-white text-[10px] font-bold px-2 py-1 rounded-md flex items-center gap-1.5 shadow-sm animate-pulse">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>Enriching</span>
          </div>
        )}
        {video.is_short && (
          <div className="absolute top-2 right-2 bg-indigo-600/90 text-white p-1 rounded-full">
            <PlayCircle className="w-4 h-4" />
          </div>
        )}
      </Link>
      
      <div className="p-4 flex-grow flex flex-col">
        <Link to={`/videos/${video.id}`} className="block mb-2">
          <h3 className="font-semibold text-gray-900 leading-tight line-clamp-2 group-hover:text-indigo-600 transition-colors" title={video.title}>
            {video.title}
          </h3>
        </Link>
        
        <div className="mt-auto pt-2 flex items-center justify-between text-xs text-gray-500">
          <div className="flex flex-col gap-1">
            <span>{formatNumber(video.view_count)} views</span>
            <span>{video.upload_date ? formatRelativeTime(video.upload_date) : 'Unknown date'}</span>
          </div>
          {video.has_transcript && (
            <span className="bg-gray-100 text-gray-600 px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider">
              CC
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
