import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Users, Video, Eye, Calendar, BadgeCheck, Loader2, CheckCircle } from 'lucide-react';
import { getChannel, refreshChannel } from '../api/channels';
import { getVideos } from '../api/videos';
import axios from 'axios';
import { API_BASE_URL } from '../constants';
import VideoGrid from '../components/video/VideoGrid';
import useNotificationStore from '../stores/notificationStore';

export default function ChannelDetail() {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const notify = useNotificationStore((s) => s.addNotification);
  const [page, setPage] = useState(1);
  const [activeTab, setActiveTab] = useState('videos');
  const perPage = 20;
  
  const { data: channel, isLoading: channelLoading } = useQuery({
    queryKey: ['channel', id],
    queryFn: () => getChannel(id)
  });

  const { data: videosData, isLoading: videosLoading } = useQuery({
    queryKey: ['videos', 'channel', id, activeTab, page],
    queryFn: () => {
      const params = { channel_id: id, page, per_page: perPage };
      if (activeTab === 'shorts') {
        params.is_short = true;
      } else if (activeTab === 'streams') {
        params.is_live = true;
      } else {
        params.is_short = false;
        params.is_live = false;
      }
      return getVideos(params);
    },
    enabled: !!channel,
    refetchInterval: (data) => data?.items?.some(video => !video.upload_date) ? 3000 : false
  });

  const [activeJobId, setActiveJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [jobError, setJobError] = useState(null);
  const [crawlResult, setCrawlResult] = useState(null);

  useEffect(() => {
    if (!activeJobId) return;

    const intervalId = setInterval(async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/jobs/${activeJobId}`);
        const { status, error_message, payload } = response.data;
        setJobStatus(status);
        if (status === 'complete') {
          clearInterval(intervalId);
          setActiveJobId(null);
          setJobStatus(null);
          if (payload && payload.result) {
            setCrawlResult(payload.result);
          }
          notify({ type: 'success', title: 'Crawl Complete', message: `Video crawl finished for this channel.` });
          queryClient.invalidateQueries({ queryKey: ['videos', 'channel', id] });
          queryClient.invalidateQueries({ queryKey: ['channel', id] });
        } else if (status === 'failed') {
          clearInterval(intervalId);
          setActiveJobId(null);
          setJobStatus(null);
          notify({ type: 'error', title: 'Crawl Failed', message: error_message || 'Video crawl job failed.' });
          setJobError(error_message || 'Crawl job failed.');
        }
      } catch (err) {
        console.error('Error polling job status:', err);
      }
    }, 1500);

    return () => clearInterval(intervalId);
  }, [activeJobId, id, queryClient]);

  const crawlLatestMutation = useMutation({
    mutationFn: async () => {
      setJobError(null);
      setCrawlResult(null);
      const response = await axios.post(`${API_BASE_URL}/channels/${id}/crawl`, {
        start_index: 1,
        limit: 50,
        refresh: false
      });
      return response.data;
    },
    onSuccess: (data) => {
      if (data.job_id) {
        setActiveJobId(data.job_id);
        setJobStatus('queued');
      }
    }
  });

  const refreshVideosMutation = useMutation({
    mutationFn: async () => {
      setJobError(null);
      setCrawlResult(null);
      const response = await axios.post(`${API_BASE_URL}/channels/${id}/crawl`, {
        start_index: 1,
        limit: 50,
        refresh: true
      });
      return response.data;
    },
    onSuccess: (data) => {
      if (data.job_id) {
        setActiveJobId(data.job_id);
        setJobStatus('queued');
      }
    }
  });

  const loadMoreMutation = useMutation({
    mutationFn: async () => {
      setJobError(null);
      setCrawlResult(null);
      const response = await axios.post(`${API_BASE_URL}/channels/${id}/crawl`, {
        load_more: true,
        limit: 20
      });
      return response.data;
    },
    onSuccess: (data) => {
      if (data.job_id) {
        setActiveJobId(data.job_id);
        setJobStatus('queued');
      }
    }
  });

  const refreshMutation = useMutation({
    mutationFn: () => refreshChannel(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channel', id] });
    }
  });

  if (channelLoading) {
    return <div className="p-8 text-center text-gray-500">Loading channel details...</div>;
  }

  if (!channel) {
    return <div className="p-8 text-center text-red-500">Channel not found.</div>;
  }

  return (
    <div className="space-y-6">
      <Link to="/channels" className="inline-flex items-center text-sm font-medium text-gray-500 hover:text-indigo-600 transition-colors">
        <ArrowLeft className="w-4 h-4 mr-1" /> Back to Channels
      </Link>
      
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
        {/* Banner */}
        <div className="h-48 md:h-64 bg-gradient-to-r from-indigo-900 via-indigo-700 to-purple-800 relative">
          {channel.banner_url && (
            <img src={channel.banner_url} alt="Banner" className="w-full h-full object-cover" />
          )}
        </div>
        
        {/* Profile Info */}
        <div className="px-6 md:px-10 pb-8 relative">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-6">
            <div className="flex flex-col sm:flex-row items-center sm:items-end sm:space-x-6 relative -mt-16 sm:-mt-20">
              <div className="w-32 h-32 md:w-40 md:h-40 rounded-full border-4 border-white bg-white overflow-hidden shadow-md">
                {channel.avatar_url ? (
                  <img src={channel.avatar_url} alt={channel.display_name} className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full bg-indigo-100 flex items-center justify-center text-4xl text-indigo-500 font-bold">
                    {channel.display_name.charAt(0)}
                  </div>
                )}
              </div>
              <div className="mt-4 sm:mt-0 text-center sm:text-left pb-2">
                <h1 className="text-3xl font-bold text-gray-900 flex items-center justify-center sm:justify-start">
                  {channel.display_name}
                  {channel.is_verified && <BadgeCheck className="w-7 h-7 text-indigo-500 ml-2" />}
                </h1>
                <p className="text-lg text-gray-500 mt-1">{channel.handle || channel.id}</p>
              </div>
            </div>
            
            <div className="mt-6 sm:mt-0 flex flex-wrap gap-3 justify-center sm:justify-end">
              <button 
                onClick={() => refreshMutation.mutate()} 
                disabled={refreshMutation.isPending || !!activeJobId}
                className="px-4 py-2 bg-white border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors shadow-sm disabled:opacity-50 flex items-center"
              >
                {refreshMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                Refresh Profile
              </button>
              <button 
                onClick={() => crawlLatestMutation.mutate()}
                disabled={crawlLatestMutation.isPending || !!activeJobId}
                className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors shadow-sm disabled:opacity-50 flex items-center"
                title="Target distribution: 30 Videos, 10 Shorts, 10 Live Streams"
              >
                {crawlLatestMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                Crawl 50 Videos
              </button>
              <button 
                onClick={() => refreshVideosMutation.mutate()}
                disabled={refreshVideosMutation.isPending || !!activeJobId}
                className="px-4 py-2 bg-emerald-600 text-white text-sm font-medium rounded-lg hover:bg-emerald-700 transition-colors shadow-sm disabled:opacity-50 flex items-center"
                title="Refresh videos from YouTube"
              >
                {refreshVideosMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                Refresh Videos
              </button>
            </div>
          </div>
          <div className="mt-2 text-right">
            <span className="text-xs text-gray-400">
              * Target crawl distribution: 30 Videos, 10 Shorts, 10 Live Streams
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
            <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
              <div className="flex items-center text-gray-500 mb-1">
                <Users className="w-4 h-4 mr-1.5" /> Subscribers
              </div>
              <div className="text-2xl font-bold text-gray-900">{channel.subscriber_count?.toLocaleString() || '0'}</div>
            </div>
            <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
              <div className="flex items-center text-gray-500 mb-1">
                <Video className="w-4 h-4 mr-1.5" /> Videos
              </div>
              <div className="text-2xl font-bold text-gray-900">{channel.video_count?.toLocaleString() || '0'}</div>
            </div>
            <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
              <div className="flex items-center text-gray-500 mb-1">
                <Eye className="w-4 h-4 mr-1.5" /> Total Views
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {channel.view_count && channel.view_count > 0 ? channel.view_count.toLocaleString() : 'Unavailable'}
              </div>
            </div>
            <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
              <div className="flex items-center text-gray-500 mb-1">
                <Calendar className="w-4 h-4 mr-1.5" /> Joined
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {channel.join_date ? new Date(channel.join_date).getFullYear() : 'Unavailable'}
              </div>
            </div>
          </div>
          
          {channel.description && (
            <div className="mt-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">About</h3>
              <p className="text-gray-700 whitespace-pre-wrap">{channel.description}</p>
            </div>
          )}
        </div>
        
        {/* Tabs */}
        <div className="border-t border-gray-200">
          <div className="flex px-6 md:px-10 space-x-8">
            <button 
              className={`py-4 font-medium text-sm border-b-2 transition-colors ${activeTab === 'videos' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}
              onClick={() => { setActiveTab('videos'); setPage(1); }}
            >
              Videos
            </button>
            <button 
              className={`py-4 font-medium text-sm border-b-2 transition-colors ${activeTab === 'shorts' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}
              onClick={() => { setActiveTab('shorts'); setPage(1); }}
            >
              Shorts
            </button>
            <button 
              className={`py-4 font-medium text-sm border-b-2 transition-colors ${activeTab === 'streams' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}
              onClick={() => { setActiveTab('streams'); setPage(1); }}
            >
              Live Streams
            </button>
          </div>
        </div>
      </div>
      
      {/* Tab Content */}
      <div className="py-6">
        {activeJobId && (
          <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4 flex items-center space-x-3 mb-6 shadow-sm">
            <Loader2 className="w-5 h-5 text-indigo-600 animate-spin" />
            <span className="text-indigo-800 font-medium">
              Crawl job running in background... Status: <span className="capitalize">{jobStatus || 'Processing'}</span>
            </span>
          </div>
        )}
        {jobError && (
          <div className="bg-red-50 border border-red-100 rounded-xl p-4 flex items-center space-x-3 mb-6 text-red-800 font-medium shadow-sm">
            <span>Error: {jobError}</span>
          </div>
        )}

        {crawlResult && (
          <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-6 mb-6 shadow-sm flex flex-col space-y-3 animate-fadeIn">
            <h3 className="text-emerald-950 font-bold text-lg flex items-center">
              <CheckCircle className="w-5 h-5 text-emerald-600 mr-2" /> Crawl Job Completed Successfully!
            </h3>
            <p className="text-emerald-800 text-sm">
              We completed crawling the uploads playlist. The following videos were imported/updated:
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-2">
              <div className="bg-white p-3 rounded-lg border border-emerald-200 shadow-sm">
                <div className="text-xs text-emerald-600 font-medium">Normal Videos</div>
                <div className="text-lg font-bold text-emerald-950">{crawlResult.normal} / {crawlResult.target_normal}</div>
              </div>
              <div className="bg-white p-3 rounded-lg border border-emerald-200 shadow-sm">
                <div className="text-xs text-emerald-600 font-medium">Shorts</div>
                <div className="text-lg font-bold text-emerald-950">{crawlResult.shorts} / {crawlResult.target_shorts}</div>
              </div>
              <div className="bg-white p-3 rounded-lg border border-emerald-200 shadow-sm">
                <div className="text-xs text-emerald-600 font-medium">Live Streams</div>
                <div className="text-lg font-bold text-emerald-950">{crawlResult.live} / {crawlResult.target_live}</div>
              </div>
              <div className="bg-white p-3 rounded-lg border border-emerald-200 shadow-sm">
                <div className="text-xs text-emerald-600 font-medium">Total Imported</div>
                <div className="text-lg font-bold text-emerald-950">{crawlResult.total} / {crawlResult.target_total}</div>
              </div>
            </div>
          </div>
        )}

        <div className="space-y-6">
          <VideoGrid videos={videosData?.items} loading={videosLoading} />
          
          {/* Load More & Pagination Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-6">
            {/* Load More from YouTube button */}
            {activeTab === 'videos' && (
              <div>
                <button
                  onClick={() => loadMoreMutation.mutate()}
                  disabled={loadMoreMutation.isPending || !!activeJobId}
                  className="w-full sm:w-auto px-5 py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors shadow flex items-center justify-center"
                >
                  {loadMoreMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Load More from YouTube
                </button>
              </div>
            )}

            {/* Local database pagination */}
            {videosData && videosData.total > perPage && (
              <div className="flex flex-1 items-center justify-between border border-gray-200 bg-white px-4 py-3 sm:px-6 rounded-xl shadow-sm">
                <div className="flex flex-1 justify-between sm:hidden">
                  <button
                    disabled={page === 1}
                    onClick={() => setPage(p => Math.max(p - 1, 1))}
                    className="relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <button
                    disabled={page >= Math.ceil(videosData.total / perPage)}
                    onClick={() => setPage(p => Math.min(p + 1, Math.ceil(videosData.total / perPage)))}
                    className="relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
                <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm text-gray-700">
                      Showing <span className="font-medium">{(page - 1) * perPage + 1}</span> to <span className="font-medium">{Math.min(page * perPage, videosData.total)}</span> of <span className="font-medium">{videosData.total}</span> results
                    </p>
                  </div>
                  <div>
                    <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm bg-white" aria-label="Pagination">
                      <button
                        disabled={page === 1}
                        onClick={() => setPage(p => Math.max(p - 1, 1))}
                        className="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50"
                      >
                        <span className="sr-only">Previous</span>
                        <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                          <path fillRule="evenodd" d="M12.79 5.23a.75.75 0 01-.02 1.06L8.832 10l3.938 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z" clipRule="evenodd" />
                        </svg>
                      </button>
                      
                      {Array.from({ length: Math.min(5, Math.ceil(videosData.total / perPage)) }, (_, i) => {
                        const totalPages = Math.ceil(videosData.total / perPage);
                        let pageNum = page;
                        if (page <= 3) {
                          pageNum = i + 1;
                        } else if (page > totalPages - 2) {
                          pageNum = totalPages - 4 + i;
                        } else {
                          pageNum = page - 2 + i;
                        }
                        
                        if (pageNum < 1 || pageNum > totalPages) return null;

                        return (
                          <button
                            key={pageNum}
                            onClick={() => setPage(pageNum)}
                            className={`relative inline-flex items-center px-4 py-2 text-sm font-semibold focus:z-20 ${
                              page === pageNum
                                ? 'z-10 bg-indigo-600 text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600'
                                : 'text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:outline-offset-0'
                            }`}
                          >
                            {pageNum}
                          </button>
                        );
                      })}

                      <button
                        disabled={page >= Math.ceil(videosData.total / perPage)}
                        onClick={() => setPage(p => Math.min(p + 1, Math.ceil(videosData.total / perPage)))}
                        className="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50"
                      >
                        <span className="sr-only">Next</span>
                        <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                          <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
                        </svg>
                      </button>
                    </nav>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
