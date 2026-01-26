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
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  session: null,
  isLoading: true,
  isAuthenticated: false,

  initialize: async () => {
    try {
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
      await supabase.auth.signOut();
      set({ session: null, user: null, isAuthenticated: false });
    } catch (error) {
      console.error('Sign out error:', error);
    }
  },
}));
