import { NavLink, Outlet } from 'react-router-dom';
import { MessageSquare, LayoutDashboard, BrainCircuit, Database, FileText } from 'lucide-react';
import { useAppStore } from '@/stores/appStore';

export function Layout() {
    const { theme, toggleTheme } = useAppStore();

    const navItems = [
        { to: "/onboarding", icon: <BrainCircuit size={20} />, label: "Initialization" },
        { to: "/", icon: <MessageSquare size={20} />, label: "Simulator" },
        { to: "/dashboard", icon: <LayoutDashboard size={20} />, label: "Dashboard" },
        { to: "/flywheel", icon: <BrainCircuit size={20} />, label: "Data Flywheel" },
        { to: "/knowledge", icon: <Database size={20} />, label: "Knowledge Base" },
        { to: "/prompts", icon: <FileText size={20} />, label: "Prompt Registry" },
    ];

    return (
        <div className={`flex h-screen overflow-hidden ${theme === 'dark' ? 'dark bg-background text-foreground' : 'bg-background text-foreground'}`}>

            {/* Sidebar */}
            <aside className="w-64 border-r border-border bg-card flex flex-col">
                <div className="p-6 border-b border-border flex items-center space-x-3 text-primary">
                    <BrainCircuit size={28} className="text-blue-500" />
                    <h1 className="text-xl font-bold tracking-tight">SalesAgent V3</h1>
                </div>

                <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
                    {navItems.map((item) => (
                        <NavLink
                            key={item.to}
                            to={item.to}
                            className={({ isActive }) =>
                                `flex items-center space-x-3 px-4 py-3 rounded-md transition-colors ${isActive
                                    ? 'bg-primary text-primary-foreground font-medium shadow-sm'
                                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                                }`
                            }
                        >
                            {item.icon}
                            <span>{item.label}</span>
                        </NavLink>
                    ))}
                </nav>

                <div className="p-4 border-t border-border">
                    <button
                        onClick={toggleTheme}
                        className="flex items-center space-x-3 w-full px-4 py-2 rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
                    >
                        <span>Toggle {theme === 'dark' ? 'Light' : 'Dark'} Mode</span>
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
                <div className="flex-1 overflow-auto bg-background">
                    <Outlet />
                </div>
            </main>

        </div>
    );
}
