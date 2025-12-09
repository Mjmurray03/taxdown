'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  Home,
  Search,
  FileText,
  Briefcase,
  BarChart3,
  Settings,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

const navItems = [
  { title: 'Dashboard', href: '/', icon: Home },
  { title: 'Properties', href: '/properties', icon: Search },
  { title: 'Appeals', href: '/appeals', icon: FileText },
  { title: 'Portfolio', href: '/portfolio', icon: Briefcase },
  { title: 'Reports', href: '/reports', icon: BarChart3 },
];

export function MainLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-white">
      {/* Top Navigation */}
      <header className="sticky top-0 z-50 w-full border-b border-[#E4E4E7] bg-white">
        <div className="mx-auto max-w-[1440px] flex h-16 items-center justify-between px-12">
          {/* Logo */}
          <Link href="/" className="flex items-center">
            <span className="text-xl font-semibold tracking-tight text-[#18181B]">Taxdown</span>
          </Link>

          {/* Navigation */}
          <nav className="hidden md:flex items-center space-x-1">
            {navItems.map((item) => {
              const isActive = pathname === item.href ||
                (item.href !== '/' && pathname.startsWith(item.href));

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'relative px-4 py-2 text-sm font-medium transition-standard',
                    isActive
                      ? 'text-[#18181B]'
                      : 'text-[#71717A] hover:text-[#18181B]'
                  )}
                >
                  <span>{item.title}</span>
                  {isActive && (
                    <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#18181B]" />
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Right side */}
          <div className="flex items-center">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon-sm">
                  <Settings className="h-5 w-5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuItem className="text-sm">
                  Account Settings
                </DropdownMenuItem>
                <DropdownMenuItem className="text-sm">
                  Preferences
                </DropdownMenuItem>
                <DropdownMenuItem className="text-sm text-[#991B1B]">
                  Sign Out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-[1440px] px-12 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-[#E4E4E7] bg-white mt-auto">
        <div className="mx-auto max-w-[1440px] px-12 py-6">
          <p className="text-center text-sm text-[#71717A]">
            Taxdown - Property tax intelligence for Benton County, Arkansas
          </p>
        </div>
      </footer>
    </div>
  );
}
