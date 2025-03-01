import React, { useState, useCallback, useEffect } from 'react';
import styled from '@emotion/styled';
import InfoPanel from './InfoPanel';
import { ConnectionStatus } from '../../components/Common/ConnectionStatus';
import MultipleImagesViewer from '../../components/MutipleImagesViewer';
import { Splitable } from '../../components/Splitable';
import { ConnectionStatusEvent, VisualEvent, VisualEventData } from '../../utils/debugClient';
import { useImmer } from 'use-immer';
import { useDebugClient, useDebugStore } from '../../store/debugStore';
import { Button, FormCheck } from 'react-bootstrap';
import { useMessageBox } from '../../hooks/useMessageBox';
import { useFullscreenSpinner } from '../../hooks/useFullscreenSpinner';

function readLocalDump(files: FileList, reportProgress?: (message: string, current: number, total: number) => void) {
  return new Promise<{records: VisualEventData[], images: Map<string, string>}>((resolve, reject) => {
    // 找到JSON文件
    const jsonFile = Array.from(files).find(f => f.name.endsWith('.json'));
    if (!jsonFile) {
      reject(new Error('未找到 JSON 文件'));
      return;
    }

    // 读取JSON文件
    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        const text = e.target?.result as string;
        const lines = text.split('\n').filter(line => line.trim());
        const records: VisualEventData[] = [];
        
        // 读取所有图像文件
        const imageFiles = Array.from(files).filter(f => 
          f.type.startsWith('image/') || f.name.endsWith('.png') || f.name.endsWith('.jpg')
        );
        
        const imageMap = new Map<string, string>();
        
        // 将所有图像转换为Data URL
        let current = 0;
        const total = imageFiles.length;
        for (const imageFile of imageFiles) {
          reportProgress?.(imageFile.name, current, total);
          const dataUrl = await new Promise<string>((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = e => resolve(e.target?.result as string);
            reader.onerror = reject;
            reader.readAsDataURL(imageFile);
          });
          imageMap.set(imageFile.name.replace(/\.[^/.]+$/, ''), dataUrl);
          current++;
        }

        // 解析JSON并替换图像路径
        for (const line of lines) {
          try {
            const data = JSON.parse(line);
            if (!data.image || !data.name || !data.details)
              throw new Error('JSON文件格式错误');
            records.push(data);
          } catch {
            console.error('无效的JSON行:', line);
          }
        }
        
        resolve({records, images: imageMap});
      } catch (err) {
        console.error('读取dump文件时出错:', err);
        reject(err);
      }
    };
    
    reader.onerror = () => reject(new Error('读取JSON文件失败'));
    reader.readAsText(jsonFile);
  });
}

const LayoutContainer = styled.div`
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
`;

const MainContent = styled.div`
  flex: 1;
  display: flex;
  overflow: hidden;
`;

const ViewerContainer = styled.div`
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%;
`;

const ToolbarContainer = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 0.5rem;
  background-color: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
  height: 42px;
`;

const ToolbarButton = styled(Button)`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.75rem;
  font-size: 0.875rem;

  i {
    font-size: 1rem;
  }
