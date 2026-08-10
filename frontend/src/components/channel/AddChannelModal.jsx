import { useState, useEffect } from 'react';
import { X, Youtube, Loader2 } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { addChannel } from '../../api/channels';
import { getJobStatus } from '../../api/jobs';

export default function AddChannelModal({ isOpen, onClose }) {
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');
  const [jobId, setJobId] = useState(null);
  
  const queryClient = useQueryClient();

  const addMutation = useMutation({
    mutationFn: addChannel,
    onSuccess: (data) => {
      setJobId(data.job_id);
    },
    onError: (err) => {
      setError(err.response?.data?.error || 'Failed to add channel');
    }
  });

  useEffect(() => {
    let interval;
    if (jobId) {
      interval = setInterval(async () => {
        try {
          const status = await getJobStatus(jobId);
          if (status.status === 'complete') {
            clearInterval(interval);
            queryClient.invalidateQueries({ queryKey: ['channels'] });
            setJobId(null);
            setUrl('');
            onClose();
          } else if (status.status === 'failed') {
            clearInterval(interval);
            setJobId(null);
            setError(status.error_message || 'Extraction failed');
          }
        } catch (e) {
          clearInterval(interval);
          setJobId(null);
          setError('Failed to poll job status');
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [jobId, queryClient, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden">
        <div className="flex justify-between items-center p-5 border-b border-gray-100 bg-gray-50/50">
          <h2 className="text-xl font-bold text-gray-900 flex items-center">
            <Youtube className="w-6 h-6 mr-2 text-indigo-600" />
            Add Channel
          </h2>
          <button onClick={onClose} disabled={!!jobId} className="p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="p-6">
          <form onSubmit={(e) => {
            e.preventDefault();
            setError('');
            if (!url) return;
            addMutation.mutate(url);
          }}>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              YouTube Channel URL or @handle
            </label>
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={!!jobId || addMutation.isPending}
              placeholder="https://youtube.com/@channel..."
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-shadow"
              autoFocus
            />
            {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
            
            <div className="mt-6 flex justify-end space-x-3">
              <button
                type="button"
                onClick={onClose}
                disabled={!!jobId}
                className="px-4 py-2 text-gray-700 font-medium hover:bg-gray-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!url || !!jobId || addMutation.isPending}
                className="px-6 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 focus:ring-4 focus:ring-indigo-100 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              >
                {(jobId || addMutation.isPending) ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    Extracting...
                  </>
                ) : (
                  'Add Channel'
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
