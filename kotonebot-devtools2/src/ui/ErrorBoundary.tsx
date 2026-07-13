import React from 'react';
import { Button, Intent } from '@blueprintjs/core';
import i18n from '../i18n';

interface Props {
  children: React.ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    console.error('Render error:', error, info);
  }

  handleReset = (): void => {
    this.setState({ error: null });
  };

  render(): React.ReactNode {
    if (this.state.error) {
      return (
        <div style={{ padding: 40, textAlign: 'center' }}>
          <h2>{i18n.t('error.renderCrashed')}</h2>
          <p style={{ color: '#5c7080', marginTop: 8 }}>
            {this.state.error.message}
          </p>
          <Button
            intent={Intent.PRIMARY}
            onClick={() => window.location.reload()}
            style={{ marginTop: 16 }}
          >
            {i18n.t('common.reload')}
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}
