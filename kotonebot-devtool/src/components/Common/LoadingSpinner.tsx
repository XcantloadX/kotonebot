import styled from '@emotion/styled';
import { Spinner } from 'react-bootstrap';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  variant?: string;
  text?: string;
  fullscreen?: boolean;
}

const SpinnerWrapper = styled.div<{ fullscreen?: boolean }>`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  ${props => props.fullscreen && `
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(255, 255, 255, 0.8);
    z-index: 9999;
  `}
`;

const SpinnerText = styled.div`
  margin-top: 1rem;
  color: #666;
  font-size: 0.9rem;
`;

const sizeMap = {
  sm: '1rem',
  md: '2rem',
  lg: '3rem'
};

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  variant = 'primary',
  text,
  fullscreen = false
}) => {
  return (
    <SpinnerWrapper fullscreen={fullscreen}>
      <Spinner
        animation="border"
        variant={variant}
        style={{ width: sizeMap[size], height: sizeMap[size] }}
      />
      {text && <SpinnerText>{text}</SpinnerText>}
    </SpinnerWrapper>
  );
}; 