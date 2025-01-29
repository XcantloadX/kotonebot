import React from 'react';
import styled from '@emotion/styled';
import { Alert, Button } from 'react-bootstrap';

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

const ErrorContainer = styled.div`
  padding: 2rem;
  text-align: center;
`;

const ErrorMessage = styled.pre`
  margin: 1rem 0;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 4px;
  text-align: left;
  overflow: auto;
  max-height: 200px;
`;

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error('组件错误:', error);
    console.error('错误详情:', errorInfo);
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null
    });
  };

  render(): React.ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <ErrorContainer>
          <Alert variant="danger">
            <Alert.Heading>发生错误</Alert.Heading>
            <p>组件渲染过程中发生了错误。</p>
            {this.state.error && (
              <ErrorMessage>
                {this.state.error.toString()}
              </ErrorMessage>
            )}
            <Button
              variant="outline-danger"
              onClick={this.handleReset}
            >
              重试
            </Button>
          </Alert>
        </ErrorContainer>
      );
    }

    return this.props.children;
  }
} 