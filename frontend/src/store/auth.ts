import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { apiClient } from '../utils/api';
import { EmployeeProfile, Employee } from '../types';

interface AuthState {
  user: EmployeeProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (employeeId: string, password: string, rememberMe: boolean) => Promise<void>;
  logout: (revokeAll?: boolean) => Promise<void>;
  refreshProfile: () => Promise<void>;
  updateProfile: (user: EmployeeProfile) => void;
  setUser: (user: EmployeeProfile | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
  hasRole: (...roles: string[]) => boolean;
  canManage: (targetEmployee: Employee) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: true,
      error: null,

      login: async (employeeId: string, password: string, rememberMe: boolean) => {
        set({ isLoading: true, error: null });
        try {
          const response = await apiClient.login({ employee_id: employeeId, password, remember_me: rememberMe });
          const user = response.data.employee;
          set({ user, isAuthenticated: true, isLoading: false, error: null });
        } catch (error: unknown) {
          const message = error instanceof Error ? error.message : 'Login failed';
          set({ isLoading: false, error: message, user: null, isAuthenticated: false });
          throw error;
        }
      },

      logout: async (revokeAll = false) => {
        set({ isLoading: true });
        try {
          await apiClient.logout(revokeAll);
        } catch {
          // Ignore logout errors
        } finally {
          set({ user: null, isAuthenticated: false, isLoading: false, error: null });
        }
      },

      refreshProfile: async () => {
        try {
          const response = await apiClient.getProfile();
          const user = response.data;
          set({ user, isAuthenticated: true });
        } catch {
          set({ user: null, isAuthenticated: false });
        }
      },

      updateProfile: (user) => set({ user, isAuthenticated: true }),

      setUser: (user) => set({ user, isAuthenticated: !!user }),
      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
      clearError: () => set({ error: null }),

      hasRole: (...roles: string[]) => {
        const user = get().user;
        return user ? roles.includes(user.role) : false;
      },

      canManage: (targetEmployee: Employee) => {
        const user = get().user;
        if (!user) return false;

        // Super admin can manage anyone
        if (user.role === 'super_admin') return true;

        // Admin can manage anyone in their company
        if (user.role === 'admin') return user.company_id === targetEmployee.company_id;

        // Manager can manage employees in their department
        if (user.role === 'manager') {
          return (
            user.company_id === targetEmployee.company_id &&
            user.department_id === targetEmployee.department_id &&
            targetEmployee.role === 'employee'
          );
        }

        return false;
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

let authStoreInstance: ReturnType<typeof useAuthStore.getState> | null = null;

export function getAuthStore() {
  if (!authStoreInstance) {
    authStoreInstance = useAuthStore.getState();
  }
  return authStoreInstance;
}

// Initialize auth on app load
export async function initializeAuth() {
  const store = useAuthStore.getState();
  if (store.isAuthenticated && store.user) {
    try {
      await store.refreshProfile();
    } catch {
      store.logout();
    }
  } else {
    store.setLoading(false);
  }
}
