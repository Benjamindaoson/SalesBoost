import { onCLS, onFCP, onLCP, onTTFB, onINP, type Metric } from 'web-vitals';
import { features } from '@/config/env';

/**
 * Web Vitals thresholds (Google's recommended values)
 */
const THRESHOLDS = {
  CLS: { good: 0.1, needsImprovement: 0.25 },
  FID: { good: 100, needsImprovement: 300 },
  FCP: { good: 1800, needsImprovement: 3000 },
  LCP: { good: 2500, needsImprovement: 4000 },
  TTFB: { good: 800, needsImprovement: 1800 },
  INP: { good: 200, needsImprovement: 500 },
};

/**
 * Get rating for a metric value
 */
function getRating(name: string, value: number): 'good' | 'needs-improvement' | 'poor' {
  const threshold = THRESHOLDS[name as keyof typeof THRESHOLDS];
  if (!threshold) return 'good';

  if (value <= threshold.good) return 'good';
  if (value <= threshold.needsImprovement) return 'needs-improvement';
  return 'poor';
}

/**
 * Report metric to analytics
 */
function reportMetric(metric: Metric) {
  const rating = getRating(metric.name, metric.value);

  console.log(`[Web Vitals] ${metric.name}:`, {
    value: metric.value,
    rating,
    id: metric.id,
    navigationType: metric.navigationType,
  });

  // Send to analytics if enabled
  if (features.analyticsEnabled && window.gtag) {
    window.gtag('event', metric.name, {
      value: Math.round(metric.name === 'CLS' ? metric.value * 1000 : metric.value),
      event_category: 'Web Vitals',
      event_label: metric.id,
      non_interaction: true,
    });
  }

  // Send to custom analytics endpoint
  if (features.analyticsEnabled) {
    sendToAnalytics({
      metric: metric.name,
      value: metric.value,
      rating,
      id: metric.id,
      navigationType: metric.navigationType,
    });
  }
}

/**
 * Send metrics to custom analytics endpoint
 */
async function sendToAnalytics(data: any) {
  try {
    // Use sendBeacon for reliability (works even when page is unloading)
    if (navigator.sendBeacon) {
      const blob = new Blob([JSON.stringify(data)], { type: 'application/json' });
      navigator.sendBeacon('/api/v1/analytics/web-vitals', blob);
    } else {
      // Fallback to fetch
      await fetch('/api/v1/analytics/web-vitals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
        keepalive: true,
      });
    }
  } catch (error) {
    console.error('Failed to send web vitals:', error);
  }
}

/**
 * Initialize Web Vitals monitoring
 * Tracks Core Web Vitals and reports to analytics
 */
export function initWebVitals() {
  if (!features.analyticsEnabled) {
    console.log('Web Vitals monitoring disabled');
    return;
  }

  // Cumulative Layout Shift (CLS)
  // Measures visual stability
  // Good: < 0.1, Needs Improvement: < 0.25, Poor: >= 0.25
  onCLS(reportMetric);

  // First Input Delay (FID) - Deprecated in v4, replaced by INP
  // Measures interactivity
  // onFID(reportMetric);

  // First Contentful Paint (FCP)
  // Measures loading performance
  // Good: < 1.8s, Needs Improvement: < 3s, Poor: >= 3s
  onFCP(reportMetric);

  // Largest Contentful Paint (LCP)
  // Measures loading performance
  // Good: < 2.5s, Needs Improvement: < 4s, Poor: >= 4s
  onLCP(reportMetric);

  // Time to First Byte (TTFB)
  // Measures server response time
  // Good: < 800ms, Needs Improvement: < 1800ms, Poor: >= 1800ms
  onTTFB(reportMetric);

  // Interaction to Next Paint (INP)
  // Measures responsiveness
  // Good: < 200ms, Needs Improvement: < 500ms, Poor: >= 500ms
  onINP(reportMetric);

  console.log('Web Vitals monitoring initialized');
}

/**
 * Get current Web Vitals snapshot
 */
export async function getWebVitalsSnapshot(): Promise<Record<string, number>> {
  return new Promise((resolve) => {
    const metrics: Record<string, number> = {};

    const checkComplete = () => {
      if (Object.keys(metrics).length >= 6) {
        resolve(metrics);
      }
    };

    onCLS((metric) => {
      metrics.CLS = metric.value;
      checkComplete();
    });
    // onFID removed
    onFCP((metric) => {
      metrics.FCP = metric.value;
      checkComplete();
    });
    onLCP((metric) => {
      metrics.LCP = metric.value;
      checkComplete();
    });
    onTTFB((metric) => {
      metrics.TTFB = metric.value;
      checkComplete();
    });
    onINP((metric) => {
      metrics.INP = metric.value;
      checkComplete();
    });

    // Timeout after 5 seconds
    setTimeout(() => resolve(metrics), 5000);
  });
}

// Type augmentation for gtag
declare global {
  interface Window {
    gtag?: (...args: any[]) => void;
  }
}
