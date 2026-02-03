import { supabase } from '@/lib/supabase';

export const authService = {
  async signInWithEmail(email: string) {
    return supabase.auth.signInWithOtp({ 
      email,
      options: {
        emailRedirectTo: window.location.origin
      }
    });
  },

  async verifyOtp(email: string, token: string) {
    return supabase.auth.verifyOtp({
      email,
      token,
      type: 'email'
    });
  },
  
  async signOut() {
    return supabase.auth.signOut();
  },
  
  async getUser() {
    return supabase.auth.getUser();
  },

  async getSession() {
    return supabase.auth.getSession();
  }
};
