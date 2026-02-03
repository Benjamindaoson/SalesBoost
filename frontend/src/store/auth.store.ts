import { create } from 'zustand';
import { User, Session } from '@supabase/supabase-js';
import { supabase } from '@/lib/supabase';

interface AuthState {
  user: User | null;
  session: Session | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  initialize: () => Promise<void>;
  signOut: () => Promise<void>;
  mockLogin: (email: string) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  session: null,
  isLoading: true,
  isAuthenticated: false,

  mockLogin: (email: string) => {
    const mockUser = {
      id: 'mock-user-id',
      email: email,
      app_metadata: { provider: 'email' },
      user_metadata: { role: 'student' },
      aud: 'authenticated',
      created_at: new Date().toISOString(),
    } as User;
    
    set({ 
      user: mockUser, 
      isAuthenticated: true, 
      isLoading: false 
    });
    localStorage.setItem('salesboost-mock-auth', 'true');
  },

  initialize: async () => {
    try {
      // Check for mock auth first
      if (localStorage.getItem('salesboost-mock-auth') === 'true') {
        const mockUser = {
          id: 'mock-user-id',
          email: 'demo@salesboost.com',
          app_metadata: { provider: 'email' },
          user_metadata: { role: 'student' },
          aud: 'authenticated',
          created_at: new Date().toISOString(),
        } as User;
        
        set({ 
          user: mockUser, 
          isAuthenticated: true, 
          isLoading: false 
        });
        return;
      }

      // Get initial session
      const { data: { session } } = await supabase.auth.getSession();
      
      set({ 
        session, 
        user: session?.user ?? null,
        isAuthenticated: !!session,
        isLoading: false 
      });

      // Listen for auth changes
      supabase.auth.onAuthStateChange((_event, session) => {
        set({ 
          session, 
          user: session?.user ?? null,
          isAuthenticated: !!session,
          isLoading: false 
        });
      });
    } catch (error) {
      console.error('Auth initialization error:', error);
      set({ isLoading: false });
    }
  },

  signOut: async () => {
    try {
      localStorage.removeItem('salesboost-mock-auth');
      await supabase.auth.signOut();
      set({ session: null, user: null, isAuthenticated: false });
    } catch (error) {
      console.error('Sign out error:', error);
    }
  },
}));