`;

export const MainLayout: React.FC = () => {
  const client = useDebugClient();
  const host = useDebugStore(state => state.host);
  const [isConnected, setIsConnected] = useState(false);
  const [records, updateRecords] = useImmer<VisualEventData[]>([]);
  const [index, setIndex] = useState(0);
  const [imageIndex, setImageIndex] = useState(0);
  const [isLocalMode, setIsLocalMode] = useState(false);
  const [localImageMap, setLocalImageMap] = useState<Map<string, string>>();
  const { ok, MessageBoxComponent } = useMessageBox();
  const spinner = useFullscreenSpinner();

  // 处理本地文件打开
  const handleOpenLocal = useCallback(async () => {
    try {
      const input = document.createElement('input');
      input.type = 'file';
      input.webkitdirectory = true; // 允许选择文件夹
      // @ts-expect-error https://stackoverflow.com/questions/72787050/typescript-upload-directory-property-directory-does-not-exist-on-type
      input.directory = true; // 允许选择文件夹
      
      input.onchange = async (e) => {
        const files = (e.target as HTMLInputElement).files;
        if (!files || files.length === 0) return;
        
        try {
          const {records, images} = await readLocalDump(files, (message, current, total) => {
            spinner.show(`读取文件夹中... ${current}/${total}`);
          });
          spinner.hide();
          setLocalImageMap(images);

          console.log('VisualEventData from local directory:', records);
          if (records.length > 0) {
            setIsLocalMode(true);
            updateRecords(() => records);
            setIndex(0);
            setImageIndex(0);
          } else {
            await ok({
              title: '提示',
              text: '文件夹中没有找到有效的记录'
            });
          }
        } catch (err) {
          console.error('Error reading local directory:', err);
          await ok({
            title: '错误',
            text: '读取文件夹失败：' + (err as Error).message
          });
        }
      };
      
      input.click();
    } catch (err) {
      console.error('Error opening local directory:', err);
      await ok({
        title: '错误',
        text: '打开文件夹失败：' + (err as Error).message
      });
    }
  }, [spinner, localImageMap, updateRecords, ok]);

  // 清除记录
  const handleClearRecords = useCallback(() => {
    updateRecords(() => []);
    setIndex(0);
    setImageIndex(0);
  }, [updateRecords]);

  // WS 客户端初始化
  const handleVisualEvent = useCallback((event: VisualEvent) => {
    if (isLocalMode)
      return;
    updateRecords(draft => {
      draft.push(event.data);
    });
  }, [updateRecords, isLocalMode]);
  const handleConnectionStatus = useCallback((event: ConnectionStatusEvent) => {
    setIsConnected(event.connected);
  }, [setIsConnected]);


  useEffect(() => {
    const _client = client;
    _client.addEventListener('connectionStatus', handleConnectionStatus);
    _client.addEventListener('visual', handleVisualEvent);

    return () => {
      _client.removeEventListener('connectionStatus', handleConnectionStatus);
      _client.removeEventListener('visual', handleVisualEvent);
    };
  }, [client, handleVisualEvent, handleConnectionStatus]);


  useEffect(() => {
    if (index === records.length - 1) {
      setIndex(records.length - 1);
    }
  }, [records, index]);

  return (
    <LayoutContainer>
      {MessageBoxComponent}
      <ToolbarContainer>
        {!isLocalMode && <ConnectionStatus connected={isConnected} />}
        <FormCheck
          type="switch"
          checked={isLocalMode}
          onClick={() => setIsLocalMode(!isLocalMode)}
          label="本地模式"
        />
        <ToolbarButton
          variant="outline-primary"
          onClick={handleOpenLocal}
        >
          <i className="bi bi-folder2-open"></i>
          打开
        </ToolbarButton>
        
        <ToolbarButton
          variant="outline-danger"
          onClick={handleClearRecords}
        >
          <i className="bi bi-trash"></i>
          清除记录
        </ToolbarButton>
      </ToolbarContainer>
      <MainContent>
        <Splitable>
          <ViewerContainer>
            <MultipleImagesViewer
              currentGroup={{
                mainIndex: 0,
                images: !isLocalMode ?
                  (records[index]?.image.value.map(item => 'http://' + host + '/api/read_memory?key=' + item))
                  : (records[index]?.image.value.map(item => localImageMap?.get(item) ?? 'error')),
              }}
              groupIndex={index}
              imageIndex={imageIndex}
              groupCount={records.length}
              onGotoGroup={(i) => {
                setIndex(i);
                setImageIndex(0);
              }}
              onGotoImage={setImageIndex}
            />
          </ViewerContainer>
          <InfoPanel
            name={records[index]?.name}
            details={records[index]?.details}
            imagesMap={isLocalMode ? localImageMap : undefined}
            timeDiff={index > 0 ? records[index]?.timestamp - records[index - 1]?.timestamp : undefined}
          />
        </Splitable>
      </MainContent>
    </LayoutContainer>
  );
}; 