/**
 * Error Boundary - React错误边界组件
 * 捕获和处理组件树中的错误，提供友好的错误界面
 */
import React, { Component, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
  errorId: string | null;
}

class ErrorBoundary extends Component<Props, State> {
  private retryCount = 0;
  private maxRetries = 3;

  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    // 生成错误ID用于追踪
    const errorId = `err_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    return {
      hasError: true,
      error,
      errorId,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    this.setState({
      errorInfo,
    });

    // 调用自定义错误处理函数
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // 发送错误到监控服务
    this.reportError(error, errorInfo);
  }

  private reportError = (error: Error, errorInfo: React.ErrorInfo) => {
    try {
      // 发送到自定义错误上报服务
      fetch('/api/v1/errors/report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          errorId: this.state.errorId,
          message: error.message,
          stack: error.stack,
          componentStack: errorInfo.componentStack,
          userAgent: navigator.userAgent,
          timestamp: new Date().toISOString(),
          url: window.location.href,
        }),
      }).catch(err => {
        console.error('Failed to report error:', err);
      });
    } catch (reportingError) {
      console.error('Error reporting failed:', reportingError);
    }
  };

  private handleRetry = () => {
    if (this.retryCount < this.maxRetries) {
      this.retryCount++;
      
      this.setState({
        hasError: false,
        error: null,
        errorInfo: null,
        errorId: null,
      });
    }
  };

  private handleGoHome = () => {
    window.location.href = '/';
  };

  private handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      // 如果提供了自定义fallback，使用它
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // 默认错误界面
      return (
        <div style={{
          minHeight: '100vh',
          backgroundColor: '#f9fafb',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '1rem'
        }}>
          <div style={{
            maxWidth: '448px',
            width: '100%',
            backgroundColor: 'white',
            borderRadius: '0.5rem',
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
            padding: '1.5rem'
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '3rem',
              height: '3rem',
              backgroundColor: '#fee2e2',
              borderRadius: '50%',
              margin: '0 auto 1rem'
            }}>
              <AlertTriangle size={24} color="#dc2626" />
            </div>
            
            <h1 style={{
              fontSize: '1.25rem',
              fontWeight: '600',
              color: '#111827',
              textAlign: 'center',
              marginBottom: '0.5rem'
            }}>
              出现了意外错误
            </h1>
            
            <p style={{
              color: '#6b7280',
              textAlign: 'center',
              marginBottom: '1.5rem'
            }}>
              很抱歉，应用遇到了一个意外错误。我们已经记录了这个问题，正在努力修复。
            </p>

            {this.state.errorId && (
              <div style={{
                backgroundColor: '#f3f4f6',
                borderRadius: '0.5rem',
                padding: '0.75rem',
                marginBottom: '1.5rem'
              }}>
                <p style={{
                  fontSize: '0.875rem',
                  color: '#6b7280',
                  margin: 0
                }}>
                  错误ID: <code style={{
                    fontSize: '0.75rem',
                    backgroundColor: '#e5e7eb',
                    padding: '0.125rem 0.25rem',
                    borderRadius: '0.25rem'
                  }}>{this.state.errorId}</code>
                </p>
              </div>
            )}

            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '0.75rem'
            }}>
              {this.retryCount < this.maxRetries && (
                <button
                  onClick={this.handleRetry}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.5rem',
                    backgroundColor: '#3b82f6',
                    color: 'white',
                    padding: '0.5rem 1rem',
                    borderRadius: '0.5rem',
                    border: 'none',
                    cursor: 'pointer',
                    fontSize: '0.875rem'
                  }}
                >
                  <RefreshCw size={16} />
                  重试 ({this.retryCount + 1}/{this.maxRetries})
                </button>
              )}
              
              <button
                onClick={this.handleGoHome}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                  backgroundColor: '#6b7280',
                  color: 'white',
                  padding: '0.5rem 1rem',
                  borderRadius: '0.5rem',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '0.875rem'
                }}
              >
                <Home size={16} />
                返回首页
              </button>
              
              <button
                onClick={this.handleReload}
                style={{
                  color: '#6b7280',
                  padding: '0.5rem 1rem',
                  borderRadius: '0.5rem',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  backgroundColor: 'transparent'
                }}
              >
                刷新页面
              </button>
            </div>

            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details style={{
                marginTop: '1.5rem',
                paddingTop: '1.5rem',
                borderTop: '1px solid #e5e7eb'
              }}>
                <summary style={{
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  fontWeight: '500',
                  color: '#374151',
                  marginBottom: '0.75rem'
                }}>
                  开发者调试信息
                </summary>
                <div style={{
                  fontSize: '0.75rem',
                  color: '#6b7280',
                  fontFamily: 'monospace'
                }}>
                  <div style={{ marginBottom: '0.5rem' }}>
                    <strong>错误:</strong>
                    <pre style={{
                      marginTop: '0.25rem',
                      backgroundColor: '#fef2f2',
                      padding: '0.5rem',
                      borderRadius: '0.25rem',
                      overflow: 'auto',
                      margin: 0
                    }}>
                      {this.state.error.message}
                    </pre>
                  </div>
                  {this.state.error.stack && (
                    <div style={{ marginBottom: '0.5rem' }}>
                      <strong>堆栈跟踪:</strong>
                      <pre style={{
                        marginTop: '0.25rem',
                        backgroundColor: '#fef2f2',
                        padding: '0.5rem',
                        borderRadius: '0.25rem',
                        overflow: 'auto',
                        maxHeight: '8rem',
                        margin: 0
                      }}>
                        {this.state.error.stack}
                      </pre>
                    </div>
                  )}
                  {this.state.errorInfo?.componentStack && (
                    <div>
                      <strong>组件堆栈:</strong>
                      <pre style={{
                        marginTop: '0.25rem',
                        backgroundColor: '#eff6ff',
                        padding: '0.5rem',
                        borderRadius: '0.25rem',
                        overflow: 'auto',
                        maxHeight: '8rem',
                        margin: 0
                      }}>
                        {this.state.errorInfo.componentStack}
                      </pre>
                    </div>
                  )}
                </div>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// 导出
export default ErrorBoundary;