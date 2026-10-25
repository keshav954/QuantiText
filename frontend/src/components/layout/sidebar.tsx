/**
 * Sidebar navigation — responsive with collapse support.
 * 
 * Uses Lucide icons. Navigation items highlight based on current route.
 * Collapses to icon-only on mobile or via toggle.
 */

import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  Bot,
  TrendingUp,
  Package,
  Bell,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  Zap,
  Info,
  Mail,
} from 'lucide-react'
import { AboutModal, ContactModal } from '@/components/common/about-contact-modal'

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/copilot', label: 'AI Chatbot', icon: Bot },
  { to: '/forecasts', label: 'Forecasts', icon: TrendingUp },
  { to: '/inventory', label: 'Inventory', icon: Package },
  { to: '/alerts', label: 'Alerts', icon: Bell },
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/admin', label: 'Admin', icon: Settings },
]

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const [aboutOpen, setAboutOpen] = useState(false)
  const [contactOpen, setContactOpen] = useState(false)

  return (
    <aside
      className={cn(
        'hidden md:flex flex-col border-r border-border/80 dark:border-border/50 bg-card/80 dark:bg-card/50 backdrop-blur-sm transition-all duration-300',
        collapsed ? 'w-[68px]' : 'w-[240px]',
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 px-4 border-b border-border/80 dark:border-border/50">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg shadow-indigo-500/25">
          <Zap className="h-5 w-5 text-white" />
        </div>
        {!collapsed && (
          <div className="animate-fade-in">
            <h1 className="text-sm font-bold text-gradient">QuantiText</h1>
            <p className="text-[10px] text-muted-foreground">Chatbot</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-3 overflow-y-auto" role="navigation" aria-label="Main navigation">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 focus-ring',
                'hover:bg-accent hover:text-accent-foreground',
                isActive
                  ? 'bg-primary/10 text-primary shadow-sm font-semibold'
                  : 'text-muted-foreground',
                collapsed && 'justify-center px-2',
              )
            }
            title={collapsed ? label : undefined}
          >
            <Icon className="h-5 w-5 shrink-0" />
            {!collapsed && <span className="animate-fade-in">{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* About & Contact Us in left down corner */}
      <div className="border-t border-border/80 dark:border-border/50 px-2 py-1.5">
        <div className={cn('flex items-center gap-1', collapsed ? 'flex-col' : 'justify-between')}>
          <button
            id="sidebar-about-btn"
            type="button"
            onClick={() => setAboutOpen(true)}
            className={cn(
              'flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition-colors focus-ring',
              collapsed && 'justify-center w-full px-1',
            )}
            title="About QuantiText"
            aria-label="About QuantiText"
          >
            <Info className="h-4 w-4 shrink-0 text-primary" />
            {!collapsed && <span>About</span>}
          </button>

          <button
            id="sidebar-contact-btn"
            type="button"
            onClick={() => setContactOpen(true)}
            className={cn(
              'flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition-colors focus-ring',
              collapsed && 'justify-center w-full px-1',
            )}
            title="Contact Us"
            aria-label="Contact Us"
          >
            <Mail className="h-4 w-4 shrink-0 text-primary" />
            {!collapsed && <span>Contact Us</span>}
          </button>
        </div>
      </div>

      {/* Collapse toggle */}
      <div className="border-t border-border/80 dark:border-border/50 p-2.5">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex w-full items-center justify-center rounded-lg p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors focus-ring"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>

      {/* Synthetic data badge */}
      {!collapsed && (
        <div className="px-4 pb-3">
          <div className="rounded-lg bg-warning/10 border border-warning/20 px-3 py-2">
            <p className="text-[10px] font-medium text-warning">⚠️ SYNTHETIC DATA</p>
          </div>
        </div>
      )}

      {/* Individual Modals */}
      <AboutModal isOpen={aboutOpen} onClose={() => setAboutOpen(false)} />
      <ContactModal isOpen={contactOpen} onClose={() => setContactOpen(false)} />
    </aside>
  )
}
