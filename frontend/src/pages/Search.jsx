import { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { 
  Search as SearchIcon, 
  SearchX, 
  Youtube, 
  Database, 
  SlidersHorizontal, 
  ChevronDown, 
  ChevronUp, 
  AlertTriangle, 
  RefreshCw, 
  Plus, 
  Check, 
  ExternalLink, 
  Clock, 
  Eye, 
  History, 
  Loader2, 
  X,
  PlayCircle
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { searchYoutube, searchInternal, getSearchHistory } from '../api/search';
import { importVideo } from '../api/videos';
import { getChannels } from '../api/channels';
import { formatDuration, formatNumber, formatRelativeTime } from '../utils/formatters';

export default function Search() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();

  // Search state parameters from URL query params
  const qParam = searchParams.get('q') || '';
  const modeParam = searchParams.get('mode') || 'youtube'; // 'youtube' | 'library'
  const typeParam = searchParams.get('type') || 'video'; // 'video' | 'channel' | 'playlist' | 'transcript'
  const channelIdParam = searchParams.get('channel_id') || '';
  const hasTranscriptParam = searchParams.get('has_transcript') || 'any'; // 'any' | 'yes' | 'no'
  const isShortParam = searchParams.get('is_short') || 'any'; // 'any' | 'yes' | 'no'
  const uploadAfterParam = searchParams.get('upload_after') || '';
  const uploadBeforeParam = searchParams.get('upload_before') || '';
  const pageParam = parseInt(searchParams.get('page') || '1', 10);

  // Local state
  const [searchQuery, setSearchQuery] = useState(qParam);
  const [isSuggestOpen, setIsSuggestOpen] = useState(false);
  const [recentSuggestions, setRecentSuggestions] = useState([]);
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [importingIds, setImportingIds] = useState({}); // video_id -> boolean (true=importing)
  const [bypassCache, setBypassCache] = useState(false);

  const suggestRef = useRef(null);

  // Sync searchQuery state with URL parameter changes
  useEffect(() => {
    setSearchQuery(qParam);
  }, [qParam]);

  // Load suggestions from local storage
  useEffect(() => {
    const saved = localStorage.getItem('recent_searches');
    if (saved) {
      try {
        setRecentSuggestions(JSON.parse(saved));
      } catch (e) {
        setRecentSuggestions([]);
      }
    }
  }, []);

  // Close suggestion dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (suggestRef.current && !suggestRef.current.contains(event.target)) {
        setIsSuggestOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Channels list for library filter
  const { data: channelsData } = useQuery({
    queryKey: ['channels-filter'],
    queryFn: () => getChannels({ per_page: 100 }),
    enabled: modeParam === 'library'
  });
  const channels = channelsData?.items || [];

  // Search History logs from DB
  const { data: searchHistoryData, refetch: refetchHistory } = useQuery({
    queryKey: ['search-history'],
    queryFn: getSearchHistory,
    enabled: isHistoryOpen
  });
  const historyLogs = searchHistoryData || [];

  // Main YouTube search query hook
  const { 
    data: ytData, 
    isLoading: isYtLoading, 
    error: ytError, 
    refetch: refetchYt 
  } = useQuery({
    queryKey: ['search-youtube', qParam, typeParam, bypassCache],
    queryFn: () => {
      // typeParam must be valid for youtube
      const t = ['video', 'channel', 'playlist'].includes(typeParam) ? typeParam : 'video';
      return searchYoutube(qParam, t, 20, bypassCache);
    },
    enabled: modeParam === 'youtube' && qParam.trim().length > 0,
    retry: false
  });

  // Main Library search query hook
  const { 
    data: libData, 
    isLoading: isLibLoading, 
    error: libError 
  } = useQuery({
    queryKey: [
      'search-library', 
      qParam, 
      typeParam, 
      channelIdParam, 
      hasTranscriptParam, 
      isShortParam, 
      uploadAfterParam, 
      uploadBeforeParam, 
      pageParam
    ],
    queryFn: () => {
      // typeParam must be valid for library (video/channel/transcript)
      const t = ['video', 'channel', 'transcript'].includes(typeParam) ? typeParam : 'video';
      return searchInternal({
        q: qParam,
        type: t,
        channel_id: channelIdParam || undefined,
        has_transcript: hasTranscriptParam !== 'any' ? hasTranscriptParam : undefined,
        is_short: isShortParam !== 'any' ? isShortParam : undefined,
        upload_after: uploadAfterParam || undefined,
        upload_before: uploadBeforeParam || undefined,
        page: pageParam,
        per_page: 20
      });
    },
    enabled: modeParam === 'library' && qParam.trim().length > 0
  });

  const isLoading = isYtLoading || isLibLoading;
  const error = modeParam === 'youtube' ? ytError : libError;

  // Save query to local storage recent searches
  const saveSuggestion = (query) => {
    if (!query || !query.trim()) return;
    const q = query.trim();
    let current = [...recentSuggestions];
    current = current.filter(item => item.toLowerCase() !== q.toLowerCase());
    current.unshift(q);
    const updated = current.slice(0, 5);
    setRecentSuggestions(updated);
    localStorage.setItem('recent_searches', JSON.stringify(updated));
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    saveSuggestion(searchQuery);
    setIsSuggestOpen(false);
    setBypassCache(false);

    const params = {
      q: searchQuery,
      mode: modeParam,
      type: typeParam,
      page: 1
    };

    if (modeParam === 'library') {
      if (channelIdParam) params.channel_id = channelIdParam;
      if (hasTranscriptParam !== 'any') params.has_transcript = hasTranscriptParam;
      if (isShortParam !== 'any') params.is_short = isShortParam;
      if (uploadAfterParam) params.upload_after = uploadAfterParam;
      if (uploadBeforeParam) params.upload_before = uploadBeforeParam;
    }

    setSearchParams(params);
  };

  const handleSuggestionClick = (suggestion) => {
    setSearchQuery(suggestion);
    saveSuggestion(suggestion);
    setIsSuggestOpen(false);
    setBypassCache(false);
    setSearchParams({
      q: suggestion,
      mode: modeParam,
      type: typeParam,
      page: 1
    });
  };

  const handleModeChange = (newMode) => {
    // Reset page and adjust type if necessary
    const newType = newMode === 'library' && typeParam === 'playlist' ? 'video' : typeParam;
    const params = {
      q: qParam,
      mode: newMode,
      type: newType,
      page: 1
    };
    setSearchParams(params);
  };

  const handleTypeChange = (newType) => {
    const params = {
      q: qParam,
      mode: modeParam,
      type: newType,
      page: 1
    };
    if (channelIdParam) params.channel_id = channelIdParam;
    if (hasTranscriptParam !== 'any') params.has_transcript = hasTranscriptParam;
    if (isShortParam !== 'any') params.is_short = isShortParam;
    if (uploadAfterParam) params.upload_after = uploadAfterParam;
    if (uploadBeforeParam) params.upload_before = uploadBeforeParam;
    setSearchParams(params);
  };

  // Re-run search bypassing cache
  const handleRefreshSearch = () => {
    setBypassCache(true);
    setTimeout(() => {
      refetchYt();
    }, 100);
  };

  // Import YouTube Video into Library
  const handleImportVideo = async (videoId, e) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    // Safety: only import if we are in a video search context
    if (!videoId || typeParam !== 'video') return;
    if (importingIds[videoId]) return;

    setImportingIds(prev => ({ ...prev, [videoId]: true }));
    try {
      await importVideo(videoId);
      queryClient.invalidateQueries(['search-youtube']);
      queryClient.invalidateQueries(['videos']);
    } catch (err) {
      console.error('Failed to import video:', err);
      const msg = err.response?.data?.message || 'Failed to add video to library. Please try again.';
      alert(msg);
    } finally {
      setImportingIds(prev => ({ ...prev, [videoId]: false }));
    }
  };

  // Transparently import and navigate when clicking a card
  const handleCardClick = async (video, e) => {
    e.preventDefault();
    // Safety: only handle card clicks for video-type results
    if (!video?.video_id) return;
    if (video.in_library) {
      navigate(`/videos/${video.video_id}`);
    } else {
      setImportingIds(prev => ({ ...prev, [video.video_id]: true }));
      try {
        await importVideo(video.video_id);
        navigate(`/videos/${video.video_id}`);
      } catch (err) {
        console.error('Failed to import video:', err);
        const msg = err.response?.data?.message || 'Failed to open video. Could not add it to your library.';
        alert(msg);
      } finally {
        setImportingIds(prev => ({ ...prev, [video.video_id]: false }));
      }
    }
  };

  // Clear query and search state
  const handleClear = () => {
    setSearchQuery('');
    setSearchParams({});
  };

  const resultsList = modeParam === 'youtube' ? ytData?.results || [] : libData?.items || [];
  const resultsCount = modeParam === 'youtube' ? resultsList.length : libData?.total || 0;
  const hasResults = resultsList.length > 0;

  // Build breadcrumb/stats display
  const isEmptyState = !qParam;

  return (
    <div className="space-y-8 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      
      {/* Search Header Container - shifts from center to top */}
      <div className={`transition-all duration-500 ease-out flex flex-col items-center ${isEmptyState ? 'pt-20 pb-16' : 'pt-2'}`}>
        
        {/* Title / Hero */}
        {isEmptyState && (
          <div className="text-center mb-8 space-y-2 animate-fade-in">
            <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
              Search YouTube & Your Library
            </h1>
            <p className="text-gray-500 text-lg max-w-md mx-auto">
              Analyze transcripts, query channels, or search and import new videos.
            </p>
          </div>
        )}

        {/* Search Bar Block */}
        <div className="w-full max-w-2xl relative" ref={suggestRef}>
          <form onSubmit={handleSearchSubmit} className="flex gap-2">
            <div className="relative flex-grow shadow-lg rounded-2xl">
              <span className="absolute inset-y-0 left-4 flex items-center pointer-events-none text-gray-400">
                <SearchIcon className="w-5 h-5" />
              </span>
              <input
                type="text"
                value={searchQuery}
                onFocus={() => setIsSuggestOpen(true)}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setIsSuggestOpen(true);
                }}
                placeholder={modeParam === 'youtube' ? "Search YouTube videos, channels, or playlists..." : "Search local videos, channels, or transcripts..."}
                className="w-full pl-12 pr-10 py-4 bg-white border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900 placeholder-gray-400 text-base transition-all shadow-inner"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={handleClear}
                  className="absolute inset-y-0 right-3 flex items-center text-gray-400 hover:text-gray-600"
                >
                  <X className="w-5 h-5" />
                </button>
              )}
            </div>
            <button
              type="submit"
              className="px-6 py-4 bg-gradient-to-r from-indigo-600 to-indigo-700 text-white font-semibold rounded-2xl hover:from-indigo-700 hover:to-indigo-800 transition-all flex items-center gap-2 shadow-md hover:shadow-lg active:scale-95"
            >
              <span>Search</span>
            </button>
          </form>

          {/* Suggestions Dropdown */}
          {isSuggestOpen && recentSuggestions.length > 0 && !searchQuery && (
            <div className="absolute left-0 right-0 mt-2 bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden z-30 animate-slide-down">
              <div className="px-4 py-2 border-b border-gray-50 flex items-center gap-1.5 text-xs font-semibold text-gray-400">
                <History className="w-3.5 h-3.5" />
                <span>RECENT SEARCHES</span>
              </div>
              <ul className="divide-y divide-gray-50">
                {recentSuggestions.map((suggestion, idx) => (
                  <li key={idx}>
                    <button
                      type="button"
                      onClick={() => handleSuggestionClick(suggestion)}
                      className="w-full text-left px-5 py-3 hover:bg-gray-50 text-sm text-gray-700 flex items-center justify-between"
                    >
                      <span>{suggestion}</span>
                      <span className="text-[10px] text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">Recall</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Mode Toggle Selection */}
        <div className="flex gap-4 mt-6 bg-gray-100 p-1.5 rounded-2xl shadow-inner">
          <button
            type="button"
            onClick={() => handleModeChange('youtube')}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all ${
              modeParam === 'youtube'
                ? 'bg-white text-indigo-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Youtube className="w-4 h-4" />
            <span>Search YouTube</span>
          </button>
          <button
            type="button"
            onClick={() => handleModeChange('library')}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all ${
              modeParam === 'library'
                ? 'bg-white text-indigo-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Database className="w-4 h-4" />
            <span>Search My Library</span>
          </button>
        </div>

        {/* Search Type Filter Tab Bar */}
        <div className="flex flex-wrap justify-center gap-2 mt-4">
          {(modeParam === 'youtube' ? ['video', 'channel', 'playlist'] : ['video', 'channel', 'transcript']).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => handleTypeChange(t)}
              className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider transition-all border ${
                typeParam === t
                  ? 'bg-indigo-50 border-indigo-200 text-indigo-700 shadow-xs'
                  : 'bg-white border-gray-200 text-gray-500 hover:border-gray-300 hover:text-gray-700'
              }`}
            >
              {t}s
            </button>
          ))}
        </div>
      </div>

      {/* Advanced Filters Drawer (Library Mode Only) */}
      {modeParam === 'library' && !isEmptyState && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden transition-all duration-300">
          <button
            type="button"
            onClick={() => setIsFiltersOpen(!isFiltersOpen)}
            className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-all font-semibold text-gray-700 text-sm"
          >
            <div className="flex items-center gap-2">
              <SlidersHorizontal className="w-4 h-4 text-indigo-500" />
              <span>Advanced Filters</span>
              {(channelIdParam || hasTranscriptParam !== 'any' || isShortParam !== 'any' || uploadAfterParam || uploadBeforeParam) && (
                <span className="bg-indigo-100 text-indigo-700 text-[10px] px-2 py-0.5 rounded-full font-bold">Active</span>
              )}
            </div>
            {isFiltersOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          
          {isFiltersOpen && (
            <div className="px-6 pb-6 pt-2 border-t border-gray-100 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 animate-slide-down">
              {/* Channel Filter (Only for Video/Transcript types) */}
              {typeParam !== 'channel' && (
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-gray-500">Channel</label>
                  <select
                    value={channelIdParam}
                    onChange={(e) => setSearchParams(prev => {
                      const next = new URLSearchParams(prev);
                      if (e.target.value) next.set('channel_id', e.target.value);
                      else next.delete('channel_id');
                      next.set('page', '1');
                      return next;
                    })}
                    className="bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">All Channels</option>
                    {channels.map((ch) => (
                      <option key={ch.id} value={ch.id}>{ch.display_name}</option>
                    ))}
                  </select>
                </div>
              )}

              {/* Transcript Filter (Only for Video type) */}
              {typeParam === 'video' && (
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-gray-500">Has Transcript</label>
                  <select
                    value={hasTranscriptParam}
                    onChange={(e) => setSearchParams(prev => {
                      const next = new URLSearchParams(prev);
                      next.set('has_transcript', e.target.value);
                      next.set('page', '1');
                      return next;
                    })}
                    className="bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="any">Any</option>
                    <option value="yes">Yes</option>
                    <option value="no">No</option>
                  </select>
                </div>
              )}

              {/* Duration/Short Filter (Only for Video type) */}
              {typeParam === 'video' && (
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-gray-500">Is Short</label>
                  <select
                    value={isShortParam}
                    onChange={(e) => setSearchParams(prev => {
                      const next = new URLSearchParams(prev);
                      next.set('is_short', e.target.value);
                      next.set('page', '1');
                      return next;
                    })}
                    className="bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="any">Any</option>
                    <option value="yes">Yes (Shorts)</option>
                    <option value="no">No (Standard videos)</option>
                  </select>
                </div>
              )}

              {/* Date Filters (Only for Video type) */}
              {typeParam === 'video' && (
                <>
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-semibold text-gray-500">Upload Date After</label>
                    <input
                      type="date"
                      value={uploadAfterParam}
                      onChange={(e) => setSearchParams(prev => {
                        const next = new URLSearchParams(prev);
                        if (e.target.value) next.set('upload_after', e.target.value);
                        else next.delete('upload_after');
                        next.set('page', '1');
                        return next;
                      })}
                      className="bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-semibold text-gray-500">Upload Date Before</label>
                    <input
                      type="date"
                      value={uploadBeforeParam}
                      onChange={(e) => setSearchParams(prev => {
                        const next = new URLSearchParams(prev);
                        if (e.target.value) next.set('upload_before', e.target.value);
                        else next.delete('upload_before');
                        next.set('page', '1');
                        return next;
                      })}
                      className="bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/* Main Results / Loading Section */}
      {!isEmptyState && (
        <div className="space-y-6">
          
          {/* Caching Banner for YouTube searches */}
          {modeParam === 'youtube' && ytData?.cached && (
            <div className="bg-amber-50 border border-amber-200 rounded-2xl px-5 py-3 flex items-center justify-between gap-4 text-sm text-amber-800 shadow-sm animate-fade-in">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
                <span>
                  Results served from cache · Refreshed {formatRelativeTime(ytData.cached_at)}
                </span>
              </div>
              <button
                type="button"
                onClick={handleRefreshSearch}
                className="flex items-center gap-1.5 bg-amber-100 hover:bg-amber-200 text-amber-900 font-semibold px-3 py-1.5 rounded-xl text-xs transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Refresh Now</span>
              </button>
            </div>
          )}

          {/* Loading Indicator */}
          {isLoading && (
            <div className="py-20 flex flex-col items-center justify-center gap-4 text-gray-400">
              <Loader2 className="w-10 h-10 animate-spin text-indigo-600" />
              <span className="font-semibold text-sm">
                {modeParam === 'youtube' ? "Searching YouTube..." : "Searching local library..."}
              </span>
            </div>
          )}

          {/* Error Indicator */}
          {error && !isLoading && (
            <div className="bg-red-50 border border-red-200 rounded-2xl p-6 flex flex-col items-center justify-center text-center gap-4 shadow-sm">
              <AlertTriangle className="w-12 h-12 text-red-600 animate-pulse" />
              <div className="space-y-1.5 max-w-md">
                <h3 className="font-bold text-red-800 text-lg">
                  {modeParam === 'youtube' ? "YouTube search temporarily unavailable" : "Internal search failed"}
                </h3>
                <p className="text-sm text-red-600">
                  {error.response?.data?.message || error.message || "yt-dlp couldn't reach YouTube. This may be a rate limit or bot detection issue."}
                </p>
              </div>
              {modeParam === 'youtube' && (
                <button
                  type="button"
                  onClick={handleRefreshSearch}
                  className="bg-red-600 hover:bg-red-700 text-white font-semibold px-4 py-2 rounded-xl text-sm transition-colors shadow-sm"
                >
                  Try Again
                </button>
              )}
            </div>
          )}

          {/* No Results Empty State */}
          {!isLoading && !error && !hasResults && (
            <div className="py-20 text-center flex flex-col items-center justify-center gap-4 border border-dashed border-gray-200 rounded-3xl bg-white p-8">
              <SearchX className="w-14 h-14 text-gray-300 animate-bounce" />
              <div className="space-y-1">
                <h3 className="font-bold text-gray-800 text-lg">
                  No {modeParam === 'youtube' ? 'YouTube' : 'library'} results found for "{qParam}"
                </h3>
                <p className="text-gray-500 text-sm max-w-sm">
                  Try different keywords, adjust filter parameters, or check your spelling.
                </p>
              </div>
            </div>
          )}

          {/* Results Grid / List */}
          {!isLoading && !error && hasResults && (
            <div className="space-y-4">
              <div className="flex justify-between items-center text-xs font-bold text-gray-400 uppercase tracking-wider">
                <span>Search Results</span>
                <span>{resultsCount} items found</span>
              </div>

              {/* RENDER BY MODE & TYPE */}

              {/* YouTube Video Results Grid */}
              {modeParam === 'youtube' && typeParam === 'video' && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {resultsList.map((video) => (
                    <div 
                      key={video.video_id} 
                      onClick={(e) => handleCardClick(video, e)}
                      className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-all group flex flex-col h-full relative cursor-pointer"
                    >
                      {/* Thumbnail Container */}
                      <div className="relative aspect-video bg-gray-100 overflow-hidden block">
                        <img 
                          src={video.thumbnail_url} 
                          alt={video.title} 
                          className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                        />
                        {video.duration_seconds > 0 && (
                          <div className="absolute bottom-2 right-2 bg-black/80 text-white text-[10px] font-bold px-1.5 py-0.5 rounded flex items-center">
                            {formatDuration(video.duration_seconds)}
                          </div>
                        )}
                        {importingIds[video.video_id] && (
                          <div className="absolute inset-0 bg-black/60 flex items-center justify-center z-10 text-white font-semibold text-sm gap-2">
                            <Loader2 className="w-5 h-5 animate-spin" />
                            <span>Adding to Library...</span>
                          </div>
                        )}
                      </div>

                      {/* Content */}
                      <div className="p-4 flex-grow flex flex-col justify-between">
                        <div className="space-y-1">
                          <h3 className="font-bold text-gray-900 leading-snug line-clamp-2 group-hover:text-indigo-600 transition-colors" title={video.title}>
                            {video.title}
                          </h3>
                          <p className="text-xs text-gray-500 font-semibold">{video.channel}</p>
                        </div>
                        
                        <div className="pt-4 space-y-3">
                          <div className="flex justify-between items-center text-[10px] text-gray-400 font-bold">
                            <span>{formatNumber(video.view_count)} views</span>
                            <span>{video.upload_date}</span>
                          </div>

                          {/* Add to Library / Action Button */}
                          <button
                            type="button"
                            disabled={video.in_library || importingIds[video.video_id]}
                            onClick={(e) => handleImportVideo(video.video_id, e)}
                            className={`w-full py-2.5 px-4 rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition-all shadow-sm ${
                              video.in_library
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 cursor-not-allowed'
                                : 'bg-indigo-600 hover:bg-indigo-700 text-white active:scale-95'
                            }`}
                          >
                            {video.in_library ? (
                              <>
                                <Check className="w-3.5 h-3.5" />
                                <span>In Library ✓</span>
                              </>
                            ) : (
                              <>
                                <Plus className="w-3.5 h-3.5" />
                                <span>Add to Library</span>
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* YouTube Channel Results Grid */}
              {modeParam === 'youtube' && typeParam === 'channel' && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {resultsList.map((chan) => (
                    <div 
                      key={chan.channel_id} 
                      className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 flex flex-col items-center text-center justify-between gap-4 hover:shadow-md transition-all"
                    >
                      <div className="flex flex-col items-center gap-3">
                        <img 
                          src={chan.thumbnail_url || 'https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?auto=format&fit=crop&w=120&h=120&q=80'} 
                          alt={chan.title} 
                          className="w-20 h-20 rounded-full object-cover border border-gray-100 shadow-sm"
                        />
                        <div>
                          <h3 className="font-bold text-gray-900 text-base leading-tight line-clamp-1">{chan.title}</h3>
                          {chan.handle && <p className="text-xs text-gray-400 font-semibold mt-0.5">{chan.handle}</p>}
                        </div>
                      </div>
                      <div className="flex justify-around w-full border-y border-gray-50 py-3 text-xs">
                        {chan.view_count && (
                          <div className="flex flex-col items-center">
                            <span className="font-bold text-gray-800">{formatNumber(chan.view_count)}</span>
                            <span className="text-[10px] text-gray-400 font-semibold uppercase">Views</span>
                          </div>
                        )}
                        {chan.video_count && (
                          <div className="flex flex-col items-center">
                            <span className="font-bold text-gray-800">{formatNumber(chan.video_count)}</span>
                            <span className="text-[10px] text-gray-400 font-semibold uppercase">Videos</span>
                          </div>
                        )}
                      </div>
                      <a 
                        href={`https://youtube.com/channel/${chan.channel_id}`}
                        target="_blank"
                        rel="noreferrer"
                        className="w-full py-2 bg-gray-50 hover:bg-gray-100 border border-gray-200 text-gray-700 font-bold rounded-xl text-xs flex items-center justify-center gap-1.5 transition-all shadow-xs"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                        <span>View on YouTube</span>
                      </a>
                    </div>
                  ))}
                </div>
              )}

              {/* YouTube Playlist Results Grid */}
              {modeParam === 'youtube' && typeParam === 'playlist' && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {resultsList.map((playlist) => (
                    <div 
                      key={playlist.playlist_id} 
                      className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-all flex flex-col h-full"
                    >
                      <div className="relative aspect-video bg-gray-100 overflow-hidden block">
                        <img 
                          src={playlist.thumbnail_url} 
                          alt={playlist.title} 
                          className="w-full h-full object-cover"
                        />
                        <div className="absolute top-2 right-2 bg-indigo-600 text-white text-[10px] font-bold px-2 py-0.5 rounded shadow-xs uppercase tracking-wider">
                          Playlist
                        </div>
                        {playlist.video_count > 0 && (
                          <div className="absolute bottom-2 right-2 bg-black/85 text-white text-[10px] font-bold px-2 py-0.5 rounded flex items-center">
                            {playlist.video_count} videos
                          </div>
                        )}
                      </div>
                      <div className="p-4 flex-grow flex flex-col justify-between gap-4">
                        <div className="space-y-1">
                          <h3 className="font-bold text-gray-900 leading-snug line-clamp-2" title={playlist.title}>
                            {playlist.title}
                          </h3>
                          <p className="text-xs text-gray-400 font-semibold">{playlist.channel}</p>
                        </div>
                        <a 
                          href={`https://youtube.com/playlist?list=${playlist.playlist_id}`}
                          target="_blank"
                          rel="noreferrer"
                          className="w-full py-2 bg-gray-50 hover:bg-gray-100 border border-gray-200 text-gray-700 font-bold rounded-xl text-xs flex items-center justify-center gap-1.5 transition-all shadow-xs"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          <span>View on YouTube</span>
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Library Video Results Grid */}
              {modeParam === 'library' && typeParam === 'video' && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {resultsList.map((video) => {
                    const fallbackThumb = video.thumbnail_url?.startsWith('/') 
                      ? `http://localhost:5000${video.thumbnail_url}` 
                      : video.thumbnail_url || `https://i.ytimg.com/vi/${video.id}/hqdefault.jpg`;
                    return (
                      <div 
                        key={video.id}
                        onClick={() => navigate(`/videos/${video.id}`)}
                        className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-all group flex flex-col h-full relative cursor-pointer"
                      >
                        <div className="relative aspect-video bg-gray-100 overflow-hidden block">
                          <img 
                            src={fallbackThumb} 
                            alt={video.title} 
                            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                          />
                          {video.duration > 0 && (
                            <div className="absolute bottom-2 right-2 bg-black/80 text-white text-[10px] font-bold px-1.5 py-0.5 rounded flex items-center">
                              {formatDuration(video.duration)}
                            </div>
                          )}
                          {video.is_short && (
                            <div className="absolute top-2 right-2 bg-indigo-600/90 text-white p-1 rounded-full shadow-xs">
                              <PlayCircle className="w-3.5 h-3.5" />
                            </div>
                          )}
                        </div>

                        <div className="p-4 flex-grow flex flex-col justify-between gap-4">
                          <div className="space-y-1">
                            <h3 className="font-bold text-gray-900 leading-snug line-clamp-2 group-hover:text-indigo-600 transition-colors" title={video.title}>
                              {video.title}
                            </h3>
                          </div>
                          
                          <div className="flex justify-between items-center text-[10px] text-gray-500 font-bold">
                            <span>{formatNumber(video.view_count)} views</span>
                            {video.has_transcript && (
                              <span className="bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded font-bold uppercase tracking-wider">
                                CC
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Library Channel Results Grid */}
              {modeParam === 'library' && typeParam === 'channel' && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {resultsList.map((chan) => (
                    <div 
                      key={chan.id}
                      onClick={() => navigate(`/channels/${chan.id}`)}
                      className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 flex flex-col items-center text-center justify-between gap-4 hover:shadow-md transition-all cursor-pointer group"
                    >
                      <div className="flex flex-col items-center gap-3">
                        <img 
                          src={chan.avatar_url || 'https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?auto=format&fit=crop&w=120&h=120&q=80'} 
                          alt={chan.display_name} 
                          className="w-20 h-20 rounded-full object-cover border border-gray-100 shadow-sm transition-transform duration-300 group-hover:scale-105"
                        />
                        <div>
                          <h3 className="font-bold text-gray-900 text-base leading-tight group-hover:text-indigo-600 transition-colors line-clamp-1">
                            {chan.display_name}
                          </h3>
                          {chan.handle && <p className="text-xs text-gray-400 font-semibold mt-0.5">{chan.handle}</p>}
                        </div>
                      </div>
                      <div className="flex justify-around w-full border-y border-gray-50 py-3 text-xs">
                        {chan.subscriber_count > 0 && (
                          <div className="flex flex-col items-center">
                            <span className="font-bold text-gray-800">{formatNumber(chan.subscriber_count)}</span>
                            <span className="text-[10px] text-gray-400 font-semibold uppercase">Subs</span>
                          </div>
                        )}
                        {chan.video_count > 0 && (
                          <div className="flex flex-col items-center">
                            <span className="font-bold text-gray-800">{formatNumber(chan.video_count)}</span>
                            <span className="text-[10px] text-gray-400 font-semibold uppercase">Videos</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Library Transcript Search Results List (Special Row layout) */}
              {modeParam === 'library' && typeParam === 'transcript' && (
                <div className="space-y-4">
                  {resultsList.map((res, idx) => {
                    const fallbackThumb = res.thumbnail_url?.startsWith('/') 
                      ? `http://localhost:5000${res.thumbnail_url}` 
                      : res.thumbnail_url || `https://i.ytimg.com/vi/${res.video_id}/hqdefault.jpg`;
                    return (
                      <div 
                        key={idx}
                        onClick={() => navigate(`/videos/${res.video_id}?t=${res.timestamp}`)}
                        className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4 hover:shadow-md transition-all flex items-start gap-4 cursor-pointer group"
                      >
                        {/* 60x34 Thumbnail */}
                        <div className="w-[60px] h-[34px] rounded overflow-hidden flex-shrink-0 bg-gray-100 shadow-xs border border-gray-150">
                          <img 
                            src={fallbackThumb} 
                            alt={res.video_title} 
                            className="w-full h-full object-cover"
                          />
                        </div>
                        
                        {/* Meta and excerpt */}
                        <div className="flex-grow space-y-1.5">
                          <div className="flex flex-wrap items-baseline gap-2">
                            <h4 className="font-bold text-gray-900 text-sm leading-snug line-clamp-1 group-hover:text-indigo-600 transition-all">
                              {res.video_title}
                            </h4>
                            <span className="text-gray-400 text-xs font-semibold">•</span>
                            <span className="text-gray-500 text-xs font-medium">{res.channel_name}</span>
                          </div>

                          {/* Timed Segment Highlighting */}
                          <div className="bg-gray-50 rounded-xl px-4 py-2 border border-gray-100 text-xs text-gray-600 leading-relaxed font-mono">
                            {/* Render raw html from excerpt containing brackets highlights */}
                            <span 
                              dangerouslySetInnerHTML={{
                                __html: res.excerpt.replace(/\[(.*?)\]/g, '<mark class="bg-yellow-100 border-b-2 border-yellow-300 px-0.5 rounded text-yellow-900 font-bold">$1</mark>')
                              }}
                            />
                          </div>

                          <div className="flex items-center gap-1.5 text-[10px] font-bold text-indigo-600 uppercase tracking-wider">
                            <Clock className="w-3.5 h-3.5" />
                            <span>Timestamp: {res.timestamp_formatted}</span>
                            <span className="text-gray-300 font-medium font-sans">|</span>
                            <span className="hover:underline flex items-center gap-0.5">
                              Jump to timestamp ↗
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Pagination Controls (Library Mode Only) */}
              {modeParam === 'library' && resultsCount > 20 && (
                <div className="flex justify-center items-center gap-2 pt-6">
                  <button
                    type="button"
                    disabled={pageParam <= 1}
                    onClick={() => setSearchParams(prev => {
                      const next = new URLSearchParams(prev);
                      next.set('page', String(pageParam - 1));
                      return next;
                    })}
                    className="px-4 py-2 border border-gray-200 rounded-xl text-xs font-semibold hover:bg-gray-50 disabled:opacity-50 disabled:pointer-events-none transition-colors"
                  >
                    Previous
                  </button>
                  <span className="text-xs text-gray-500 font-bold">
                    Page {pageParam} of {Math.ceil(resultsCount / 20)}
                  </span>
                  <button
                    type="button"
                    disabled={pageParam >= Math.ceil(resultsCount / 20)}
                    onClick={() => setSearchParams(prev => {
                      const next = new URLSearchParams(prev);
                      next.set('page', String(pageParam + 1));
                      return next;
                    })}
                    className="px-4 py-2 border border-gray-200 rounded-xl text-xs font-semibold hover:bg-gray-50 disabled:opacity-50 disabled:pointer-events-none transition-colors"
                  >
                    Next
                  </button>
                </div>
              )}

            </div>
          )}
        </div>
      )}

      {/* Database Search History Panel */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-xs overflow-hidden mt-12">
        <button
          type="button"
          onClick={() => {
            setIsHistoryOpen(!isHistoryOpen);
            if (!isHistoryOpen) refetchHistory();
          }}
          className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-50 font-bold text-gray-700 text-sm transition-all"
        >
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-indigo-500" />
            <span>Recent Search History</span>
          </div>
          {isHistoryOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {isHistoryOpen && (
          <div className="border-t border-gray-100 overflow-x-auto animate-slide-down">
            {historyLogs.length === 0 ? (
              <p className="p-6 text-center text-sm text-gray-400">No recent queries in search cache.</p>
            ) : (
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100 font-bold uppercase text-[10px] text-gray-400">
                    <th className="px-6 py-3">Query</th>
                    <th className="px-6 py-3">Type</th>
                    <th className="px-6 py-3">Results</th>
                    <th className="px-6 py-3">Searched At</th>
                    <th className="px-6 py-3">Cache Status</th>
                    <th className="px-6 py-3">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 text-gray-700 font-medium">
                  {historyLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-50/50">
                      <td className="px-6 py-3.5 font-semibold text-gray-900 max-w-[200px] truncate" title={log.query}>
                        {log.query}
                      </td>
                      <td className="px-6 py-3.5">
                        <span className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded text-[10px] font-bold uppercase">
                          {log.search_type}
                        </span>
                      </td>
                      <td className="px-6 py-3.5">{log.result_count ?? 0}</td>
                      <td className="px-6 py-3.5">{formatRelativeTime(log.searched_at)}</td>
                      <td className="px-6 py-3.5">
                        {log.is_expired ? (
                          <span className="bg-gray-100 text-gray-400 px-2 py-0.5 rounded text-[10px] font-bold uppercase">
                            Expired
                          </span>
                        ) : (
                          <span className="bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded text-[10px] font-bold uppercase">
                            Cached
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-3.5">
                        <button
                          type="button"
                          onClick={() => {
                            setSearchQuery(log.query);
                            setSearchParams({
                              q: log.query,
                              mode: log.search_type === 'video' || log.search_type === 'channel' || log.search_type === 'playlist' ? 'youtube' : 'library',
                              type: log.search_type,
                              page: 1
                            });
                          }}
                          className="text-indigo-600 hover:text-indigo-800 font-bold hover:underline"
                        >
                          Run Query
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>

    </div>
  );
}
