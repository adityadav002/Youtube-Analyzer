import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Users, Youtube, DownloadCloud, Search, Activity, Settings, X } from 'lucide-react'

const navItems = [
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Channels', path: '/channels', icon: Users },
  { name: 'Videos', path: '/videos', icon: Youtube },
  { name: 'Downloader', path: '/downloader', icon: DownloadCloud },
  { name: 'Search', path: '/search', icon: Search },
  { name: 'Jobs', path: '/jobs', icon: Activity },
]

function SidebarContent({ onClose }) {
  return (
    <div className="flex flex-col h-full bg-slate-900 text-white">
      {/* Logo Area */}
      <div className="p-6 flex items-center justify-between border-b border-slate-800">
        <div className="flex items-center space-x-3">
          <div className="bg-indigo-600 p-2 rounded-lg">
            <Youtube className="w-6 h-6 text-white" />
          </div>
          <span className="text-lg font-bold tracking-tight">YT Analyzer</span>
        </div>
        {/* Close button - only visible on mobile drawer */}
        <button 
          className="md:hidden p-2 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 focus:outline-none transition-colors"
          onClick={onClose}
          aria-label="Close sidebar"
        >
          <X className="w-5 h-5" />
        </button>
      </div>
      
      {/* Navigation Links */}
      <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.name}
            to={item.path}
            onClick={onClose}
            className={({ isActive }) =>
              `flex items-center space-x-3 px-3 py-2.5 rounded-lg transition-all duration-200 ${
                isActive 
                  ? 'bg-indigo-600 text-white font-medium shadow-md shadow-indigo-600/10' 
                  : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
              }`
            }
          >
            <item.icon className="w-5 h-5" />
            <span>{item.name}</span>
          </NavLink>
        ))}
      </nav>
      
      {/* Footer / Settings Link */}
      <div className="p-4 border-t border-slate-800">
        <NavLink
          to="/settings"
          onClick={onClose}
          className={({ isActive }) =>
            `flex items-center space-x-3 px-3 py-2.5 rounded-lg transition-all duration-200 ${
              isActive 
                ? 'bg-indigo-600 text-white font-medium shadow-md shadow-indigo-600/10' 
                : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
            }`
          }
        >
          <Settings className="w-5 h-5" />
          <span>Settings</span>
        </NavLink>
      </div>
    </div>
  )
}

export default function Sidebar({ isOpen, onClose }) {
  return (
    <>
      {/* Desktop Sidebar (permanent) */}
      <aside className="hidden md:flex w-64 flex-col shrink-0 shadow-xl border-r border-slate-800 z-20">
        <SidebarContent />
      </aside>

      {/* Mobile Drawer (overlay) */}
      <div className={`fixed inset-0 z-40 md:hidden transition-all duration-300 ${isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`}>
        {/* Backdrop */}
        <div 
          className={`fixed inset-0 bg-slate-950/60 backdrop-blur-sm transition-opacity duration-300 ${isOpen ? 'opacity-100' : 'opacity-0'}`} 
          onClick={onClose} 
        />
        
        {/* Drawer container */}
        <aside className={`fixed inset-y-0 left-0 w-64 flex flex-col shadow-2xl transition-transform duration-300 ease-out transform ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>
          <SidebarContent onClose={onClose} />
        </aside>
      </div>
    </>
  )
}
