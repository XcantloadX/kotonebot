import React from 'react';
import styled from '@emotion/styled';

interface ConnectionStatusProps {
  connected: boolean;
}

const StatusContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.875rem;
`;

const StatusDot = styled.div<{ connected: boolean }>`
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: ${props => props.connected ? '#28a745' : '#dc3545'};
`;

const statusMessages = {
  connected: 'WebSocket 已连接',
  disconnected: 'WebSocket 已断开',
  connecting: 'WebSocket 连接中...'
};

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ connected }) => {
  return (
    <StatusContainer>
      <StatusDot connected={connected} />
      <span>{statusMessages[connected ? 'connected' : 'disconnected']}</span>
    </StatusContainer>
  );
}; 