import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Eye, Clock, Calendar, ThumbsUp, MessageSquare, Loader2, PlayCircle, Download, CheckCircle, AlertCircle } from 'lucide-react';
import { getVideo } from '../api/videos';
import { startDownload } from '../api/downloads';
import { formatNumber, formatDuration, formatDate } from '../utils/formatters';
import { API_BASE_URL } from '../constants';

export default function VideoDetail() {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('description');
  
  const [shouldPoll, setShouldPoll] = useState(true);

  const { data: video, isLoading } = useQuery({
    queryKey: ['video', id],
    queryFn: () => getVideo(id),
    refetchInterval: shouldPoll ? 3000 : false
  });

  const startDownloadMutation = useMutation({
    mutationFn: startDownload,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['downloads'] });
    }
  });

  useEffect(() => {
    if (video && video.upload_date) {
      setShouldPoll(false);
    } else if (video && !video.upload_date) {
      setShouldPoll(true);
    }
  }, [video]);

  if (isLoading) {
    return <div className="p-8 text-center text-gray-500">Loading video details...</div>;
  }

  if (!video) {
    return <div className="p-8 text-center text-red-500">Video not found.</div>;
  }

  const handleDownload = () => {
    const canonicalUrl = `https://www.youtube.com/watch?v=${video.id}`;
    startDownloadMutation.mutate({
      url: canonicalUrl,
      download_type: 'video',
      quality: 'best',
      format: 'mp4'
    });
  };

  const BACKEND_BASE_URL = API_BASE_URL.replace(/\/api\/?$/, '');
  const thumbnail = video.thumbnail_url?.startsWith('/') 
    ? `${BACKEND_BASE_URL}${video.thumbnail_url}` 
    : video.thumbnail_url || `https://i.ytimg.com/vi/${video.id}/hqdefault.jpg`;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <Link to={`/channels/${video.channel_id}`} className="inline-flex items-center text-sm font-medium text-gray-500 hover:text-indigo-600 transition-colors">
          <ArrowLeft className="w-4 h-4 mr-1" /> Back to Channel
        </Link>
      </div>
      
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
        {/* Header / Player Area (Placeholder) */}
        <div className="aspect-video bg-black relative flex items-center justify-center group">
          <img 
            src={thumbnail} 
            alt="Thumbnail" 
            className="w-full h-full object-cover opacity-60 group-hover:opacity-40 transition-opacity" 
          />
          <a 
            href={`https://youtube.com/watch?v=${video.id}`} 
            target="_blank" 
            rel="noreferrer"
            className="absolute z-10 text-white opacity-90 hover:text-red-500 hover:opacity-100 transition-colors cursor-pointer flex flex-col items-center"
          >
            <PlayCircle className="w-20 h-20 shadow-xl rounded-full" />
            <span className="mt-2 font-medium bg-black/50 px-3 py-1 rounded">Watch on YouTube</span>
          </a>
        </div>
        
        {/* Info */}
        <div className="p-6 md:p-10">
          <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6 mb-8">
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-gray-900 leading-snug">
                {video.title}
              </h1>
              <div className="mt-3 flex flex-wrap items-center gap-4 text-sm text-gray-600">
                <span className="flex items-center bg-gray-100 px-2.5 py-1 rounded-md font-medium text-gray-800">
                  <Eye className="w-4 h-4 mr-1.5 text-gray-500" />
                  {formatNumber(video.view_count)} views
                </span>
                <span className="flex items-center">
                  <Clock className="w-4 h-4 mr-1.5" />
                  {formatDuration(video.duration)}
                </span>
                <span className="flex items-center">
                  <Calendar className="w-4 h-4 mr-1.5" />
                  {formatDate(video.upload_date)}
                </span>
                {video.like_count > 0 && (
                  <span className="flex items-center">
                    <ThumbsUp className="w-4 h-4 mr-1.5" />
                    {formatNumber(video.like_count)} likes
                  </span>
                )}
                {video.comment_count > 0 && (
                  <span className="flex items-center">
                    <MessageSquare className="w-4 h-4 mr-1.5" />
                    {formatNumber(video.comment_count)} comments
                  </span>
                )}
              </div>
            </div>
            
            <div className="flex flex-col items-stretch lg:items-end gap-1.5 w-full lg:w-auto">
              {!video.upload_date && (
                <div className="flex items-center text-sm text-yellow-600 bg-yellow-50 border border-yellow-100 rounded-lg px-4 py-2 font-medium shadow-sm animate-pulse mb-1.5">
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Background details enrichment in progress...
                </div>
              )}
              <button 
                onClick={handleDownload}
                disabled={startDownloadMutation.isPending || startDownloadMutation.isSuccess}
                className={`w-full lg:w-auto px-5 py-2.5 font-medium rounded-lg transition-all shadow-sm flex items-center justify-center border ${
                  startDownloadMutation.isSuccess
                    ? 'bg-emerald-600 hover:bg-emerald-700 text-white border-emerald-600'
                    : startDownloadMutation.isError
                    ? 'bg-red-600 hover:bg-red-700 text-white border-red-600'
                    : 'bg-indigo-600 hover:bg-indigo-700 text-white border-indigo-600 disabled:opacity-50'
                }`}
              >
                {startDownloadMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Queueing...
                  </>
                ) : startDownloadMutation.isSuccess ? (
                  <>
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Download Queued
                  </>
                ) : startDownloadMutation.isError ? (
                  <>
                    <AlertCircle className="w-4 h-4 mr-2" />
                    Failed - Retry
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4 mr-2" />
                    Download Video
                  </>
                )}
              </button>
              {startDownloadMutation.isError && (
                <p className="text-xs font-semibold text-red-600 mt-1 max-w-[200px] text-center lg:text-right">
                  {startDownloadMutation.error?.response?.data?.message || startDownloadMutation.error?.response?.data?.error || "Queue failed"}
                </p>
              )}
            </div>
          </div>

          
          {/* Tabs */}
          <div className="border-b border-gray-200 mb-6">
            <div className="flex space-x-8">
              <button 
                className={`pb-4 font-medium text-sm border-b-2 transition-colors ${activeTab === 'description' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}
                onClick={() => setActiveTab('description')}
              >
                Description
              </button>
              <button 
                className={`pb-4 font-medium text-sm border-b-2 transition-colors ${activeTab === 'formats' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}
                onClick={() => setActiveTab('formats')}
              >
                Formats & Streams
              </button>
              {video.chapters && video.chapters.length > 0 && (
                <button 
                  className={`pb-4 font-medium text-sm border-b-2 transition-colors ${activeTab === 'chapters' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}
                  onClick={() => setActiveTab('chapters')}
                >
                  Chapters ({video.chapters.length})
                </button>
              )}
            </div>
          </div>
          
          {/* Tab Content */}
          <div className="min-h-[300px]">
            {activeTab === 'description' && (
              <div className="bg-gray-50 rounded-xl p-5 border border-gray-100">
                {video.description ? (
                  <p className="text-gray-800 whitespace-pre-wrap break-words text-sm leading-relaxed">
                    {video.description}
                  </p>
                ) : (
                  <p className="text-gray-500 italic">No description available. Enrichment pending or details not found.</p>
                )}
              </div>
            )}
            
            {activeTab === 'formats' && (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Format</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Resolution</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ext</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Size</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {video.formats && video.formats.length > 0 ? (
                      video.formats.slice(0, 15).map((f, i) => (
                        <tr key={i}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{f.format_note || f.format_id}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{f.resolution || (f.width ? `${f.width}x${f.height}` : 'audio')}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{f.ext}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {f.filesize ? `${(f.filesize / 1024 / 1024).toFixed(1)} MB` : 'Unknown'}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="4" className="px-6 py-8 text-center text-gray-500">
                          Format details are not stored to optimize database storage.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
            
            {activeTab === 'chapters' && video.chapters && (
              <div className="space-y-2">
                {video.chapters.map((chapter, i) => (
                  <div key={i} className="flex items-center p-3 hover:bg-gray-50 rounded-lg transition-colors border border-transparent hover:border-gray-200 cursor-pointer">
                    <div className="text-indigo-600 font-mono text-sm w-16 shrink-0">
                      {formatDuration(chapter.start_time)}
                    </div>
                    <div className="text-gray-900 font-medium">
                      {chapter.title}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
