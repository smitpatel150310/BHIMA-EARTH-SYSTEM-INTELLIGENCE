import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import {
  LayoutDashboard,
  Globe,
  Search,
  BarChart2,
  MessageCircle,
  Database,
  BookOpen,
  X,
  ExternalLink,
} from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const NAV_ITEMS = [
  { path: '/app/overview', label: 'Overview', icon: LayoutDashboard },
  { path: '/app/explorer', label: 'Earth Explorer', icon: Globe },
  { path: '/app/investigation', label: 'Investigation', icon: Search },
  { path: '/app/compare', label: 'Compare Regions', icon: BarChart2 },
  { path: '/app/ask', label: 'Ask BHIMA', icon: MessageCircle },
  { path: '/app/data-sources', label: 'Data Sources', icon: Database },
  { path: '/app/methodology', label: 'Methodology', icon: BookOpen },
];

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-bhima-text/20 backdrop-blur-xs z-30 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed top-0 bottom-0 left-0 z-40 w-60 bg-white border-r border-bhima-border flex flex-col transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand header */}
        <div className="h-14 border-b border-bhima-border px-5 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-7 h-7 rounded bg-bhima-primary flex items-center justify-center text-white font-semibold text-sm">
              B
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-sm tracking-tight text-bhima-text">BHIMA</span>
              <span className="text-[10px] text-bhima-secondary -mt-1 font-medium tracking-wide uppercase">
                Earth Intelligence
              </span>
            </div>
          </Link>

          <button
            onClick={onClose}
            className="lg:hidden p-1 text-bhima-muted hover:text-bhima-text rounded"
            aria-label="Close menu"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation list */}
        <div className="flex-1 py-4 px-3 overflow-y-auto space-y-1">
          <div className="px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-bhima-secondary">
            Platform
          </div>
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => onClose()}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 text-xs font-medium rounded-md transition-colors ${
                    isActive
                      ? 'bg-bhima-primary text-white shadow-xs'
                      : 'text-bhima-text hover:bg-bhima-subtle hover:text-bhima-text'
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </div>

        {/* Sidebar footer: NASA data sources & integrity note */}
        <div className="p-3 border-t border-bhima-border bg-bhima-subtle/50">
          <div className="bg-white rounded border border-bhima-border p-3 text-[11px]">
            <div className="text-bhima-secondary font-medium uppercase tracking-wider text-[10px] mb-1">
              Data Pipeline
            </div>
            <div className="text-bhima-text font-medium flex items-center justify-between mb-1">
              <span>NASA GPM / MODIS</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
            </div>
            <p className="text-[10px] text-bhima-muted leading-relaxed">
              Mann-Kendall & Sen's Slope verified without synthetic interpolation.
            </p>
            <Link
              to="/"
              className="mt-2.5 inline-flex items-center gap-1 text-[11px] font-medium text-bhima-primary hover:underline"
            >
              Public Home <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </aside>
    </>
  );
};
