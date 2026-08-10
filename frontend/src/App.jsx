import { Routes, Route, Navigate } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import Channels from './pages/Channels'
import ChannelDetail from './pages/ChannelDetail'
import VideoDetail from './pages/VideoDetail'
import Downloader from './pages/Downloader'
import Jobs from './pages/Jobs'
import Settings from './pages/Settings'

import Dashboard from './pages/Dashboard'
import Videos from './pages/Videos'
import Search from './pages/Search'



function App() {
  return (
    <Routes>
      <Route path="/" element={<AppShell />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="channels" element={<Channels />} />
        <Route path="channels/:id" element={<ChannelDetail />} />
        <Route path="videos" element={<Videos />} />
        <Route path="videos/:id" element={<VideoDetail />} />
        <Route path="downloader" element={<Downloader />} />
        <Route path="search" element={<Search />} />
        <Route path="jobs" element={<Jobs />} />
        <Route path="settings" element={<Settings />} />
        <Route path="*" element={<div className="p-4">404 - Not Found</div>} />
      </Route>
    </Routes>
  )
}

export default App
