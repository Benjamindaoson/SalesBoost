import { useEffect, useRef, useCallback } from 'react';

export interface UseSmartPollingOptions {
  /**
   * Initial polling interval in milliseconds
   * @default 5000
   */
  initialInterval?: number;

  /**
   * Maximum polling interval in milliseconds
   * @default 60000
   */
  maxInterval?: number;

  /**
   * Multiplier for exponential backoff
   * @default 1.5
   */
  backoffMultiplier?: number;

  /**
   * Whether to pause polling when tab is hidden
   * @default true
   */
  pauseWhenHidden?: boolean;

  /**
   * Whether polling is enabled
   * @default true
   */
  enabled?: boolean;
}

/**
 * Smart polling hook with exponential backoff and visibility API integration
 * Reduces server load and improves battery life
 *
 * @example
 * ```tsx
 * useSmartPolling(async () => {
 *   const data = await fetchData();
 *   setData(data);
 * }, {
 *   initialInterval: 5000,
 *   maxInterval: 60000,
 *   pauseWhenHidden: true,
 * });
 * ```
 */
export function useSmartPolling(
  callback: () => void | Promise<void>,
  options: UseSmartPollingOptions = {}
) {
  const {
    initialInterval = 5000,
    maxInterval = 60000,
    backoffMultiplier = 1.5,
    pauseWhenHidden = true,
    enabled = true,
  } = options;

  const intervalRef = useRef(initialInterval);
  const timeoutRef = useRef<NodeJS.Timeout>();
  const isVisibleRef = useRef(true);

  // Stable callback reference
  const stableCallback = useCallback(callback, [callback]);

  // Handle visibility change
  useEffect(() => {
    if (!pauseWhenHidden) return;

    const handleVisibilityChange = () => {
      isVisibleRef.current = !document.hidden;

      // Resume polling when tab becomes visible
      if (isVisibleRef.current && enabled) {
        poll();
      } else {
        // Clear timeout when tab is hidden
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [pauseWhenHidden, enabled]);

  // Polling function
  const poll = useCallback(async () => {
    // Don't poll if disabled or tab is hidden
    if (!enabled || (pauseWhenHidden && !isVisibleRef.current)) {
      return;
    }

    try {
      await stableCallback();

      // Reset interval on success
      intervalRef.current = initialInterval;
    } catch (error) {
      console.error('Polling error:', error);

      // Exponential backoff on error
      intervalRef.current = Math.min(
        intervalRef.current * backoffMultiplier,
        maxInterval
      );
    }

    // Schedule next poll
    timeoutRef.current = setTimeout(poll, intervalRef.current);
  }, [
    enabled,
    pauseWhenHidden,
    stableCallback,
    initialInterval,
    maxInterval,
    backoffMultiplier,
  ]);

  // Start polling
  useEffect(() => {
    if (!enabled) return;

    // Initial poll
    poll();

    // Cleanup
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [enabled, poll]);

  // Return current interval for debugging
  return {
    currentInterval: intervalRef.current,
  };
}
