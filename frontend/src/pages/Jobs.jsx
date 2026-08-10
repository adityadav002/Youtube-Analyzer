import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Activity, RefreshCw, XCircle, Eye, SlidersHorizontal, Clock,
  Users, Video, DownloadCloud, AlertCircle, CheckCircle2, Play, Info
} from 'lucide-react';
import { getJobs, cancelJob, retryJob } from '../api/jobs';

export default function Jobs() {
  const queryClient = useQueryClient();

  // Filters State
  const [statusFilter, setStatusFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');

  // Detail Modal State
  const [selectedJob, setSelectedJob] = useState(null);

  // Fetch jobs with smart polling
  const { data: jobs = [], isLoading, isError } = useQuery({
    queryKey: ['jobs', { status: statusFilter, job_type: typeFilter }],
    queryFn: () => getJobs({ status: statusFilter, job_type: typeFilter }),
    refetchInterval: (query) => {
      const hasActive = query.state.data?.some(j => j.status === 'queued' || j.status === 'processing');
      return hasActive ? 3000 : 10000;
    }
  });

  // Mutations
  const cancelJobMutation = useMutation({
    mutationFn: cancelJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
    onError: (err) => {
      alert(err.response?.data?.error || 'Failed to cancel job');
    }
  });

  const retryJobMutation = useMutation({
    mutationFn: retryJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
    onError: (err) => {
      alert(err.response?.data?.error || 'Failed to retry job');
    }
  });

  const getStatusBadge = (status) => {
    switch (status) {
      case 'complete':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
            <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Complete
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800">
            <AlertCircle className="w-3.5 h-3.5 mr-1" /> Failed
          </span>
        );
      case 'cancelled':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-800">
            <XCircle className="w-3.5 h-3.5 mr-1" /> Cancelled
          </span>
        );
      case 'processing':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
            <RefreshCw className="w-3.5 h-3.5 mr-1 animate-spin" /> Processing
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
            <Clock className="w-3.5 h-3.5 mr-1" /> Queued
          </span>
        );
    }
  };

  const getJobTypeIcon = (type) => {
    switch (type) {
      case 'crawl_channel':
        return <Users className="w-4 h-4 text-blue-500" />;
      case 'extract_channel':
        return <Users className="w-4 h-4 text-purple-500" />;
      case 'extract_video':
        return <Video className="w-4 h-4 text-emerald-500" />;
      case 'download_video':
        return <DownloadCloud className="w-4 h-4 text-indigo-500" />;
      default:
        return <Activity className="w-4 h-4 text-gray-500" />;
    }
  };

  const getDuration = (job) => {
    if (!job.created_at) return '—';
    const start = new Date(job.created_at);
    const end = job.status === 'processing' || job.status === 'queued'
      ? new Date()
      : new Date(job.updated_at || job.created_at);
    
    const diffMs = end - start;
    if (diffMs < 0) return '0s';
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    
    if (diffHours > 0) {
      return `${diffHours}h ${diffMins % 60}m`;
    }
    if (diffMins > 0) {
      return `${diffMins}m ${diffSecs % 60}s`;
    }
    return `${diffSecs}s`;
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Header */}
      <div>
        <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight flex items-center">
          <Activity className="w-8 h-8 mr-3 text-indigo-600" />
          Background Jobs
        </h1>
        <p className="text-gray-500 mt-2">Monitor all channel crawling, metadata extraction, and media download background tasks.</p>
      </div>

      {/* Filters Bar */}
      <div className="bg-white p-5 rounded-2xl shadow-sm border border-gray-200">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-2 text-gray-700 font-semibold">
            <SlidersHorizontal className="w-5 h-5 text-indigo-600" />
            <span>Filters</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full sm:w-auto">
            <div>
              <label htmlFor="job-type-filter" className="sr-only">Filter by Job Type</label>
              <select
                id="job-type-filter"
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="w-full sm:w-48 px-3.5 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
              >
                <option value="all">All Types</option>
                <option value="crawl_channel">Crawl Channel</option>
                <option value="extract_channel">Extract Channel</option>
                <option value="extract_video">Extract Video</option>
                <option value="download_video">Download Video</option>
              </select>
            </div>
            <div>
              <label htmlFor="job-status-filter" className="sr-only">Filter by Status</label>
              <select
                id="job-status-filter"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full sm:w-48 px-3.5 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
              >
                <option value="all">All Statuses</option>
                <option value="queued">Queued</option>
                <option value="processing">Processing</option>
                <option value="complete">Complete</option>
                <option value="failed">Failed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Jobs Table Section */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-gray-500">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-3 text-indigo-600" />
            <p className="font-medium text-gray-600">Loading background jobs...</p>
          </div>
        ) : isError ? (
          <div className="p-12 text-center text-red-500">
            <AlertCircle className="w-12 h-12 mx-auto mb-3 text-red-400" />
            <p className="font-semibold text-lg">Error loading background jobs</p>
            <p className="text-sm mt-1 text-red-400">Please make sure the backend server is running.</p>
          </div>
        ) : jobs.length === 0 ? (
          <div className="p-16 text-center text-gray-400">
            <Activity className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <p className="text-lg font-bold text-gray-600">No background jobs found</p>
            <p className="text-sm mt-1 text-gray-400">No jobs match your current filter selection.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Job Type</th>
                  <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Target</th>
                  <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
                  <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Progress</th>
                  <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Created</th>
                  <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Duration</th>
                  <th scope="col" className="px-6 py-4 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200 text-sm">
                {jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-gray-50/50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center space-x-2.5">
                        <span className="p-1.5 bg-gray-100 rounded-lg">{getJobTypeIcon(job.job_type)}</span>
                        <span className="font-semibold text-gray-800 uppercase tracking-wide text-xs">
                          {job.job_type.replace('_', ' ')}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {job.job_type === 'extract_video' || job.job_type === 'download_video' ? (
                        <Link
                          to={`/videos/${job.target_id}`}
                          className="font-semibold text-indigo-600 hover:text-indigo-800 hover:underline max-w-[240px] truncate block"
                          title={job.target_title}
                        >
                          {job.target_title}
                        </Link>
                      ) : job.job_type === 'crawl_channel' ? (
                        <Link
                          to={`/channels/${job.target_id}`}
                          className="font-semibold text-indigo-600 hover:text-indigo-800 hover:underline max-w-[240px] truncate block"
                          title={job.target_title}
                        >
                          {job.target_title}
                        </Link>
                      ) : (
                        <span className="text-gray-800 font-semibold max-w-[240px] truncate block" title={job.target_title}>
                          {job.target_title}
                        </span>
                      )}
                      <span className="text-xs text-gray-400 font-mono mt-0.5 block">{job.id.slice(0, 8)}...</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(job.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {job.job_type === 'download_video' ? (
                        <div className="flex items-center space-x-2">
                          <div className="w-16 bg-gray-200 rounded-full h-1.5 flex-shrink-0">
                            <div
                              className="bg-indigo-600 h-1.5 rounded-full"
                              style={{ width: `${job.payload?.progress_percent || 0}%` }}
                            ></div>
                          </div>
                          <span className="text-xs text-gray-500 font-mono font-semibold">
                            {job.payload?.progress_percent || 0}%
                          </span>
                        </div>
                      ) : job.status === 'complete' ? (
                        <span className="text-xs text-emerald-600 font-bold">100%</span>
                      ) : job.status === 'processing' ? (
                        <span className="text-xs text-blue-600 font-semibold animate-pulse">Running...</span>
                      ) : (
                        <span className="text-xs text-gray-400 font-semibold">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                      {job.created_at ? new Date(job.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500 font-medium">
                      {getDuration(job)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right space-x-1.5">
                      <button
                        onClick={() => setSelectedJob(job)}
                        title="View details"
                        className="inline-flex p-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-indigo-600 transition-all shadow-sm"
                      >
                        <Eye className="w-4 h-4" />
                      </button>

                      {(job.status === 'queued' || job.status === 'processing') && (
                        <button
                          onClick={() => cancelJobMutation.mutate(job.id)}
                          title="Cancel job"
                          className="inline-flex p-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-red-600 hover:border-red-100 transition-all shadow-sm"
                        >
                          <XCircle className="w-4 h-4" />
                        </button>
                      )}

                      {(job.status === 'failed' || job.status === 'cancelled') && (
                        <button
                          onClick={() => retryJobMutation.mutate(job.id)}
                          title="Retry job"
                          className="inline-flex p-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-indigo-600 transition-all shadow-sm"
                        >
                          <Play className="w-4 h-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Job Detail Modal */}
      {selectedJob && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/40 flex items-center justify-center p-4 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full border border-gray-100 overflow-hidden transform transition-all flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="p-6 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-gray-900 flex items-center">
                  <span className="p-1 bg-gray-100 rounded-lg mr-2">{getJobTypeIcon(selectedJob.job_type)}</span>
                  Job Details
                </h3>
                <p className="text-xs text-gray-500 font-mono mt-1">ID: {selectedJob.id}</p>
              </div>
              <button
                onClick={() => setSelectedJob(null)}
                className="text-gray-400 hover:text-gray-600 p-1.5 hover:bg-gray-100 rounded-lg transition-all"
              >
                <SlidersHorizontal className="w-5 h-5 transform rotate-45" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-6 flex-1 text-sm text-gray-700">
              
              {/* Properties Grid */}
              <div className="grid grid-cols-2 gap-4 bg-gray-50 p-4 rounded-xl border border-gray-100 font-medium">
                <div>
                  <span className="block text-xs text-gray-400">Type</span>
                  <span className="text-gray-900 uppercase text-xs font-semibold">{selectedJob.job_type.replace('_', ' ')}</span>
                </div>
                <div>
                  <span className="block text-xs text-gray-400">Status</span>
                  <span className="mt-0.5 inline-block">{getStatusBadge(selectedJob.status)}</span>
                </div>
                <div>
                  <span className="block text-xs text-gray-400">Created At</span>
                  <span className="text-gray-800">{new Date(selectedJob.created_at).toLocaleString()}</span>
                </div>
                <div>
                  <span className="block text-xs text-gray-400">Duration</span>
                  <span className="text-gray-800">{getDuration(selectedJob)}</span>
                </div>
                <div>
                  <span className="block text-xs text-gray-400">Priority</span>
                  <span className="text-gray-800">{selectedJob.priority}</span>
                </div>
                <div>
                  <span className="block text-xs text-gray-400">Retry Count</span>
                  <span className="text-gray-800">{selectedJob.retry_count}</span>
                </div>
              </div>

              {/* Payload Block */}
              <div>
                <span className="block text-xs font-bold text-gray-400 mb-2 uppercase tracking-wide">Payload Arguments</span>
                <pre className="bg-slate-900 text-slate-100 p-4 rounded-xl overflow-x-auto font-mono text-xs shadow-inner">
                  {JSON.stringify(selectedJob.payload, null, 2)}
                </pre>
              </div>

              {/* Error Message Code block if failed */}
              {selectedJob.status === 'failed' && selectedJob.error_message && (
                <div>
                  <span className="block text-xs font-bold text-red-500 mb-2 uppercase tracking-wide flex items-center">
                    <AlertCircle className="w-4 h-4 mr-1" /> Execution Error Stack trace
                  </span>
                  <pre className="bg-red-50 text-red-800 border border-red-200 p-4 rounded-xl overflow-x-auto font-mono text-xs whitespace-pre-wrap break-all shadow-inner">
                    {selectedJob.error_message}
                  </pre>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 bg-gray-50 border-t border-gray-100 flex justify-end space-x-2">
              <button
                onClick={() => setSelectedJob(null)}
                className="px-4 py-2 border border-gray-300 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-100 transition-colors"
              >
                Close
              </button>
              {(selectedJob.status === 'failed' || selectedJob.status === 'cancelled') && (
                <button
                  onClick={() => {
                    retryJobMutation.mutate(selectedJob.id);
                    setSelectedJob(null);
                  }}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-semibold transition-colors shadow-sm flex items-center"
                >
                  <Play className="w-4 h-4 mr-1.5" /> Retry Job
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
