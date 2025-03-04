import { useCallback } from 'react';
import styled from '@emotion/styled';
import { useDebugStore } from '../../store/debugStore';
import { Callstack } from '../../utils/debugClient';
import { css } from '@emotion/react';

interface AttributeEntry {
  /** 信息标签 */
  label: string;
  /** 信息值（支持字符串或数字） */
  value: string | number;
}

interface InfoPanelProps {
  /** 信息名称 */
  name: string;
  /** 信息具体内容 */
  details?: string;
  /** 图片映射 */
  imagesMap?: Map<string, string>;
  /** 与上一条记录的时间差（毫秒） */
  attributes: AttributeEntry[];
  /** 调用堆栈 */
  callstacks: Callstack[];
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

const AttributeText = styled.div`
  color: #6c757d;
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
`;

// 解析 [img]url[/img] 标签
function parseImgTags(text: string, img2urlCallback = (k: string) => '/api/read_memory?key=' + k): string {
  text = text.replace(/\[img\](.*?)\[\/img\]/g, (match, p1) => {
      return `<img src="${img2urlCallback(p1)}" alt="image">`;
  });

  return text;
}

function CallstackList({ callstacks }: { callstacks: Callstack[] }) {
  const listStyle = css`
    list-style-type: none; 
    padding: 0; 
    li {
      padding: 0.2rem;
      transition: background-color 0.1s;
      cursor: pointer;
      &:hover {
        background-color: #f2f2f2;
      }
    }
  `;
  const methodIconStyle = css`margin-right: 5px;`;
  const entryNameStyle = css`color: #000; font-size: 0.9rem; `;
  const entryFileStyle = css`float: right; color: #6c757d; font-size: 0.9rem; `;
  const entryLineStyle = css`background-color: #dddddd; padding: 0.2rem; border-radius: 5px; `;

  const iconSrcs = {
    function: '/icons/symbol-method.svg',
    module: '/icons/symbol-file.svg',
    method: '/icons/symbol-class.svg',
    lambda: '/icons/symbol-file.svg',
  };

  return (
    <div>
      <ul css={listStyle}>
        {callstacks.map((entry, index) => (
        <li key={index} onClick={() => window.open(entry.url, '_blank')}>
          {entry.type && <img src={iconSrcs[entry.type]} alt={`${entry.type} icon`} css={methodIconStyle} />}
          <span css={entryNameStyle}>{entry.name}</span> 
          <span css={entryFileStyle}>
            <span css={css`margin-right: 5px;`}>{entry.file.split(/[/\\]/).pop()}</span> 
            <span css={entryLineStyle}>{entry.line}</span>
          </span>
        </li>
      ))}
      </ul>
    </div>
  );
}

function InfoPanel({
  name,
  details,
  imagesMap,
  attributes,
  callstacks,
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
          
          {attributes.map((info, index) => (
            <AttributeText key={index}>
              {info.label}：{info.value}
            </AttributeText>
          ))}

          {callstacks?.length > 0 && <CallstackList callstacks={callstacks} />}
          <MethodDetails>
            <div dangerouslySetInnerHTML={{ __html: details ? parseImgTags(details, img2urlCallback) : '' }} />
          </MethodDetails>
        </MethodContainer>
      </ScrollContainer>
    </PanelContainer>
  );
}; 

export default InfoPanel;
