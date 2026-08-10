import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Users, Plus, Search } from 'lucide-react';
import { getChannels } from '../api/channels';
import ChannelCard from '../components/channel/ChannelCard';
import AddChannelModal from '../components/channel/AddChannelModal';

export default function Channels() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [search, setSearch] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['channels'],
    queryFn: () => getChannels({ page: 1, per_page: 50 })
  });

  const channels = data?.items || [];
  const filteredChannels = channels.filter(c => 
    c.display_name?.toLowerCase().includes(search.toLowerCase()) || 
    c.handle?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Users className="w-7 h-7 text-indigo-600" />
            Channels
          </h1>
          <p className="text-gray-500 mt-1">Manage and track your YouTube channels.</p>
        </div>
        <button 
          onClick={() => setIsModalOpen(true)}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-indigo-700 transition-colors flex items-center shadow-sm"
        >
          <Plus className="w-5 h-5 mr-1" />
          Add Channel
        </button>
      </div>

      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex items-center">
        <Search className="w-5 h-5 text-gray-400 mr-3" />
        <input 
          type="text" 
          placeholder="Filter channels by name or handle..." 
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 bg-transparent border-none focus:outline-none text-gray-700"
        />
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {[1,2,3,4].map(i => (
            <div key={i} className="bg-white rounded-xl shadow-sm border border-gray-200 h-64 animate-pulse">
              <div className="h-20 bg-gray-200 rounded-t-xl" />
              <div className="px-5 relative">
                <div className="w-20 h-20 rounded-full border-4 border-white bg-gray-200 relative -mt-10 mb-3" />
                <div className="h-6 bg-gray-200 rounded w-3/4 mb-2" />
                <div className="h-4 bg-gray-200 rounded w-1/2 mb-4" />
                <div className="h-4 bg-gray-200 rounded w-full" />
              </div>
            </div>
          ))}
        </div>
      ) : filteredChannels.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredChannels.map(channel => (
            <ChannelCard key={channel.id} channel={channel} />
          ))}
        </div>
      ) : (
        <div className="text-center py-20 bg-white rounded-xl border border-dashed border-gray-300">
          <Users className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-gray-900">No channels found</h3>
          <p className="text-gray-500 mt-1">Get started by adding a YouTube channel to track.</p>
          <button 
            onClick={() => setIsModalOpen(true)}
            className="mt-4 text-indigo-600 font-medium hover:text-indigo-700"
          >
            + Add Channel
          </button>
        </div>
      )}

      <AddChannelModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </div>
  );
}
