import React, { useRef } from 'react';
import styled from '@emotion/styled';
import ImageViewer, { ImageViewerRef } from '../components/ImageViewer';
import MultipleImagesViewer from '../components/MutipleImagesViewer';
import { useMessageBox } from '../hooks/useMessageBox';
import { useFullscreenSpinner } from '../hooks/useFullscreenSpinner';

const DemoContainer = styled.div`
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 80%;
  margin: 0 auto;
`;

const ViewerContainer = styled.div`
  height: 500px;
  border: 1px solid #ccc;
  border-radius: 4px;
`;

const ControlPanel = styled.div`
  display: flex;
  gap: 10px;
  align-items: center;
`;

const Button = styled.button`
  padding: 8px 16px;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  
  &:hover {
    background: #f5f5f5;
  }
`;

const Section = styled.section`
  margin-bottom: 40px;
`;

function Demo() {
  const viewerRef = useRef<ImageViewerRef>(null);
  const messageBox = useMessageBox();
  const spinner = useFullscreenSpinner();

  // 示例图片，这里使用一个在线图片
  const demoImage = 'https://picsum.photos/800/600';

  // 多图片查看器的示例数据
  const demoImageGroups = [
    {
      mainIndex: 0,
      images: [
        'https://picsum.photos/800/600?random=1',
        'https://picsum.photos/800/600?random=2',
        'https://picsum.photos/800/600?random=3'
      ]
    },
    {
      mainIndex: 1,
      images: [
        'https://picsum.photos/800/600?random=4',
        'https://picsum.photos/800/600?random=5'
      ]
    },
    {
      mainIndex: 0,
      images: [
        'https://picsum.photos/800/600?random=6',
        'https://picsum.photos/800/600?random=7',
        'https://picsum.photos/800/600?random=8',
        'https://picsum.photos/800/600?random=9'
      ]
    }
  ];

  const handleReset = () => {
    viewerRef.current?.reset('all');
  };

  const handleResetPosition = () => {
    viewerRef.current?.reset('position');
  };

  const handleResetZoom = () => {
    viewerRef.current?.reset('zoom');
  };

  const handleFit = () => {
    viewerRef.current?.fit();
  };

  const handleZoomIn = () => {
    if (viewerRef.current) {
      viewerRef.current.setScale(viewerRef.current.scale + 0.1);
    }
  };

  const handleZoomOut = () => {
    if (viewerRef.current) {
      viewerRef.current.setScale(viewerRef.current.scale - 0.1);
    }
  };

  const handleShowYesNo = async () => {
    const result = await messageBox.yesNo({
      title: '确认操作',
      text: '您确定要执行此操作吗？'
    });
    alert(`您选择了: ${result === 'yes' ? '是' : '否'}`);
  };

  const handleShowOk = async () => {
    await messageBox.ok({
      title: '操作成功',
      text: '数据已成功保存！'
    });
  };

  const handleShowConfirmCancel = async () => {
    const result = await messageBox.confirmCancel({
      title: '删除确认',
      text: '此操作将永久删除所选项目，是否继续？'
    });
    alert(`您选择了: ${result === 'confirm' ? '确认' : '取消'}`);
  };

  const handleShowSpinner = () => {
    spinner.show('加载中...');
    setTimeout(() => {
      spinner.hide();
    }, 3000);
  };

  const handleShowSpinnerWithoutMessage = () => {
    spinner.show();
    setTimeout(() => {
      spinner.hide();
    }, 3000);
  };

  return (
    <DemoContainer>
      {messageBox.MessageBoxComponent}
      <Section>
        <h2>消息框演示</h2>
        <ControlPanel>
          <Button onClick={handleShowYesNo}>是/否对话框</Button>
          <Button onClick={handleShowOk}>提示对话框</Button>
          <Button onClick={handleShowConfirmCancel}>确认/取消对话框</Button>
        </ControlPanel>

        <div>
          <h3>使用说明：</h3>
          <ul>
            <li>点击"是/否对话框"显示带有是/否选项的对话框</li>
            <li>点击"提示对话框"显示只有确定按钮的提示框</li>
            <li>点击"确认/取消对话框"显示带有确认/取消选项的对话框</li>
          </ul>
        </div>
      </Section>

      <Section>
        <h2>全屏加载动画演示</h2>
        <ControlPanel>
          <Button onClick={handleShowSpinner}>显示带消息的加载动画</Button>
          <Button onClick={handleShowSpinnerWithoutMessage}>显示无消息的加载动画</Button>
        </ControlPanel>

        <div>
          <h3>使用说明：</h3>
          <ul>
            <li>点击按钮显示全屏加载动画，3秒后自动关闭</li>
            <li>加载动画会显示在整个应用的最上层</li>
            <li>可以选择是否显示加载消息</li>
          </ul>
        </div>
      </Section>

      <Section>
        <h2>单图片查看器演示</h2>
        
        <ViewerContainer>
          <ImageViewer
            ref={viewerRef}
            image={demoImage}
            zoomable={true}
            movable={true}
          />
        </ViewerContainer>

        <ControlPanel>
          <Button onClick={handleZoomIn}>放大</Button>
          <Button onClick={handleZoomOut}>缩小</Button>
          <Button onClick={handleFit}>适应</Button>
          <Button onClick={handleReset}>完全重置</Button>
          <Button onClick={handleResetPosition}>重置位置</Button>
          <Button onClick={handleResetZoom}>重置缩放</Button>
        </ControlPanel>

        <div>
          <h3>使用说明：</h3>
          <ul>
            <li>鼠标拖动可移动图片</li>
            <li>鼠标滚轮可缩放图片</li>
            <li>点击"适应"按钮使图片适应容器大小</li>
            <li>点击"重置位置"只重置图片位置</li>
            <li>点击"重置缩放"只重置图片缩放</li>
            <li>点击"完全重置"同时重置位置和缩放</li>
          </ul>
        </div>
      </Section>

      <Section>
        <h2>多图片查看器演示</h2>
        
        <ViewerContainer>
          <MultipleImagesViewer images={demoImageGroups} />
        </ViewerContainer>

        <div>
          <h3>使用说明：</h3>
          <ul>
            <li>使用工具栏上的按钮或滑块切换图片组</li>
            <li>使用组内导航按钮切换当前组内的图片</li>
            <li>支持键盘快捷键：左右方向键切换组，Home/End 跳转到第一组/最后一组</li>
            <li>可以通过下载按钮下载当前图片组的所有图片</li>
            <li>锁定视图选项可以在切换图片时保持当前的缩放和位置</li>
            <li>所有图片支持鼠标拖动和滚轮缩放</li>
          </ul>
        </div>
      </Section>
    </DemoContainer>
  );
}

export default Demo;
