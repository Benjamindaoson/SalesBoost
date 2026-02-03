import * as Sentry from '@sentry/react';
import { env, features, isProd } from '@/config/env';

/**
 * Initialize Sentry error tracking and performance monitoring
 * Only runs in production if DSN is configured
 */
export function initSentry() {
  // Only initialize in production with valid DSN
  if (!isProd || !env.VITE_SENTRY_DSN || !features.errorReportingEnabled) {
    console.log('Sentry disabled:', {
      isProd,
      hasDSN: !!env.VITE_SENTRY_DSN,
      enabled: features.errorReportingEnabled,
    });
    return;
  }

  Sentry.init({
    dsn: env.VITE_SENTRY_DSN,

    // Performance Monitoring
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],

    // Performance Monitoring sample rate
    // 1.0 = 100% of transactions, adjust for production
    tracesSampleRate: isProd ? 0.1 : 1.0,

    // Session Replay sample rates
    // Capture 10% of all sessions
    replaysSessionSampleRate: 0.1,
    // Capture 100% of sessions with errors
    replaysOnErrorSampleRate: 1.0,

    // Environment
    environment: env.MODE,

    // Release tracking
    release: `salesboost-frontend@${import.meta.env.VITE_APP_VERSION || 'dev'}`,

    // Before send hook - filter sensitive data
    beforeSend(event, hint) {
      // Filter out sensitive data
      if (event.request?.headers) {
        delete event.request.headers['Authorization'];
        delete event.request.headers['Cookie'];
      }

      // Don't send events in development
      if (!isProd) {
        console.log('Sentry event (dev):', event);
        return null;
      }

      return event;
    },

    // Ignore certain errors
    ignoreErrors: [
      // Browser extensions
      'top.GLOBALS',
      'chrome-extension://',
      'moz-extension://',
      // Network errors
      'NetworkError',
      'Failed to fetch',
      // Cancelled requests
      'AbortError',
      'Request aborted',
    ],

    // Deny URLs (don't track errors from these sources)
    denyUrls: [
      // Browser extensions
      /extensions\//i,
      /^chrome:\/\//i,
      /^moz-extension:\/\//i,
    ],
  });

  console.log('Sentry initialized successfully');
}

/**
 * Manually capture an exception
 */
export function captureException(error: Error, context?: Record<string, any>) {
  if (!features.errorReportingEnabled) return;

  Sentry.captureException(error, {
    extra: context,
  });
}

/**
 * Manually capture a message
 */
export function captureMessage(message: string, level: Sentry.SeverityLevel = 'info') {
  if (!features.errorReportingEnabled) return;

  Sentry.captureMessage(message, level);
}

/**
 * Set user context for error tracking
 */
export function setUser(user: { id: string; email?: string; username?: string } | null) {
  if (!features.errorReportingEnabled) return;

  Sentry.setUser(user);
}

/**
 * Add breadcrumb for debugging
 */
export function addBreadcrumb(breadcrumb: {
  message: string;
  category?: string;
  level?: Sentry.SeverityLevel;
  data?: Record<string, any>;
}) {
  if (!features.errorReportingEnabled) return;

  Sentry.addBreadcrumb(breadcrumb);
}
