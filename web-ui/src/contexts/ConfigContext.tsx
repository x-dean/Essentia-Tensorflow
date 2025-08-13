import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getConfig, updateConfig, reloadConfigs } from '../services/api';

// Configuration state interface
interface ConfigState {
  discovery: any;
  analysis: any;
  database: any;
  logging: any;
  app_settings: any;
  isLoading: boolean;
  error: string | null;
}

// Action types
type ConfigAction = 
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_CONFIG'; payload: { section: string; data: any } }
  | { type: 'SET_ALL_CONFIGS'; payload: any }
  | { type: 'CLEAR_ERROR' };

// Initial state
const initialState: ConfigState = {
  discovery: null,
  analysis: null,
  database: null,
  logging: null,
  app_settings: null,
  isLoading: false,
  error: null,
};

// Reducer function
function configReducer(state: ConfigState, action: ConfigAction): ConfigState {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'SET_CONFIG':
      return { 
        ...state, 
        [action.payload.section]: action.payload.data 
      };
    case 'SET_ALL_CONFIGS':
      return { 
        ...state, 
        ...action.payload,
        isLoading: false,
        error: null 
      };
    case 'CLEAR_ERROR':
      return { ...state, error: null };
    default:
      return state;
  }
}

// Context interface
interface ConfigContextType {
  state: ConfigState;
  updateConfigSection: (section: string, data: any) => Promise<void>;
  clearError: () => void;
  refetchConfigs: () => void;
}

// Create context
const ConfigContext = createContext<ConfigContextType | undefined>(undefined);

// Provider component
export const ConfigProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(configReducer, initialState);
  const queryClient = useQueryClient();

  // Fetch all configurations
  const { data: configData, isLoading, error, refetch } = useQuery({
    queryKey: ['config'],
    queryFn: getConfig,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
  });

  // Update configuration mutation
  const updateConfigMutation = useMutation({
    mutationFn: ({ section, data }: { section: string; data: any }) => updateConfig(section, data),
    onSuccess: async (_, variables) => {
      // Reload configs on backend
      try {
        await reloadConfigs();
      } catch (error) {
        console.warn('Failed to reload configs on backend:', error);
      }
      
      // Refetch all configs to get fresh data
      await refetch();
      
      dispatch({ type: 'CLEAR_ERROR' });
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to update configuration';
      dispatch({ type: 'SET_ERROR', payload: errorMessage });
    },
  });

  // Update state when data changes
  useEffect(() => {
    if (configData?.configs) {
      dispatch({ type: 'SET_ALL_CONFIGS', payload: configData.configs });
    }
  }, [configData]);

  // Update loading state
  useEffect(() => {
    dispatch({ type: 'SET_LOADING', payload: isLoading });
  }, [isLoading]);

  // Update error state
  useEffect(() => {
    if (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load configuration';
      dispatch({ type: 'SET_ERROR', payload: errorMessage });
    }
  }, [error]);

  // Update configuration section
  const updateConfigSection = async (section: string, data: any) => {
    dispatch({ type: 'SET_LOADING', payload: true });
    await updateConfigMutation.mutateAsync({ section, data });
  };

  // Clear error
  const clearError = () => {
    dispatch({ type: 'CLEAR_ERROR' });
  };

  // Refetch configurations
  const refetchConfigs = () => {
    refetch();
  };

  const value: ConfigContextType = {
    state,
    updateConfigSection,
    clearError,
    refetchConfigs,
  };

  return (
    <ConfigContext.Provider value={value}>
      {children}
    </ConfigContext.Provider>
  );
};

// Custom hook to use the config context
export const useConfig = () => {
  const context = useContext(ConfigContext);
  if (context === undefined) {
    throw new Error('useConfig must be used within a ConfigProvider');
  }
  return context;
};

// Custom hook for specific config sections
export const useConfigSection = (section: keyof Omit<ConfigState, 'isLoading' | 'error'>) => {
  const { state, updateConfigSection } = useConfig();
  return {
    config: state[section],
    isLoading: state.isLoading,
    error: state.error,
    updateConfig: (data: any) => updateConfigSection(section, data),
  };
};
