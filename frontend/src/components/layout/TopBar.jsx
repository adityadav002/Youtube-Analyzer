import { useLocation, Link } from 'react-router-dom'
import { Menu, Youtube } from 'lucide-react'

export default function TopBar({ onMenuClick }) {
  const location = useLocation()
  
  // Map paths to user-friendly titles
  const getPageTitle = (pathname) => {
    if (pathname === '/dashboard') return 'Dashboard'
    if (pathname.startsWith('/channels')) {
      if (pathname.includes('/', 10)) return 'Channel Details' // matches /channels/:id
      return 'Channels'
    }
    if (pathname.startsWith('/videos')) {
      if (pathname.includes('/', 8)) return 'Video Details' // matches /videos/:id
      return 'Videos'
    }
    if (pathname === '/downloader') return 'Media Downloader'
    if (pathname === '/search') return 'Search Videos'
    if (pathname === '/jobs') return 'Background Jobs'
    if (pathname === '/settings') return 'Settings'
    return 'YouTube Video Analyzer'
  }

  const title = getPageTitle(location.pathname)

  return (
    <header className="bg-white border-b border-gray-200 h-16 flex items-center justify-between px-4 sm:px-6 lg:px-8 z-10 shrink-0 shadow-sm">
      <div className="flex items-center space-x-3">
        {/* Hamburger Menu on Mobile */}
        <button 
          onClick={onMenuClick}
          className="md:hidden p-2 rounded-lg text-gray-500 hover:text-gray-900 hover:bg-gray-100 focus:outline-none transition-colors"
          aria-label="Open sidebar"
        >
          <Menu className="w-6 h-6" />
        </button>

        {/* Brand Logo - Mobile Only */}
        <Link to="/dashboard" className="flex md:hidden items-center space-x-2">
          <div className="bg-indigo-600 p-1.5 rounded-lg">
            <Youtube className="w-5 h-5 text-white" />
          </div>
          <span className="text-base font-bold text-gray-900 tracking-tight">YT Analyzer</span>
        </Link>

        {/* Page Title - Desktop Only */}
        <h1 className="hidden md:block text-lg font-semibold text-gray-800">
          {title}
        </h1>
      </div>

      {/* Page Title - Mobile Only */}
      <div className="md:hidden text-sm font-semibold text-gray-600">
        {title}
      </div>
    </header>
  )
}
