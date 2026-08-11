import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  DownloadCloud, Play, Square, RefreshCw, Trash2, Folder,
  Download, FileVideo, Music, FileText, Image, Search,
  AlertCircle, CheckCircle, Clock, Loader2, Info
} from 'lucide-react';
import {
  getDownloads, startDownload, cancelDownload, retryDownload, deleteDownload, openFileLocation
} from '../api/downloads';
import { API_BASE_URL } from '../constants';
import { apiClient } from '../client';

export default function Downloader() {
  const queryClient = useQueryClient();

  // Form State
  const [url, setUrl] = useState('');
  const [downloadType, setDownloadType] = useState('video'); // video, audio, subtitle, thumbnail
  const [quality, setQuality] = useState('best');
  const [formatOption, setFormatOption] = useState('mp4');
  const [subtitleLang, setSubtitleLang] = useState('en');

  // Preview & Validation State
  const [videoPreview, setVideoPreview] = useState(null);
  const [previewError, setPreviewError] = useState('');
  const [urlValidationError, setUrlValidationError] = useState('');
  const [notification, setNotification] = useState(null); // { type: 'success'|'warning'|'error', message, historyId }

  // Filter/Search State
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');

  // Confirmation state for deleting & cancelling
  const [deleteModal, setDeleteModal] = useState(null); // holds download item to delete
  const [deleteFileFromDisk, setDeleteFileFromDisk] = useState(false);
  const [cancelConfirmModal, setCancelConfirmModal] = useState(null); // holds download item to cancel
  const [cancelledTransitions, setCancelledTransitions] = useState({}); // { [id]: timestamp }
  const [highlightedId, setHighlightedId] = useState(null);

  // Fetch downloads list with smart polling
  const { data: downloads = [], isLoading } = useQuery({
    queryKey: ['downloads'],
    queryFn: getDownloads,
    refetchInterval: (query) => {
      const hasActive = query.state.data?.some(d => d.status === 'pending' || d.status === 'downloading');
      return hasActive ? 1500 : 5000;
    }
  });

  // Helper to extract Video ID
  const extractVideoId = (value) => {
    if (!value || typeof value !== 'string') return null;
    const trimmed = value.trim();
    const patterns = [
      /(?:v=|\/v\/|embed\/|shorts\/|youtu\.be\/|\/v=)([^#\&\?]{11})/,
      /^[a-zA-Z0-9_-]{11}$/
    ];
    for (const pattern of patterns) {
      const match = trimmed.match(pattern);
      if (match) {
        return match[1] || match[0];
      }
    }
    return null;
  };

  const handleUrlChange = (val) => {
    setUrl(val);
    if (urlValidationError) setUrlValidationError('');
    if (!val.trim()) {
      setVideoPreview(null);
      setPreviewError('');
    }
  };

  const handleUrlBlur = async () => {
    const trimmed = url.trim();
    if (!trimmed) {
      setUrlValidationError('');
      setVideoPreview(null);
      return;
    }

    const videoId = extractVideoId(trimmed);
    if (!videoId) {
      setUrlValidationError('Please enter a valid YouTube Video URL or 11-character Video ID.');
      setVideoPreview(null);
      return;
    }

    setUrlValidationError('');

    try {
      const { data } = await apiClient.get(`/videos/${videoId}`);
      setVideoPreview(data);
      setPreviewError('');
    } catch (err) {
      setVideoPreview(null);
      if (err.response?.status !== 404) {
        setPreviewError('Failed to fetch video details.');
      }
    }
  };

  // Mutations
  const startDownloadMutation = useMutation({
    mutationFn: startDownload,
    onSuccess: (data) => {
      setUrl('');
      setVideoPreview(null);
      setNotification({
        type: 'success',
        message: 'Download queued successfully! Your stream will start downloading shortly.'
      });
      setTimeout(() => setNotification(null), 5000);
      queryClient.invalidateQueries({ queryKey: ['downloads'] });

      // Automatically trigger browser download using an invisible iframe
      if (data && data.history_id) {
        const iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        iframe.src = `${API_BASE_URL}/downloads/${data.history_id}/file`;
        document.body.appendChild(iframe);
        setTimeout(() => {
          document.body.removeChild(iframe);
        }, 10000);
      }
    },
    onError: (err) => {
      const status = err.response?.status;
      const data = err.response?.data;
      if (status === 409) {
        setNotification({
          type: 'warning',
          message: 'Already downloaded — ',
          historyId: data?.history_id
        });
      } else if (status === 507) {
        setNotification({
          type: 'error',
          message: 'Insufficient disk space. Please clean up files.'
        });
      } else {
        setNotification({
          type: 'error',
          message: data?.message || err.message || 'Failed to queue download.'
        });
      }
    }
  });

  const cancelDownloadMutation = useMutation({
    mutationFn: cancelDownload,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['downloads'] });
    }
  });

  const retryDownloadMutation = useMutation({
    mutationFn: retryDownload,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['downloads'] });
    }
  });

  const deleteDownloadMutation = useMutation({
    mutationFn: ({ id, deleteFile }) => deleteDownload(id, deleteFile),
    onSuccess: () => {
      setDeleteModal(null);
      setDeleteFileFromDisk(false);
      queryClient.invalidateQueries({ queryKey: ['downloads'] });
    }
  });

  const openFolderMutation = useMutation({
    mutationFn: openFileLocation,
    onError: (err) => {
      alert(err.response?.data?.error || 'Failed to open file location');
    }
  });

  const handleQueueDownload = (e) => {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) return;

    const videoId = extractVideoId(trimmed);
    if (!videoId) {
      setUrlValidationError('Please enter a valid YouTube Video URL or 11-character Video ID.');
      return;
    }
    setUrlValidationError('');

    let payloadQuality = quality;
    let payloadFormat = formatOption;

    if (downloadType === 'subtitle') {
      payloadQuality = subtitleLang;
      payloadFormat = formatOption; // srt or vtt
    } else if (downloadType === 'thumbnail') {
      payloadQuality = 'default';
      payloadFormat = 'jpg';
    }

    const downloadUrl = `${API_BASE_URL}/videos/${videoId}/download?quality=${payloadQuality}&format=${payloadFormat}&download_type=${downloadType}`;
    
    setNotification({
      type: 'success',
      message: 'Download started! Your browser will download the file directly.'
    });
    setTimeout(() => setNotification(null), 6000);
    
    // Use a hidden anchor tag to trigger native browser download.
    // Unlike an iframe with a 15s timeout, this keeps the connection alive
    // for the entire duration of the download, supporting files of any size.
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    setUrl('');
    setVideoPreview(null);
    
    setTimeout(() => {
      queryClient.invalidateQueries({ queryKey: ['downloads'] });
    }, 1200);
  };

  const handleViewInHistory = (historyId) => {
    setNotification(null);
    setHighlightedId(historyId);
    
    setTimeout(() => {
      const element = document.getElementById(`download-row-${historyId}`);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 100);

    setTimeout(() => {
      setHighlightedId(null);
    }, 4000);
  };

  const getEstimatedSizeDisplay = () => {
    if (!videoPreview || !videoPreview.duration) return null;
    const durationMinutes = videoPreview.duration / 60;
    if (downloadType === 'video') {
      let mbPerMin = 60;
      if (quality === '720p') mbPerMin = 30;
      else if (quality === '480p') mbPerMin = 11.25;
      const sizeMb = durationMinutes * mbPerMin;
      return sizeMb >= 1000 ? `~${(sizeMb / 1000).toFixed(1)} GB` : `~${Math.round(sizeMb)} MB`;
    } else if (downloadType === 'audio') {
      let mbPerMin = 1.4;
      if (quality === '320k') mbPerMin = 2.4;
      else if (quality === '256k') mbPerMin = 1.92;
      else if (quality === '128k') mbPerMin = 0.96;
      const sizeMb = durationMinutes * mbPerMin;
      return `~${sizeMb.toFixed(1)} MB`;
    }
    return null;
  };

  // Filter lists including cancelled transitions
  const activeDownloads = downloads.filter(d => {
    if (d.status === 'pending' || d.status === 'downloading') return true;
    const cancelTime = cancelledTransitions[d.id];
    if (cancelTime && Date.now() - cancelTime < 2000) return true;
    return false;
  });

  const finishedDownloads = downloads.filter(d => {
    const cancelTime = cancelledTransitions[d.id];
    if (cancelTime && Date.now() - cancelTime < 2000) return false;
    return d.status !== 'pending' && d.status !== 'downloading';
  });

  const filteredHistory = finishedDownloads.filter(d => {
    const matchesSearch = d.video_title?.toLowerCase().includes(searchTerm.toLowerCase()) || d.video_id.includes(searchTerm);
    const matchesStatus = statusFilter === 'all' || d.status === statusFilter;
    const matchesType = typeFilter === 'all' || d.download_type === typeFilter;
    return matchesSearch && matchesStatus && matchesType;
  });

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'complete':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800"><CheckCircle className="w-3.5 h-3.5 mr-1" /> Complete</span>;
      case 'failed':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800"><AlertCircle className="w-3.5 h-3.5 mr-1" /> Failed</span>;
      case 'cancelled':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800"><Clock className="w-3.5 h-3.5 mr-1" /> Cancelled</span>;
      default:
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">Pending</span>;
    }
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'video':
        return <FileVideo className="w-4 h-4 text-indigo-500" />;
      case 'audio':
        return <Music className="w-4 h-4 text-emerald-500" />;
      case 'subtitle':
        return <FileText className="w-4 h-4 text-amber-500" />;
      case 'thumbnail':
        return <Image className="w-4 h-4 text-rose-500" />;
      default:
        return <DownloadCloud className="w-4 h-4 text-gray-500" />;
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight flex items-center">
          <DownloadCloud className="w-8 h-8 mr-3 text-indigo-600" />
          Video Downloader
        </h1>
        <p className="text-gray-500 mt-2">Queue video, audio, subtitles, or thumbnail downloads in the background.</p>
      </div>

      {/* Quick Download Form */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 md:p-8 animate-in fade-in duration-300">
        <h2 className="text-xl font-bold text-gray-900 mb-6">Queue New Download</h2>

        {/* Notifications Banner */}
        {notification && (
          <div className={`mb-6 p-4 rounded-xl border flex items-start space-x-3 animate-in fade-in slide-in-from-top-2 duration-300 ${
            notification.type === 'success' ? 'bg-emerald-50 border-emerald-200 text-emerald-800' :
            notification.type === 'warning' ? 'bg-amber-50 border-amber-200 text-amber-800' :
            'bg-rose-50 border-rose-200 text-rose-800'
          }`}>
            <AlertCircle className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
              notification.type === 'success' ? 'text-emerald-600' :
              notification.type === 'warning' ? 'text-amber-600' :
              'text-rose-600'
            }`} />
            <div className="text-sm font-semibold">
              <span>{notification.message}</span>
              {notification.type === 'warning' && notification.historyId && (
                <button
                  type="button"
                  onClick={() => handleViewInHistory(notification.historyId)}
                  className="underline text-amber-900 hover:text-amber-950 font-bold focus:outline-none ml-1 transition-colors"
                >
                  View in history
                </button>
              )}
            </div>
          </div>
        )}

        <form onSubmit={handleQueueDownload} className="space-y-6">
          <div className="grid grid-cols-1 gap-y-6">
            {/* URL Input */}
            <div>
              <label htmlFor="url" className="block text-sm font-semibold text-gray-700 mb-2">
                YouTube Video URL or Video ID
              </label>
              <input
                type="text"
                id="url"
                required
                placeholder="https://www.youtube.com/watch?v=..."
                value={url}
                onChange={(e) => handleUrlChange(e.target.value)}
                onBlur={handleUrlBlur}
                className={`w-full px-4 py-3 rounded-xl border focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 text-gray-900 shadow-sm transition-colors ${
                  urlValidationError ? 'border-red-500 focus:ring-red-500/20 focus:border-red-500' : 'border-gray-300'
                }`}
              />
              {urlValidationError && (
                <p className="text-red-600 text-xs font-semibold mt-2.5 flex items-center animate-in fade-in duration-200">
                  <AlertCircle className="w-3.5 h-3.5 mr-1" />
                  {urlValidationError}
                </p>
              )}

              {/* Video metadata preview stub */}
              {videoPreview && (
                <div className="mt-4 p-3.5 bg-indigo-50/40 border border-indigo-100 rounded-xl flex items-center space-x-3.5 animate-in fade-in duration-300">
                  <div className="w-24 aspect-video bg-gray-200 rounded-lg overflow-hidden flex-shrink-0 border border-indigo-100 shadow-sm">
                    <img src={videoPreview.thumbnail_url} alt="" className="w-full h-full object-cover" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-bold text-indigo-600 uppercase tracking-wide">Video Detected</p>
                    <p className="text-sm font-semibold text-gray-900 truncate mt-0.5">{videoPreview.title}</p>
                    <p className="text-xs text-gray-500 mt-0.5">Duration: {Math.floor(videoPreview.duration / 60)}m {videoPreview.duration % 60}s</p>
                  </div>
                </div>
              )}
            </div>

            {/* Type Selector */}
            <div>
              <span className="block text-sm font-semibold text-gray-700 mb-3">Download Type</span>
              <div className="flex flex-wrap gap-4">
                {[
                  { id: 'video', label: '🎬 Video', icon: FileVideo },
                  { id: 'audio', label: '🎵 Audio', icon: Music },
                  { id: 'thumbnail', label: '🖼️ Thumbnail', icon: Image }
                ].map((type) => (
                  <button
                    key={type.id}
                    type="button"
                    onClick={() => {
                      setDownloadType(type.id);
                      if (type.id === 'video') {
                        setFormatOption('mp4');
                      } else if (type.id === 'audio') {
                        setFormatOption('mp3');
                      }
                    }}
                    className={`flex items-center space-x-2 px-5 py-3 rounded-xl border text-sm font-medium transition-all ${downloadType === type.id
                      ? 'border-indigo-600 bg-indigo-50/50 text-indigo-700 font-semibold'
                      : 'border-gray-200 hover:bg-gray-50 text-gray-600'
                      }`}
                  >
                    <type.icon className="w-4 h-4" />
                    <span>{type.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Quality and Format Row (Contextual) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-gray-50/50 p-4 rounded-2xl border border-gray-100">
              {downloadType === 'video' && (
                <>
                  <div>
                    <label htmlFor="quality" className="block text-sm font-medium text-gray-600 mb-2">Video Quality</label>
                    <select
                      id="quality"
                      value={quality}
                      onChange={(e) => setQuality(e.target.value)}
                      className="w-full px-3 py-2 bg-white rounded-lg border border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm text-gray-700 shadow-sm"
                    >
                      <option value="best">Best Available Quality</option>
                      <option value="1080p">1080p (Full HD)</option>
                      <option value="720p">720p (HD)</option>
                      <option value="480p">480p (SD)</option>
                    </select>
                  </div>
                  <div>
                    <label htmlFor="format" className="block text-sm font-medium text-gray-600 mb-2">Container Format</label>
                    <select
                      id="format"
                      value={formatOption}
                      onChange={(e) => setFormatOption(e.target.value)}
                      className="w-full px-3 py-2 bg-white rounded-lg border border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm text-gray-700 shadow-sm"
                    >
                      <option value="mp4">MP4 (Recommended)</option>
                      <option value="mkv">MKV</option>
                      <option value="webm">WebM</option>
                    </select>
                  </div>
                  {videoPreview && (
                    <div className="col-span-1 sm:col-span-2 text-xs font-semibold text-gray-500 flex items-center justify-end px-1.5 mt-1 border-t border-gray-200/50 pt-2.5">
                      <Info className="w-3.5 h-3.5 mr-1 text-indigo-500" />
                      Estimated Size: <span className="text-indigo-600 font-bold ml-1">{getEstimatedSizeDisplay() || 'Unknown'}</span>
                    </div>
                  )}
                </>
              )}

              {downloadType === 'audio' && (
                <>
                  <div>
                    <label htmlFor="quality" className="block text-sm font-medium text-gray-600 mb-2">Audio Bitrate</label>
                    <select
                      id="quality"
                      value={quality}
                      onChange={(e) => setQuality(e.target.value)}
                      className="w-full px-3 py-2 bg-white rounded-lg border border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm text-gray-700 shadow-sm"
                    >
                      <option value="320k">320kbps (High)</option>
                      <option value="256k">256kbps</option>
                      <option value="192k">192kbps (Standard)</option>
                      <option value="128k">128kbps (Eco)</option>
                    </select>
                  </div>
                  <div>
                    <label htmlFor="format" className="block text-sm font-medium text-gray-600 mb-2">Audio Format</label>
                    <select
                      id="format"
                      value={formatOption}
                      onChange={(e) => setFormatOption(e.target.value)}
                      className="w-full px-3 py-2 bg-white rounded-lg border border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm text-gray-700 shadow-sm"
                    >
                      <option value="mp3">MP3</option>
                      <option value="m4a">M4A (AAC)</option>
                      <option value="wav">WAV (Lossless)</option>
                    </select>
                  </div>
                  {videoPreview && (
                    <div className="col-span-1 sm:col-span-2 text-xs font-semibold text-gray-500 flex items-center justify-end px-1.5 mt-1 border-t border-gray-200/50 pt-2.5">
                      <Info className="w-3.5 h-3.5 mr-1 text-indigo-500" />
                      Estimated Size: <span className="text-indigo-600 font-bold ml-1">{getEstimatedSizeDisplay() || 'Unknown'}</span>
                    </div>
                  )}
                </>
              )}


              {downloadType === 'thumbnail' && (
                <div className="col-span-2 text-sm text-gray-500 flex items-center justify-center p-2 font-medium">
                  <Info className="w-4 h-4 mr-2 text-indigo-500" /> Downloads the high-resolution maxresdefault thumbnail image directly.
                </div>
              )}
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              className="w-full sm:w-auto px-6 py-3.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-base font-semibold transition-colors shadow-sm flex items-center justify-center"
            >
              <Download className="w-5 h-5 mr-2" />
              Download
            </button>
          </div>
        </form>
      </div>

      {/* Active Downloads Panel */}
      {activeDownloads.length > 0 && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center">
            <Loader2 className="w-5 h-5 mr-2 text-indigo-600 animate-spin" />
            Active Downloads ({activeDownloads.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {activeDownloads.map((dl) => {
              const isDlCancelled = dl.status === 'cancelled' || !!cancelledTransitions[dl.id];
              return (
                <div key={dl.id} className="p-4 rounded-xl border border-gray-200 flex flex-col sm:flex-row items-center sm:items-start space-y-3 sm:space-y-0 sm:space-x-4 animate-in fade-in duration-300">
                  {/* Thumbnail / Icon */}
                  <div className="w-24 h-14 bg-gray-100 rounded-lg overflow-hidden flex-shrink-0 flex items-center justify-center border border-gray-200 shadow-sm">
                    {dl.thumbnail_url ? (
                      <img src={dl.thumbnail_url} alt="" className="w-full h-full object-cover" />
                    ) : (
                      getTypeIcon(dl.download_type)
                    )}
                  </div>
                  {/* Details */}
                  <div className="flex-1 w-full min-w-0 space-y-2">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="text-sm font-semibold text-gray-900 truncate pr-2 max-w-[200px] sm:max-w-xs">{dl.video_title}</h3>
                        <p className="text-xs text-gray-500 uppercase mt-0.5 tracking-wider font-medium flex items-center">
                          {getTypeIcon(dl.download_type)}
                          <span className="ml-1">{dl.download_type} · {dl.quality}</span>
                        </p>
                      </div>
                      <button
                        onClick={() => setCancelConfirmModal(dl)}
                        disabled={isDlCancelled}
                        className="text-xs font-semibold text-red-600 hover:text-red-800 transition-colors bg-red-50 hover:bg-red-100 px-2.5 py-1 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {isDlCancelled ? 'Cancelling...' : 'Cancel'}
                      </button>
                    </div>

                    {/* Progress bar */}
                    <div className="space-y-1">
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all duration-300 ${
                            isDlCancelled
                              ? 'bg-gray-400 w-full animate-pulse'
                              : dl.status === 'pending'
                              ? 'bg-blue-400 w-1/12 animate-pulse'
                              : 'bg-indigo-600'
                          }`}
                          style={{
                            width: isDlCancelled
                              ? '100%'
                              : dl.status === 'pending'
                              ? '8%'
                              : `${dl.progress_percent}%`
                          }}
                        ></div>
                      </div>
                      <div className="flex justify-between text-xs text-gray-500 font-medium">
                        <span>
                          {isDlCancelled
                            ? 'Cancelled'
                            : dl.status === 'pending'
                            ? 'Queued'
                            : `${dl.progress_percent}%`}
                        </span>
                        {dl.status === 'downloading' && !isDlCancelled && dl.speed && (
                          <span>{dl.speed} · ETA {dl.eta}</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Download History Section */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">Download History</h2>

          {/* Filters */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6">
            <div className="relative">
              <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
              <input
                type="text"
                placeholder="Search history..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>
            <div>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="all">All Types</option>
                <option value="video">Video</option>
                <option value="audio">Audio</option>
                <option value="subtitle">Subtitles</option>
                <option value="thumbnail">Thumbnail</option>
              </select>
            </div>
            <div>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="all">All Statuses</option>
                <option value="complete">Complete</option>
                <option value="failed">Failed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
          </div>
        </div>

        {/* History Table */}
        {isLoading ? (
          <div className="p-8 text-center text-gray-500"><Loader2 className="w-8 h-8 animate-spin mx-auto mb-2 text-indigo-600" /> Loading history...</div>
        ) : filteredHistory.length === 0 ? (
          <div className="p-12 text-center text-gray-400">
            <DownloadCloud className="w-12 h-12 mx-auto mb-3 text-gray-300 animate-bounce" />
            <p className="text-base font-semibold">No downloads found</p>
            <p className="text-sm text-gray-400 mt-1">Start a download using the form above.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Thumbnail</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Title</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Type</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Quality/Format</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Size</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Date</th>
                  <th scope="col" className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200 text-sm">
                {filteredHistory.map((item) => (
                  <tr
                    key={item.id}
                    id={`download-row-${item.id}`}
                    className={`transition-all duration-500 ${
                      item.id === highlightedId
                        ? 'bg-indigo-50 border-y-2 border-indigo-300 scale-[1.005] shadow-sm z-10 font-semibold'
                        : 'hover:bg-gray-50/50'
                    }`}
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="w-16 h-10 bg-gray-100 rounded overflow-hidden flex items-center justify-center border border-gray-200 shadow-sm">
                        {item.thumbnail_url ? (
                          <img src={item.thumbnail_url} alt="" className="w-full h-full object-cover" />
                        ) : (
                          getTypeIcon(item.download_type)
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <Link
                        to={`/videos/${item.video_id}`}
                        className="font-semibold text-indigo-600 hover:text-indigo-800 hover:underline max-w-[200px] truncate block"
                        title={item.video_title}
                      >
                        {item.video_title}
                      </Link>
                      <div className="text-xs text-gray-400 mt-0.5 font-mono">{item.video_id}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap uppercase tracking-wider text-xs font-semibold text-gray-500">
                      {item.download_type}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500 font-medium">
                      {item.quality}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500 font-medium">
                      {item.file_size_bytes ? formatBytes(item.file_size_bytes) : '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap relative group">
                      {getStatusBadge(item.status)}
                      {item.status === 'failed' && item.error_message && (
                        <div className="absolute z-10 bottom-full left-1/2 transform -translate-x-1/2 bg-slate-900 text-white text-xs rounded py-1.5 px-3 max-w-xs shadow-lg opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity whitespace-normal break-words font-medium -translate-y-1">
                          {item.error_message.slice(0, 100)}{item.error_message.length > 100 ? '...' : ''}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-400">
                      {item.created_at ? new Date(item.created_at).toLocaleDateString() : '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right space-x-1.5">
                      {item.status === 'complete' && item.file_path && (
                        <>
                          <button
                            onClick={() => openFolderMutation.mutate(item.id)}
                            title="Open file location"
                            className="inline-flex p-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-indigo-600 transition-all shadow-sm"
                          >
                            <Folder className="w-4 h-4" />
                          </button>
                          <a
                            href={`${API_BASE_URL}/downloads/${item.id}/file`}
                            download
                            title="Download file"
                            className="inline-flex p-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-indigo-600 transition-all shadow-sm"
                          >
                            <Download className="w-4 h-4" />
                          </a>
                        </>
                      )}

                      {(item.status === 'failed' || item.status === 'cancelled') && (
                        <button
                          onClick={() => {
                            const retryUrl = `${API_BASE_URL}/videos/${item.video_id}/download?quality=${item.quality}&format=${item.format}&download_type=${item.download_type}`;
                            const a = document.createElement('a');
                            a.href = retryUrl;
                            a.style.display = 'none';
                            document.body.appendChild(a);
                            a.click();
                            document.body.removeChild(a);
                            setTimeout(() => {
                              queryClient.invalidateQueries({ queryKey: ['downloads'] });
                            }, 1200);
                          }}
                          title="Retry download"
                          className="inline-flex p-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-indigo-600 transition-all shadow-sm"
                        >
                          <RefreshCw className="w-4 h-4" />
                        </button>
                      )}

                      <button
                        onClick={() => setDeleteModal(item)}
                        title="Delete download record"
                        className="inline-flex p-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-red-600 hover:border-red-200 transition-all shadow-sm"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {deleteModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/40 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full border border-gray-100 overflow-hidden transform transition-all p-6">
            <h3 className="text-lg font-bold text-gray-900">Delete Download Record</h3>
            <p className="text-sm text-gray-500 mt-2">
              Are you sure you want to delete the record for: <span className="font-semibold text-gray-800">{deleteModal.video_title}</span>?
            </p>

            {deleteModal.status === 'complete' && deleteModal.file_path && (
              <div className="mt-4 flex items-center">
                <input
                  type="checkbox"
                  id="delete-disk-file"
                  checked={deleteFileFromDisk}
                  onChange={(e) => setDeleteFileFromDisk(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
                <label htmlFor="delete-disk-file" className="ml-2 block text-sm font-semibold text-gray-700 select-none">
                  Also delete file from disk ({formatBytes(deleteModal.file_size_bytes)})
                </label>
              </div>
            )}

            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => {
                  setDeleteModal(null);
                  setDeleteFileFromDisk(false);
                }}
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteDownloadMutation.mutate({ id: deleteModal.id, deleteFile: deleteFileFromDisk })}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-semibold transition-colors shadow-sm"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Cancel Confirmation Modal */}
      {cancelConfirmModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/40 flex items-center justify-center p-4 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full border border-gray-100 overflow-hidden transform transition-all p-6">
            <h3 className="text-lg font-bold text-gray-900 flex items-center">
              <AlertCircle className="w-5 h-5 text-red-500 mr-2" />
              Cancel Download
            </h3>
            <p className="text-sm text-gray-500 mt-2">
              Are you sure you want to cancel the download for: <span className="font-semibold text-gray-800">{cancelConfirmModal.video_title}</span>? Partial files will be deleted.
            </p>
            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => setCancelConfirmModal(null)}
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Go Back
              </button>
              <button
                onClick={() => {
                  const id = cancelConfirmModal.id;
                  cancelDownloadMutation.mutate(id);
                  setCancelledTransitions(prev => ({ ...prev, [id]: Date.now() }));
                  setCancelConfirmModal(null);
                }}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-semibold transition-colors shadow-sm"
              >
                Confirm Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
