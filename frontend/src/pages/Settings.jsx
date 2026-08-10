import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Settings as SettingsIcon, Download, Sliders, PlayCircle, ShieldAlert,
  Database, RefreshCw, CheckCircle2, AlertCircle, FileText, Trash2, Check, Upload, Info
} from 'lucide-react';
import {
  getSettings, updateSettings, uploadCookiesFile, deleteCookiesFile, testCookiesFile
} from '../api/settings';

export default function Settings() {
  const queryClient = useQueryClient();

  // Load Settings and DB Stats
  const { data, isLoading, isError } = useQuery({
    queryKey: ['settings'],
    queryFn: getSettings
  });

  // Local Form states (segmented per card)
  const [downloadForm, setDownloadForm] = useState({
    default_video_quality: 'best',
    default_audio_format: 'mp3',
    default_audio_quality: '192k',
    max_concurrent_downloads: 2
  });

  const [extractionForm, setExtractionForm] = useState({
    auto_extract_transcript: false,
    auto_extract_comments: false,
    auto_extract_thumbnail: true,
    max_comments_per_video: 500
  });

  const [ytdlpForm, setYtdlpForm] = useState({
    ytdlp_player_client: 'ios',
    ytdlp_rate_limit: '500K',
    ytdlp_proxy: '',
    cookies_file_path: ''
  });

  const [monitoringForm, setMonitoringForm] = useState({
    rss_poll_interval_minutes: 60,
    snapshot_enabled: true
  });

  // Notification States
  const [saveStatus, setSaveStatus] = useState({}); // { [section]: 'success' | 'error' | 'loading' }
  const [cookieStatus, setCookieStatus] = useState(null); // { type: 'success'|'error', message }

  // Sync DB settings to local state when fetched
  useEffect(() => {
    if (data?.settings) {
      const s = data.settings;
      setDownloadForm({
        default_video_quality: s.default_video_quality || 'best',
        default_audio_format: s.default_audio_format || 'mp3',
        default_audio_quality: s.default_audio_quality || '192k',
        max_concurrent_downloads: s.max_concurrent_downloads || 2
      });
      setExtractionForm({
        auto_extract_transcript: !!s.auto_extract_transcript,
        auto_extract_comments: !!s.auto_extract_comments,
        auto_extract_thumbnail: !!s.auto_extract_thumbnail,
        max_comments_per_video: s.max_comments_per_video || 500
      });
      setYtdlpForm({
        ytdlp_player_client: s.ytdlp_player_client || 'ios',
        ytdlp_rate_limit: s.ytdlp_rate_limit || '500K',
        ytdlp_proxy: s.ytdlp_proxy || '',
        cookies_file_path: s.cookies_file_path || ''
      });
      setMonitoringForm({
        rss_poll_interval_minutes: s.rss_poll_interval_minutes || 60,
        snapshot_enabled: !!s.snapshot_enabled
      });
    }
  }, [data]);

  // Mutations
  const updateSettingsMutation = useMutation({
    mutationFn: updateSettings,
    onSuccess: (_, variables) => {
      // Invalidate settings query
      queryClient.invalidateQueries({ queryKey: ['settings'] });
      // Identify which section triggered the update based on payload keys
      const keys = Object.keys(variables);
      let section = 'download';
      if (keys.includes('auto_extract_transcript')) section = 'extraction';
      else if (keys.includes('ytdlp_player_client')) section = 'ytdlp';
      else if (keys.includes('rss_poll_interval_minutes')) section = 'monitoring';

      setSaveStatus(prev => ({ ...prev, [section]: 'success' }));
      setTimeout(() => {
        setSaveStatus(prev => ({ ...prev, [section]: null }));
      }, 3000);
    },
    onError: (err, variables) => {
      const keys = Object.keys(variables);
      let section = 'download';
      if (keys.includes('auto_extract_transcript')) section = 'extraction';
      else if (keys.includes('ytdlp_player_client')) section = 'ytdlp';
      else if (keys.includes('rss_poll_interval_minutes')) section = 'monitoring';

      setSaveStatus(prev => ({ ...prev, [section]: 'error' }));
      setTimeout(() => {
        setSaveStatus(prev => ({ ...prev, [section]: null }));
      }, 3000);
    }
  });

  const uploadCookiesMutation = useMutation({
    mutationFn: uploadCookiesFile,
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
      setCookieStatus({ type: 'success', message: 'Cookies uploaded successfully!' });
      setTimeout(() => setCookieStatus(null), 5000);
    },
    onError: (err) => {
      setCookieStatus({ type: 'error', message: err.response?.data?.error || 'Failed to upload cookies file.' });
      setTimeout(() => setCookieStatus(null), 5000);
    }
  });

  const deleteCookiesMutation = useMutation({
    mutationFn: deleteCookiesFile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
      setCookieStatus({ type: 'success', message: 'Cookies deleted successfully.' });
      setTimeout(() => setCookieStatus(null), 5000);
    },
    onError: (err) => {
      setCookieStatus({ type: 'error', message: err.response?.data?.error || 'Failed to delete cookies file.' });
      setTimeout(() => setCookieStatus(null), 5000);
    }
  });

  const testCookiesMutation = useMutation({
    mutationFn: testCookiesFile,
    onSuccess: (res) => {
      if (res.valid) {
        setCookieStatus({ type: 'success', message: 'Cookies file is valid and verified!' });
      } else {
        setCookieStatus({ type: 'error', message: res.message || 'Cookies format check failed.' });
      }
      setTimeout(() => setCookieStatus(null), 5000);
    },
    onError: (err) => {
      setCookieStatus({ type: 'error', message: err.response?.data?.message || 'Cookies verification failed.' });
      setTimeout(() => setCookieStatus(null), 5000);
    }
  });

  const handleSaveSection = (section, payload) => {
    setSaveStatus(prev => ({ ...prev, [section]: 'loading' }));
    updateSettingsMutation.mutate(payload);
  };

  const handleCookieUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      uploadCookiesMutation.mutate(file);
    }
  };

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <RefreshCw className="w-10 h-10 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-8 text-center text-red-500 bg-red-50 rounded-2xl border border-red-100 max-w-2xl mx-auto">
        <AlertCircle className="w-12 h-12 mx-auto mb-3 text-red-400" />
        <h3 className="text-lg font-bold">Failed to load platform settings</h3>
        <p className="text-sm mt-1 text-red-400">Please make sure the backend Flask service is active.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-5xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500 pb-16">
      
      {/* Header */}
      <div>
        <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight flex items-center">
          <SettingsIcon className="w-8 h-8 mr-3 text-indigo-600 animate-pulse" />
          Platform Settings
        </h1>
        <p className="text-gray-500 mt-2">Manage download options, automation steps, scraper proxies, and scheduler parameters.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        
        {/* 1. Download Settings Card */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-6 pb-2 border-b border-gray-100">
              <h2 className="text-lg font-bold text-gray-900 flex items-center">
                <Download className="w-5 h-5 mr-2 text-indigo-600" />
                Download Configurations
              </h2>
              {saveStatus['download'] === 'success' && <span className="text-xs text-emerald-600 font-semibold flex items-center"><Check className="w-3.5 h-3.5 mr-0.5" /> Saved</span>}
              {saveStatus['download'] === 'error' && <span className="text-xs text-red-600 font-semibold flex items-center"><AlertCircle className="w-3.5 h-3.5 mr-0.5" /> Error</span>}
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1.5">Default Video Quality</label>
                <select
                  value={downloadForm.default_video_quality}
                  onChange={(e) => setDownloadForm({ ...downloadForm, default_video_quality: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                >
                  <option value="best">Best Quality Available</option>
                  <option value="1080p">1080p (Full HD)</option>
                  <option value="720p">720p (HD)</option>
                  <option value="480p">480p (SD)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1.5">Default Audio Format</label>
                  <select
                    value={downloadForm.default_audio_format}
                    onChange={(e) => setDownloadForm({ ...downloadForm, default_audio_format: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  >
                    <option value="mp3">MP3</option>
                    <option value="m4a">M4A</option>
                    <option value="wav">WAV</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1.5">Default Audio Quality</label>
                  <select
                    value={downloadForm.default_audio_quality}
                    onChange={(e) => setDownloadForm({ ...downloadForm, default_audio_quality: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  >
                    <option value="320k">320kbps (High)</option>
                    <option value="256k">256kbps</option>
                    <option value="192k">192kbps (Standard)</option>
                    <option value="128k">128kbps (Eco)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1.5">Max Concurrent Downloads</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={downloadForm.max_concurrent_downloads}
                  onChange={(e) => setDownloadForm({ ...downloadForm, max_concurrent_downloads: parseInt(e.target.value) || 2 })}
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
              </div>
            </div>
          </div>

          <div className="mt-8 flex justify-end">
            <button
              onClick={() => handleSaveSection('download', downloadForm)}
              disabled={saveStatus['download'] === 'loading'}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-semibold transition-colors disabled:opacity-50 flex items-center shadow-sm"
            >
              {saveStatus['download'] === 'loading' && <RefreshCw className="w-4 h-4 mr-1.5 animate-spin" />}
              Save Changes
            </button>
          </div>
        </div>

        {/* 2. Extraction Settings Card */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-6 pb-2 border-b border-gray-100">
              <h2 className="text-lg font-bold text-gray-900 flex items-center">
                <Sliders className="w-5 h-5 mr-2 text-indigo-600" />
                Metadata Extraction
              </h2>
              {saveStatus['extraction'] === 'success' && <span className="text-xs text-emerald-600 font-semibold flex items-center"><Check className="w-3.5 h-3.5 mr-0.5" /> Saved</span>}
              {saveStatus['extraction'] === 'error' && <span className="text-xs text-red-600 font-semibold flex items-center"><AlertCircle className="w-3.5 h-3.5 mr-0.5" /> Error</span>}
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                <div>
                  <span className="block text-sm font-semibold text-gray-800">Auto-extract Transcript</span>
                  <span className="block text-xs text-gray-400 mt-0.5">Generate or download video text subtitles automatically.</span>
                </div>
                <input
                  type="checkbox"
                  checked={extractionForm.auto_extract_transcript}
                  onChange={(e) => setExtractionForm({ ...extractionForm, auto_extract_transcript: e.target.checked })}
                  className="w-4.5 h-4.5 rounded text-indigo-600 border-gray-300 focus:ring-indigo-500"
                />
              </div>

              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                <div>
                  <span className="block text-sm font-semibold text-gray-800">Auto-extract Comments</span>
                  <span className="block text-xs text-gray-400 mt-0.5">Collect user comments upon parsing video metadata.</span>
                </div>
                <input
                  type="checkbox"
                  checked={extractionForm.auto_extract_comments}
                  onChange={(e) => setExtractionForm({ ...extractionForm, auto_extract_comments: e.target.checked })}
                  className="w-4.5 h-4.5 rounded text-indigo-600 border-gray-300 focus:ring-indigo-500"
                />
              </div>

              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                <div>
                  <span className="block text-sm font-semibold text-gray-800">Auto-extract Thumbnail</span>
                  <span className="block text-xs text-gray-400 mt-0.5">Cache and parse thumbnail files automatically.</span>
                </div>
                <input
                  type="checkbox"
                  checked={extractionForm.auto_extract_thumbnail}
                  onChange={(e) => setExtractionForm({ ...extractionForm, auto_extract_thumbnail: e.target.checked })}
                  className="w-4.5 h-4.5 rounded text-indigo-600 border-gray-300 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1.5">Max Comments Limit per Video</label>
                <input
                  type="number"
                  min="50"
                  max="10000"
                  step="50"
                  value={extractionForm.max_comments_per_video}
                  onChange={(e) => setExtractionForm({ ...extractionForm, max_comments_per_video: parseInt(e.target.value) || 500 })}
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
              </div>
            </div>
          </div>

          <div className="mt-8 flex justify-end">
            <button
              onClick={() => handleSaveSection('extraction', extractionForm)}
              disabled={saveStatus['extraction'] === 'loading'}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-semibold transition-colors disabled:opacity-50 flex items-center shadow-sm"
            >
              {saveStatus['extraction'] === 'loading' && <RefreshCw className="w-4 h-4 mr-1.5 animate-spin" />}
              Save Changes
            </button>
          </div>
        </div>

        {/* 3. yt-dlp Options Card */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200 md:col-span-2 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-6 pb-2 border-b border-gray-100">
              <h2 className="text-lg font-bold text-gray-900 flex items-center">
                <PlayCircle className="w-5 h-5 mr-2 text-indigo-600" />
                yt-dlp Scraper Options
              </h2>
              {saveStatus['ytdlp'] === 'success' && <span className="text-xs text-emerald-600 font-semibold flex items-center"><Check className="w-3.5 h-3.5 mr-0.5" /> Saved</span>}
              {saveStatus['ytdlp'] === 'error' && <span className="text-xs text-red-600 font-semibold flex items-center"><AlertCircle className="w-3.5 h-3.5 mr-0.5" /> Error</span>}
            </div>

            {cookieStatus && (
              <div className={`mb-6 p-4 rounded-xl border flex items-center justify-between animate-in fade-in duration-300 ${
                cookieStatus.type === 'success' ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-red-50 border-red-200 text-red-800'
              }`}>
                <div className="flex items-center space-x-2.5 text-sm font-semibold">
                  {cookieStatus.type === 'success' ? <CheckCircle2 className="w-5 h-5 text-emerald-600" /> : <AlertCircle className="w-5 h-5 text-red-600" />}
                  <span>{cookieStatus.message}</span>
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1.5">Player Client Type</label>
                  <select
                    value={ytdlpForm.ytdlp_player_client}
                    onChange={(e) => setYtdlpForm({ ...ytdlpForm, ytdlp_player_client: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  >
                    <option value="ios">iOS Official Client (Recommended)</option>
                    <option value="web_safari">Web Safari</option>
                    <option value="android">Android App</option>
                    <option value="mweb">Mobile Web</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1.5">Rate Limit (e.g. 500K or 5M)</label>
                  <input
                    type="text"
                    value={ytdlpForm.ytdlp_rate_limit}
                    onChange={(e) => setYtdlpForm({ ...ytdlpForm, ytdlp_rate_limit: e.target.value })}
                    placeholder="e.g. 500K"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1.5">Proxy URL Configuration</label>
                  <input
                    type="text"
                    value={ytdlpForm.ytdlp_proxy}
                    onChange={(e) => setYtdlpForm({ ...ytdlpForm, ytdlp_proxy: e.target.value })}
                    placeholder="e.g. http://username:password@ip:port"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  />
                </div>
              </div>

              {/* Cookies management panel */}
              <div className="space-y-4 bg-gray-50/50 p-4 border border-gray-150 rounded-2xl">
                <h3 className="text-sm font-bold text-gray-800 flex items-center">
                  <FileText className="w-4.5 h-4.5 mr-1.5 text-indigo-500" />
                  YouTube Session Cookies
                </h3>
                <p className="text-xs text-gray-400 leading-relaxed font-medium">
                  Provide a Netscape-formatted cookies file to bypass bot checks or access age-restricted and private contents.
                </p>

                <div className="text-xs font-semibold">
                  <span className="text-gray-400">Current Status: </span>
                  {ytdlpForm.cookies_file_path ? (
                    <span className="text-emerald-600 font-bold block mt-1 break-all bg-emerald-50/60 p-2 rounded-lg border border-emerald-100 font-mono">
                      Active: {ytdlpForm.cookies_file_path.split('\\').pop().split('/').pop()}
                    </span>
                  ) : (
                    <span className="text-amber-600 font-bold block mt-1">No cookies file configured</span>
                  )}
                </div>

                <div className="flex flex-wrap gap-2 pt-2">
                  <label className="flex items-center space-x-1.5 px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold cursor-pointer shadow-sm transition-colors">
                    <Upload className="w-3.5 h-3.5" />
                    <span>Upload File</span>
                    <input
                      type="file"
                      accept=".txt"
                      onChange={handleCookieUpload}
                      className="hidden"
                    />
                  </label>

                  {ytdlpForm.cookies_file_path && (
                    <>
                      <button
                        onClick={() => testCookiesMutation.mutate()}
                        disabled={testCookiesMutation.isPending}
                        className="px-3 py-2 border border-gray-300 hover:bg-gray-100 text-gray-700 rounded-xl text-xs font-semibold shadow-sm transition-colors flex items-center"
                      >
                        {testCookiesMutation.isPending && <RefreshCw className="w-3 h-3 mr-1 animate-spin" />}
                        Validate
                      </button>
                      
                      <button
                        onClick={() => {
                          if (window.confirm('Delete local cookies file?')) {
                            deleteCookiesMutation.mutate();
                          }
                        }}
                        className="px-3 py-2 bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 rounded-xl text-xs font-semibold shadow-sm transition-colors flex items-center"
                      >
                        <Trash2 className="w-3.5 h-3.5 mr-1" />
                        Delete
                      </button>
                    </>
                  )}
                </div>
              </div>

            </div>
          </div>

          <div className="mt-8 flex justify-end">
            <button
              onClick={() => handleSaveSection('ytdlp', ytdlpForm)}
              disabled={saveStatus['ytdlp'] === 'loading'}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-semibold transition-colors disabled:opacity-50 flex items-center shadow-sm"
            >
              {saveStatus['ytdlp'] === 'loading' && <RefreshCw className="w-4 h-4 mr-1.5 animate-spin" />}
              Save Changes
            </button>
          </div>
        </div>

        {/* 4. Monitoring / Sync Settings Card */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-6 pb-2 border-b border-gray-100">
              <h2 className="text-lg font-bold text-gray-900 flex items-center">
                <ShieldAlert className="w-5 h-5 mr-2 text-indigo-600" />
                RSS & Monitoring Sync
              </h2>
              {saveStatus['monitoring'] === 'success' && <span className="text-xs text-emerald-600 font-semibold flex items-center"><Check className="w-3.5 h-3.5 mr-0.5" /> Saved</span>}
              {saveStatus['monitoring'] === 'error' && <span className="text-xs text-red-600 font-semibold flex items-center"><AlertCircle className="w-3.5 h-3.5 mr-0.5" /> Error</span>}
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1.5">RSS Poll Interval (Minutes)</label>
                <input
                  type="number"
                  min="5"
                  max="1440"
                  value={monitoringForm.rss_poll_interval_minutes}
                  onChange={(e) => setMonitoringForm({ ...monitoringForm, rss_poll_interval_minutes: parseInt(e.target.value) || 60 })}
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
              </div>

              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                <div>
                  <span className="block text-sm font-semibold text-gray-800">Snapshot Monitoring</span>
                  <span className="block text-xs text-gray-400 mt-0.5">Collect daily video metrics snapshot stubs (views, likes).</span>
                </div>
                <input
                  type="checkbox"
                  checked={monitoringForm.snapshot_enabled}
                  onChange={(e) => setMonitoringForm({ ...monitoringForm, snapshot_enabled: e.target.checked })}
                  className="w-4.5 h-4.5 rounded text-indigo-600 border-gray-300 focus:ring-indigo-500"
                />
              </div>
            </div>
          </div>

          <div className="mt-8 flex justify-end">
            <button
              onClick={() => handleSaveSection('monitoring', monitoringForm)}
              disabled={saveStatus['monitoring'] === 'loading'}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-semibold transition-colors disabled:opacity-50 flex items-center shadow-sm"
            >
              {saveStatus['monitoring'] === 'loading' && <RefreshCw className="w-4 h-4 mr-1.5 animate-spin" />}
              Save Changes
            </button>
          </div>
        </div>

        {/* 5. Advanced / Database Info Card */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-6 pb-2 border-b border-gray-100">
              <h2 className="text-lg font-bold text-gray-900 flex items-center">
                <Database className="w-5 h-5 mr-2 text-indigo-600" />
                Advanced / Database Info
              </h2>
              <span className="text-xs text-gray-400 font-semibold font-mono">ID: {data?.settings?.id || 1}</span>
            </div>

            {data?.db_stats && (
              <div className="space-y-4">
                
                <div className="grid grid-cols-2 gap-3.5">
                  <div className="p-3 bg-gray-50 border border-gray-100 rounded-xl">
                    <span className="block text-xs text-gray-400 font-bold uppercase tracking-wider">Channels</span>
                    <span className="text-xl font-extrabold text-gray-900 mt-1 block">{data.db_stats.counts.channels}</span>
                  </div>
                  <div className="p-3 bg-gray-50 border border-gray-100 rounded-xl">
                    <span className="block text-xs text-gray-400 font-bold uppercase tracking-wider">Videos</span>
                    <span className="text-xl font-extrabold text-gray-900 mt-1 block">{data.db_stats.counts.videos}</span>
                  </div>
                  <div className="p-3 bg-gray-50 border border-gray-100 rounded-xl">
                    <span className="block text-xs text-gray-400 font-bold uppercase tracking-wider">Downloads</span>
                    <span className="text-xl font-extrabold text-gray-900 mt-1 block">{data.db_stats.counts.downloads}</span>
                  </div>
                  <div className="p-3 bg-gray-50 border border-gray-100 rounded-xl">
                    <span className="block text-xs text-gray-400 font-bold uppercase tracking-wider">Comments</span>
                    <span className="text-xl font-extrabold text-gray-900 mt-1 block">{data.db_stats.counts.comments}</span>
                  </div>
                </div>

                <div className="flex items-center justify-between p-3.5 bg-indigo-50/40 border border-indigo-100 rounded-xl">
                  <div>
                    <span className="block text-xs font-bold text-indigo-600 uppercase tracking-wider">Database Space Used</span>
                    <span className="text-base font-extrabold text-gray-900 mt-0.5 block">{formatBytes(data.db_stats.size_bytes)}</span>
                  </div>
                  <Database className="w-7 h-7 text-indigo-500 opacity-80" />
                </div>

              </div>
            )}
          </div>

          <div className="mt-8 pt-4 border-t border-gray-100 flex items-center justify-between text-xs text-gray-400 font-medium">
            <span>Cache TTL: 24 Hours</span>
            <span className="font-mono text-gray-300">V1.0.0</span>
          </div>
        </div>

      </div>
    </div>
  );
}
