import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, Play } from 'lucide-react';
import { getVideos } from '../api/videos';
import VideoGrid from '../components/video/VideoGrid';

export default function Videos() {
  const [page, setPage] = useState(1);
  const perPage = 20;
  const [sortBy, setSortBy] = useState('upload_date');
  const [sortOrder, setSortOrder] = useState('desc');
  const [contentType, setContentType] = useState('all');

  const { data, isLoading, isError } = useQuery({
    queryKey: ['global_videos', page, sortBy, sortOrder, contentType],
    queryFn: () => {
      const params = {
        page,
        per_page: perPage,
        sort_by: sortBy,
        sort_order: sortOrder,
      };
      if (contentType === 'normal') {
        params.is_short = false;
        params.is_live = false;
      } else if (contentType === 'shorts') {
        params.is_short = true;
        params.is_live = false;
      } else if (contentType === 'live') {
        params.is_short = false;
        params.is_live = true;
      }
      return getVideos(params);
    }
  });

  const handleSortChange = (newSortBy) => {
    if (sortBy === newSortBy) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(newSortBy);
      setSortOrder('desc');
    }
    setPage(1);
  };

  const SortButton = ({ label, field }) => {
    const isActive = sortBy === field;
    return (
      <button
        onClick={() => handleSortChange(field)}
        className={`flex items-center px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
          isActive 
            ? 'bg-indigo-100 text-indigo-700' 
            : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-200'
        }`}
      >
        {label}
        {isActive && (
          sortOrder === 'desc' ? <ArrowDown className="w-4 h-4 ml-1.5" /> : <ArrowUp className="w-4 h-4 ml-1.5" />
        )}
      </button>
    );
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            <Play className="w-6 h-6 mr-2 text-indigo-600" />
            Global Video Library
          </h1>
          <p className="text-gray-500 mt-1">Browse, sort, and filter all videos across all tracked channels.</p>
        </div>
        
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={contentType}
            onChange={(e) => { setContentType(e.target.value); setPage(1); }}
            className="px-4 py-2.5 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 font-medium shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer"
          >
            <option value="all">All Content</option>
            <option value="normal">Normal Videos</option>
            <option value="shorts">Shorts</option>
            <option value="live">Live Streams</option>
          </select>
          
          <div className="flex items-center gap-2 bg-white p-1.5 rounded-xl border border-gray-200 shadow-sm">
            <SortButton label="Latest" field="upload_date" />
            <SortButton label="Most Viewed" field="view_count" />
            <SortButton label="Duration" field="duration" />
          </div>
        </div>
      </div>

      <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200 min-h-[500px] flex flex-col">
        {isError ? (
          <div className="text-center py-12 text-red-500 flex-grow flex items-center justify-center">
            Failed to load videos. Please try again or check backend server.
          </div>
        ) : (
          <div className="flex-grow">
            <VideoGrid videos={data?.items || data?.videos} loading={isLoading} />
          </div>
        )}

        {/* Pagination */}
        {data?.total > 0 && (
          <div className="mt-8 flex items-center justify-between border-t border-gray-100 pt-6">
            <div className="text-sm text-gray-500">
              Showing <span className="font-medium text-gray-900">{((page - 1) * perPage) + 1}</span> to <span className="font-medium text-gray-900">{Math.min(page * perPage, data.total)}</span> of <span className="font-medium text-gray-900">{formatNumber(data.total)}</span> videos
            </div>
            
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 hover:text-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <div className="px-4 py-2 rounded-lg bg-indigo-50 text-indigo-700 font-bold text-sm shadow-sm">
                Page {page}
              </div>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={!data?.has_more}
                className="p-2 rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 hover:text-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function formatNumber(num) {
  if (num === undefined || num === null) return '0';
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}
