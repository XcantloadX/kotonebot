import { useCallback } from 'react';
import styled from '@emotion/styled';
import { useDebugStore } from '../../store/debugStore';

interface InfoPanelProps {
  /** 信息名称 */
  name: string;
  /** 信息具体内容 */
  details?: string;
  /** 图片映射 */
  imagesMap?: Map<string, string>;
}

const PanelContainer = styled.div`
  position: relative;
  height: 100%;
  background-color: #fff;
  overflow: hidden;
`;

const ScrollContainer = styled.div`
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
`;

const MethodContainer = styled.div`
  padding: 1rem;
  border-bottom: 1px solid #dee2e6;
`;

const MethodName = styled.h2`
  margin: 0 0 1rem 0;
  font-weight: 600;
  color: #495057;
`;

const MethodDetails = styled.div`
  font-size: 0.9rem;
  white-space: pre-wrap;
  word-break: break-word;
`;


// 解析 [img]url[/img] 标签
function parseImgTags(text: string, img2urlCallback = (k: string) => '/api/read_memory?key=' + k): string {
  // 解析 [img] 标签
  text = text.replace(/\[img\](.*?)\[\/img\]/g, (match, p1) => {
      return `<img src="${img2urlCallback(p1)}" alt="image">`;
  });

  return text;
}

function InfoPanel({
  name,
  details,
  imagesMap
}: InfoPanelProps) {
  const host = useDebugStore(state => state.host);
  const img2urlCallback = useCallback((k: string) => {
    if (imagesMap) {
      return imagesMap.get(k) ?? `http://${host}/api/read_memory?key=${k}`;
    }
    return `http://${host}/api/read_memory?key=${k}`;
  }, [imagesMap, host]);
  return (
    <PanelContainer>
      <ScrollContainer>
        <MethodContainer>
          <MethodName>{name}</MethodName>
          <MethodDetails>
            <div dangerouslySetInnerHTML={{ __html: details ? parseImgTags(details, img2urlCallback) : '' }} />
          </MethodDetails>
        </MethodContainer>
      </ScrollContainer>
    </PanelContainer>
  );
}; 

export default InfoPanel;
