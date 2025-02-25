import { useRef, useState } from 'react';
import styled from '@emotion/styled';
import { useNavigate, useLocation, Routes, Route, Navigate } from 'react-router-dom';
import ImageViewer, { ImageViewerRef } from '../components/ImageViewer';
import MultipleImagesViewer from '../components/MutipleImagesViewer';
import { useMessageBox } from '../hooks/useMessageBox';
import { useFullscreenSpinner } from '../hooks/useFullscreenSpinner';
import ImageEditor, { ImageEditorRef } from '../components/ImageEditor/ImageEditor';
import { Annotation, RectPoints, Tool as EditorTool } from '../components/ImageEditor/types';
import RectBox from '../components/ImageEditor/RectBox';
import RectMask from '../components/ImageEditor/RectMask';
import FormRange from 'react-bootstrap/esm/FormRange';
import NativeDiv from '../components/NativeDiv';
import { AnnotationChangedEvent } from '../components/ImageEditor/ImageEditor';
import { SideToolBar } from '../components/SideToolBar';
import type { Tool as SideBarTool } from '../components/SideToolBar';
import PropertyGrid, { Property, PropertyCategory } from '../components/PropertyGrid';
import ImageViewerModal, { useImageViewerModal } from '../components/ImageViewerModal';
import { useToast } from '../components/ToastMessage';
import VSToolBar, { Tool, ToolBarItem, DropdownOption } from '../components/VSToolBar';
import { Splitable } from '../components/Splitable';
import { useFormModal } from '../hooks/useFormModal';
import AutocompleteInput from '../components/AutocompleteInput';
import Form from 'react-bootstrap/Form';

// 布局相关的样式组件
const DemoContainer = styled.div`
  display: flex;
  height: 100vh;
  width: 100%;
`;

const Sidebar = styled.div`
  width: 200px;
  background-color: #f5f5f5;
  padding: 20px;
  border-right: 1px solid #ddd;
  overflow-y: auto;
  height: 100vh;
`;

const Content = styled.div`
  flex: 1;
  padding: 20px;
  overflow-y: auto;
`;

const MenuItem = styled.div<{ active: boolean }>`
  padding: 10px;
  margin-bottom: 8px;
  cursor: pointer;
  border-radius: 4px;
  background-color: ${props => props.active ? '#e0e0e0' : 'transparent'};
  
  &:hover {
    background-color: ${props => props.active ? '#e0e0e0' : '#eaeaea'};
  }
`;

// 通用样式组件
const ViewerContainer = styled.div`
  height: 500px;
  border: 1px solid #ccc;
  border-radius: 4px;
`;

const ControlPanel = styled.div`
  display: flex;
  gap: 10px;
  align-items: center;
  margin: 20px 0;
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

// 新增 RectBox 演示相关的样式组件
const RectBoxContainer = styled.div`
  width: 100%;
  height: 400px;
  background-color: #2c2c2c;
  position: relative;
  border-radius: 4px;
  overflow: hidden;
`;

const RectBoxPlayground = styled.div`
  width: 100%;
  height: 100%;
  position: relative;
`;

const ModeSelect = styled.select`
  padding: 8px;
  border-radius: 4px;
  margin-right: 10px;
`;

// 添加 NativeDiv 演示组件的样式
const NativeDivPlayground = styled.div`
  width: 100%;
  height: 400px;
  background-color: #f0f0f0;
  position: relative;
  border-radius: 4px;
  padding: 20px;
`;

const DemoNativeDiv = styled(NativeDiv)`
  width: 200px;
  height: 200px;
  background-color: #4a90e2;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  cursor: pointer;
  transition: transform 0.2s;
  user-select: none;

  &:hover {
    transform: scale(1.05);
  }
`;

// 图片标注器相关的样式组件
const EditorLayout = styled.div`
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
`;

const EditorMain = styled.div`
  flex: 7;
  display: flex;
  flex-direction: column;
`;

const EditorSidebar = styled.div`
  flex: 3;
  background: #f5f5f5;
  border-radius: 4px;
  padding: 15px;
  height: 500px;
  overflow-y: auto;
`;

const AnnotationItem = styled.div`
  padding: 10px;
  background: white;
  border-radius: 4px;
  margin-bottom: 10px;
  border: 1px solid #ddd;

  &:hover {
    border-color: #aaa;
  }
`;

// 消息框演示组件
function MessageBoxDemo(): JSX.Element {
  const messageBox = useMessageBox();

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

  return (
    <div>
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
      {messageBox.MessageBoxComponent}
    </div>
  );
}

// 加载动画演示组件
function SpinnerDemo(): JSX.Element {
  const spinner = useFullscreenSpinner();

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
    <div>
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
    </div>
  );
}

// 添加 Toast 消息演示组件
function ToastMessageDemo(): JSX.Element {
  const { showToast, ToastComponent } = useToast();

  const handleShowSuccess = () => {
    showToast('success', '成功', '操作已成功完成！');
  };

  const handleShowError = () => {
    showToast('danger', '错误', '操作执行失败，请重试。');
  };

  const handleShowInfo = () => {
    showToast('info', '提示', '这是一条信息提示。');
  };

  const handleShowWarning = () => {
    showToast('warning', '警告', '请注意，这是一条警告消息。');
  };

  const handleShowCustomDuration = () => {
    showToast('info', '自定义时长', '这条消息会显示 10 秒钟。', 10000);
  };

  return (
    <div>
      <h2>Toast 消息演示</h2>
      <ControlPanel>
        <Button onClick={handleShowSuccess}>显示成功消息</Button>
        <Button onClick={handleShowError}>显示错误消息</Button>
        <Button onClick={handleShowInfo}>显示信息提示</Button>
        <Button onClick={handleShowWarning}>显示警告消息</Button>
        <Button onClick={handleShowCustomDuration}>显示长时消息</Button>
      </ControlPanel>
      {ToastComponent}
      <div>
        <h3>使用说明：</h3>
        <ul>
          <li>点击不同的按钮可以显示不同类型的 Toast 消息</li>
          <li>每种消息类型都有其独特的颜色样式：</li>
          <ul>
            <li>成功消息 - 绿色</li>
            <li>错误消息 - 红色</li>
            <li>信息提示 - 蓝色</li>
            <li>警告消息 - 黄色</li>
          </ul>
          <li>默认情况下，消息会在 3 秒后自动消失</li>
          <li>"显示长时消息"按钮会显示一个持续 10 秒的消息</li>
          <li>可以通过点击消息右上角的关闭按钮手动关闭消息</li>
          <li>多个消息会按顺序堆叠显示</li>
          <li>消息会显示在屏幕右上角</li>
        </ul>
      </div>
    </div>
  );
}

// 单图片查看器演示组件
function SingleImageViewerDemo(): JSX.Element {
  const viewerRef = useRef<ImageViewerRef>(null);
  const demoImage = 'https://picsum.photos/800/600';

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

  return (
    <div>
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
    </div>
  );
}

// 多图片查看器演示组件
function MultipleImagesViewerDemo(): JSX.Element {
  const [currentGroupIndex, setCurrentGroupIndex] = useState(0);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);

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

  return (
    <div>
      <h2>多图片查看器演示</h2>
      <ViewerContainer>
        <MultipleImagesViewer 
          currentGroup={demoImageGroups[currentGroupIndex]}
          groupCount={demoImageGroups.length}
          groupIndex={currentGroupIndex}
          imageIndex={currentImageIndex}
          onGotoGroup={setCurrentGroupIndex}
          onGotoImage={setCurrentImageIndex}
        />
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
    </div>
  );
}

// 图片标注器演示组件
function ImageEditorDemo(): JSX.Element {
  const editorRef = useRef<ImageEditorRef>(null);
  const [showCrosshair, setShowCrosshair] = useState(false);
  const [currentTool, setCurrentTool] = useState<EditorTool>(EditorTool.Drag);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [showMask, setShowMask] = useState(true);
  const [maskAlpha, setMaskAlpha] = useState(0.5);
  const [scaleMode, setScaleMode] = useState<'wheel' | 'ctrlWheel'>('wheel');
  const demoImage = 'https://picsum.photos/800/600';

  const handleEditorReset = () => {
    editorRef.current?.reset();
  };

  const handleEditorZoomIn = () => {
    if (editorRef.current) {
      const currentScale = editorRef.current.getScale();
      editorRef.current.setScale(currentScale * 1.1);
    }
  };

  const handleEditorZoomOut = () => {
    if (editorRef.current) {
      const currentScale = editorRef.current.getScale();
      editorRef.current.setScale(currentScale * 0.9);
    }
  };

  const handleClearAnnotations = () => {
    setAnnotations([]);
  };

  const handleAnnotationChanged = (e: AnnotationChangedEvent) => {
    console.log('AnnotationChangedEvent: ', e);
    if (e.type === 'update') {
      const target = annotations.find(anno => anno.id === e.annotation.id);
      if (target) {
        target.data = e.annotation.data;
      }
      setAnnotations([...annotations]);
    }
    else if (e.type === 'remove') {
      const targetIndex = annotations.findIndex(anno => anno.id === e.annotation.id);
      if (targetIndex !== -1) {
        setAnnotations(prev => {
          const newAnnotations = [...prev];
          newAnnotations.splice(targetIndex, 1);
          return newAnnotations;
        });
      }
    }
    else if (e.type === 'add') {
      setAnnotations(prev => [e.annotation, ...prev]);
    }
  };

  return (
    <div>
      <h2>图片标注器演示</h2>
      <EditorLayout>
        <EditorMain>
          <ViewerContainer>
            <ImageEditor
              ref={editorRef}
              annotations={annotations}
              image={demoImage}
              initialScale={1}
              showCrosshair={showCrosshair}
              tool={currentTool}
              onAnnotationChanged={handleAnnotationChanged}
              enableMask={showMask}
              maskAlpha={maskAlpha}
              scaleMode={scaleMode}
            />
          </ViewerContainer>
          <ControlPanel>
            <Button onClick={handleEditorZoomIn}>放大</Button>
            <Button onClick={handleEditorZoomOut}>缩小</Button>
            <Button onClick={handleEditorReset}>重置</Button>
            <Button onClick={() => setShowCrosshair(!showCrosshair)}>
              {showCrosshair ? '隐藏准线' : '显示准线'}
            </Button>
            <Button onClick={() => setCurrentTool(currentTool === EditorTool.Drag ? EditorTool.Rect : EditorTool.Drag)}>
              {currentTool === EditorTool.Drag ? '切换到矩形工具' : '切换到拖动工具'}
            </Button>
            <Button onClick={handleClearAnnotations}>清除标注</Button>
            <Button onClick={() => setShowMask(!showMask)}>
              {showMask ? '隐藏遮罩' : '显示遮罩'}
            </Button>
            <Button onClick={() => setScaleMode(mode => mode === 'wheel' ? 'ctrlWheel' : 'wheel')}>
              {scaleMode === 'wheel' ? '切换到Ctrl+滚轮缩放' : '切换到滚轮缩放'}
            </Button>
            <FormRange
              style={{ flex: '0 1 200px' }}
              value={maskAlpha}
              onChange={(e) => setMaskAlpha(Number(e.target.value))}
              min={0}
              max={1}
              step={0.01}
            />
            <span>已标注数量：{annotations.length}</span>
          </ControlPanel>
        </EditorMain>
        <EditorSidebar>
          <h3>标注列表</h3>
          {annotations.length === 0 ? (
            <div style={{ color: '#666', textAlign: 'center', marginTop: '20px' }}>
              暂无标注内容
            </div>
          ) : (
            annotations.map((annotation, index) => (
              <AnnotationItem key={annotation.id}>
                <div>标注 #{index + 1}</div>
                <div>ID: {annotation.id}</div>
                <div>
                  位置: ({annotation.data.x1}, {annotation.data.y1}) - ({annotation.data.x2}, {annotation.data.y2})
                </div>
                <div>
                  尺寸: {Math.abs(annotation.data.x2 - annotation.data.x1)} x {Math.abs(annotation.data.y2 - annotation.data.y1)}
                </div>
              </AnnotationItem>
            ))
          )}
        </EditorSidebar>
      </EditorLayout>
      <div>
        <h3>使用说明：</h3>
        <ul>
          <li>使用鼠标滚轮可以缩放图片</li>
          <li>按住鼠标左键可以拖动图片</li>
          <li>点击"重置"按钮可以恢复初始状态</li>
          <li>使用"放大"和"缩小"按钮可以精确控制缩放级别</li>
          <li>点击"显示准线"按钮可以显示/隐藏鼠标位置的十字准线</li>
          <li>点击"切换到矩形工具"可以进入矩形标注模式</li>
          <li>在矩形工具模式下，按住鼠标左键并拖动可以绘制矩形</li>
          <li>点击"清除标注"可以删除所有已绘制的矩形</li>
          <li>点击"显示遮罩"可以显示/隐藏非标注区域的遮罩</li>
          <li>使用滑块可以调整遮罩的透明度</li>
          <li>点击"切换到Ctrl+滚轮缩放"可以切换缩放模式：</li>
          <ul>
            <li>滚轮缩放模式：直接使用滚轮缩放，Ctrl+滚轮上下移动，Shift+滚轮左右移动</li>
            <li>Ctrl+滚轮缩放模式：使用Ctrl+滚轮缩放，直接滚轮上下移动，Shift+滚轮左右移动</li>
          </ul>
        </ul>
      </div>
    </div>
  );
}

// RectBox 演示组件
function RectBoxDemo(): JSX.Element {
  const [mode, setMode] = useState<'move' | 'resize' | 'none'>('resize');
  const [rect, setRect] = useState({ x1: 50, y1: 50, x2: 200, y2: 200 });
  const [lineColor, setLineColor] = useState('#ffffff');
  const [showRectTip, setShowRectTip] = useState(true);
  const [eventStatus, setEventStatus] = useState({
    isHovered: false,
    lastClickTime: '',
    mousePosition: { x: 0, y: 0 }
  });

  const rectTip = (
    <div style={{
      background: 'rgba(0, 0, 0, 0.7)',
      color: 'white',
      padding: '4px 8px',
      borderRadius: '4px',
      fontSize: '12px',
      whiteSpace: 'nowrap'
    }}>
      {`${rect.x2 - rect.x1}x${rect.y2 - rect.y1}`}
    </div>
  );

  const handleTransform = (points: RectPoints) => {
    setRect(points);
  };

  const handleMouseEnter = (e: MouseEvent) => {
    setEventStatus(prev => ({
      ...prev,
      isHovered: true,
      mousePosition: { x: e.clientX, y: e.clientY }
    }));
  };

  const handleMouseLeave = (e: MouseEvent) => {
    setEventStatus(prev => ({
      ...prev,
      isHovered: false,
      mousePosition: { x: e.clientX, y: e.clientY }
    }));
  };

  const handleClick = (e: MouseEvent) => {
    const now = new Date().toLocaleTimeString();
    setEventStatus(prev => ({
      ...prev,
      lastClickTime: now,
      mousePosition: { x: e.clientX, y: e.clientY }
    }));
  };

  return (
    <div>
      <h2>矩形框组件演示</h2>
      <ControlPanel>
        <ModeSelect value={mode} onChange={(e) => setMode(e.target.value as 'move' | 'resize' | 'none')}>
          <option value="resize">调整大小模式</option>
          <option value="move">移动模式</option>
          <option value="none">禁用模式</option>
        </ModeSelect>
        <input
          type="color"
          value={lineColor}
          onChange={(e) => setLineColor(e.target.value)}
          style={{ marginLeft: '10px', marginRight: '10px' }}
        />
        <Button onClick={() => {
          setRect({ x1: 50, y1: 50, x2: 200, y2: 200 });
        }}>重置位置</Button>
        <Button onClick={() => setShowRectTip(!showRectTip)}>
          {showRectTip ? '隐藏尺寸提示' : '显示尺寸提示'}
        </Button>
      </ControlPanel>
      <RectBoxContainer>
        <RectBoxPlayground>
          <RectBox
            rect={rect}
            mode={mode}
            lineColor={lineColor}
            rectTip={rectTip}
            showRectTip={showRectTip}
            onTransform={handleTransform}
            onNativeMouseEnter={handleMouseEnter}
            onNativeMouseLeave={handleMouseLeave}
            onNativeClick={handleClick}
          />
        </RectBoxPlayground>
      </RectBoxContainer>
      <div style={{ 
        marginTop: '20px', 
        padding: '15px',
        border: '1px solid #ddd',
        borderRadius: '4px',
        backgroundColor: '#f9f9f9'
      }}>
        <h3>事件状态：</h3>
        <ul>
          <li>鼠标悬停状态：{eventStatus.isHovered ? '是' : '否'}</li>
          <li>最后点击时间：{eventStatus.lastClickTime || '未点击'}</li>
          <li>鼠标位置：X: {eventStatus.mousePosition.x}, Y: {eventStatus.mousePosition.y}</li>
        </ul>
      </div>
      <div>
        <h3>使用说明：</h3>
        <ul>
          <li>可以通过下拉菜单切换矩形框的模式</li>
          <li>使用颜色选择器可以改变矩形框的线条颜色</li>
          <li>调整大小模式：可以拖动四个角和四条边调整大小，也可以拖动矩形整体移动</li>
          <li>移动模式：只能拖动矩形整体移动</li>
          <li>禁用模式：无法进行任何操作</li>
          <li>点击"重置位置"可以将矩形恢复到初始位置</li>
          <li>点击"显示/隐藏尺寸提示"可以控制矩形框上方的尺寸提示</li>
          <li>当前位置：起点({rect.x1}, {rect.y1}), 终点({rect.x2}, {rect.y2})</li>
          <li>鼠标移入矩形框时会触发 onMouseEnter 事件</li>
          <li>鼠标移出矩形框时会触发 onMouseLeave 事件</li>
          <li>点击矩形框时会触发 onClick 事件</li>
        </ul>
      </div>
    </div>
  );
}

// RectMask 演示组件
function RectMaskDemo(): JSX.Element {
  const [rects, setRects] = useState<RectPoints[]>([
    { x1: 50, y1: 50, x2: 150, y2: 150 },
    { x1: 200, y1: 150, x2: 350, y2: 250 }
  ]);
  const [alpha, setAlpha] = useState(0.5);
  const [enableTransition, setEnableTransition] = useState(false);

  const handleAddRect = () => {
    setRects([...rects, {
      x1: Math.random() * 300,
      y1: Math.random() * 300,
      x2: Math.random() * 300,
      y2: Math.random() * 300
    }]);
  };

  const handleClear = () => {
    setRects([]);
  };

  return (
    <div>
      <h2>遮罩层演示</h2>
      <ControlPanel>
        <Button onClick={handleAddRect}>添加随机矩形</Button>
        <Button onClick={handleClear}>清除所有</Button>
        <Button onClick={() => setEnableTransition(!enableTransition)}>
          {enableTransition ? '禁用过渡动画' : '启用过渡动画'}
        </Button>
        <FormRange
          style={{ flex: '0 1 300px' }}
          value={alpha}
          onChange={(e) => setAlpha(Number(e.target.value))}
          min={0}
          max={1}
          step={0.01}
        />
        <span>当前矩形数量: {rects.length}</span>
      </ControlPanel>
      <RectBoxContainer>
        <img 
          src="https://picsum.photos/800/600" 
          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          alt="Demo"
        />
        <RectMask 
          rects={rects} 
          alpha={alpha} 
          transition={enableTransition}
          scale={1}
          transform={{ x: 0, y: 0, width: 800, height: 600 }}
        />
      </RectBoxContainer>
      <div>
        <h3>使用说明：</h3>
        <ul>
          <li>图片上方会显示一个半透明的黑色遮罩层</li>
          <li>矩形区域内保持原图清晰可见</li>
          <li>点击"添加随机矩形"可以在随机位置添加一个新的透明区域</li>
          <li>点击"清除所有"可以移除所有透明区域</li>
          <li>点击"启用过渡动画"可以开启/关闭遮罩的过渡动画效果</li>
          <li>当前已添加 {rects.length} 个透明区域</li>
          <li>过渡动画状态：{enableTransition ? '已启用' : '已禁用'}</li>
        </ul>
      </div>
    </div>
  );
}

// NativeDiv 演示组件
function NativeDivDemo(): JSX.Element {
  const [events, setEvents] = useState<Array<{ type: string; time: string; details: string }>>([]);
  const [wheelValue, setWheelValue] = useState(0);

  const addEvent = (type: string, details: string) => {
    const newEvent = {
      type,
      time: new Date().toLocaleTimeString(),
      details
    };
    setEvents(prev => [newEvent, ...prev].slice(0, 10));
  };

  const handleNativeMouseEnter = (e: MouseEvent) => {
    addEvent('mouseenter', `位置：(${e.clientX}, ${e.clientY})`);
  };

  const handleNativeMouseMove = (e: MouseEvent) => {
    addEvent('mousemove', `位置：(${e.clientX}, ${e.clientY})`);
  };

  const handleNativeMouseLeave = (e: MouseEvent) => {
    addEvent('mouseleave', `位置：(${e.clientX}, ${e.clientY})`);
  };

  const handleNativeMouseDown = (e: MouseEvent) => {
    addEvent('mousedown', `位置：(${e.clientX}, ${e.clientY})`);
  };

  const handleNativeClick = (e: MouseEvent) => {
    addEvent('click', `位置：(${e.clientX}, ${e.clientY})`);
  };

  const handleNativeKeyDown = (e: KeyboardEvent) => {
    addEvent('keydown', `按键：${e.key}，键码：${e.keyCode}，修饰键：${[
      e.ctrlKey && 'Ctrl',
      e.shiftKey && 'Shift',
      e.altKey && 'Alt',
      e.metaKey && 'Meta'
    ].filter(Boolean).join('+') || '无'}`);
  };

  const handleNativeKeyUp = (e: KeyboardEvent) => {
    addEvent('keyup', `按键：${e.key}，键码：${e.keyCode}，修饰键：${[
      e.ctrlKey && 'Ctrl',
      e.shiftKey && 'Shift',
      e.altKey && 'Alt',
      e.metaKey && 'Meta'
    ].filter(Boolean).join('+') || '无'}`);
  };

  const handleNativeMouseWheel = (e: WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY;
    setWheelValue(prev => {
      const newValue = prev + delta;
      addEvent('mousewheel', `滚动值：${newValue}，增量：${delta}`);
      return newValue;
    });
  };

  return (
    <div>
      <h2>原生 Div 事件演示</h2>
      <NativeDivPlayground>
        <DemoNativeDiv
          tabIndex={0}
          onNativeMouseEnter={handleNativeMouseEnter}
          onNativeMouseMove={handleNativeMouseMove}
          onNativeMouseLeave={handleNativeMouseLeave}
          onNativeClick={handleNativeClick}
          onNativeMouseDown={handleNativeMouseDown}
          onNativeKeyDown={handleNativeKeyDown}
          onNativeKeyUp={handleNativeKeyUp}
          onNativeMouseWheel={handleNativeMouseWheel}
          style={{ transform: `rotate(${wheelValue * 0.1}deg)` }}
        >
          <div style={{ textAlign: 'center' }}>
            <div>与我互动！</div>
            <small style={{ 
              fontSize: '0.8em', 
              display: 'block',
              marginTop: '8px',
              color: 'rgba(255, 255, 255, 0.8)'
            }}>
              点击获取焦点
              <br />
              然后按键盘或滚动鼠标
            </small>
            <div style={{
              fontSize: '0.8em',
              marginTop: '8px',
              color: 'rgba(255, 255, 255, 0.8)'
            }}>
              滚动值：{wheelValue.toFixed(0)}
            </div>
          </div>
        </DemoNativeDiv>
      </NativeDivPlayground>
      <div style={{ marginTop: '20px' }}>
        <h3>最近的事件：</h3>
        <ul style={{ 
          listStyle: 'none',
          padding: 0,
          margin: 0,
          maxHeight: '200px',
          overflowY: 'auto',
          border: '1px solid #ddd',
          borderRadius: '4px'
        }}>
          {events.map((event, index) => (
            <li key={index} style={{
              padding: '8px',
              borderBottom: index < events.length - 1 ? '1px solid #eee' : 'none',
              backgroundColor: index === 0 ? '#f5f5f5' : 'transparent'
            }}>
              <strong>{event.type}</strong> - {event.time}
              <br />
              <span style={{ color: '#666', fontSize: '0.9em' }}>{event.details}</span>
            </li>
          ))}
        </ul>
      </div>
      <div>
        <h3>使用说明：</h3>
        <ul>
          <li>这个演示展示了 NativeDiv 组件的原生 DOM 事件处理能力</li>
          <li>尝试将鼠标移入蓝色方块来触发 mouseenter 事件</li>
          <li>在方块内移动鼠标来触发 mousemove 事件</li>
          <li>将鼠标移出方块来触发 mouseleave 事件</li>
          <li>点击方块来触发 click 事件</li>
          <li><strong>点击方块获取焦点后，按下键盘按键来触发 keydown 和 keyup 事件</strong></li>
          <li><strong>在方块上滚动鼠标滚轮来旋转方块，并触发 mousewheel 事件</strong></li>
          <li>所有事件都会显示在下方的列表中，包括：</li>
          <ul>
            <li>事件类型和触发时间</li>
            <li>鼠标事件：鼠标位置坐标</li>
            <li>键盘事件：按键名称、键码和修饰键状态</li>
            <li>滚轮事件：滚动值和增量</li>
          </ul>
        </ul>
      </div>
    </div>
  );
}

// 添加 SideToolBar 演示组件
function SideToolBarDemo(): JSX.Element {
  const [count, setCount] = useState(0);
  const [selectedToolId, setSelectedToolId] = useState<string | undefined>(undefined);

  const handleToolSelect = (id: string) => {
    setSelectedToolId(id);
  };

  const tools: Array<SideBarTool | 'separator'> = [
    {
      id: 'select',
      icon: <i className="bi bi-hand-index"></i>,
      title: '选择工具',
      selectable: true,
      onClick: () => {
      }
    },
    {
      id: 'crop',
      icon: <i className="bi bi-crop"></i>,
      title: '裁剪工具',
      selectable: true,
      onClick: () => {
      }
    },
    'separator',
    {
      id: 'add',
      icon: <i className="bi bi-plus-lg"></i>,
      title: '添加',
      selectable: false,
      onClick: () => {
        setCount(prev => prev + 1);
      }
    },
    {
      id: 'subtract',
      icon: <i className="bi bi-dash-lg"></i>,
      title: '减少',
      selectable: false,
      onClick: () => {
        setCount(prev => prev - 1);
      }
    },
    'separator',
    {
      id: 'reset',
      icon: <i className="bi bi-arrow-clockwise"></i>,
      title: '重置',
      selectable: false,
      onClick: () => {
        setCount(0);
      }
    }
  ];

  return (
    <div>
      <h2>工具栏演示</h2>
      <div style={{ display: 'flex', gap: '20px', alignItems: 'flex-start', marginTop: '20px' }}>
        <SideToolBar 
          tools={tools} 
          selectedToolId={selectedToolId}
          onSelectTool={handleToolSelect}
        />
        <div>
          <h3>计数器: {count}</h3>
          <p>使用加号和减号按钮来改变计数器的值</p>
          <p>当前选中的工具ID: {selectedToolId || '无'}</p>
          <p>提示：只有选择工具和裁剪工具是可选择的，其他工具点击后不会保持选中状态</p>
        </div>
      </div>
      <div style={{ marginTop: '20px' }}>
        <h3>使用说明：</h3>
        <ul>
          <li>工具栏包含了多个工具按钮和分隔符</li>
          <li>鼠标悬停在按钮上会显示工具提示</li>
          <li>点击按钮会触发相应的操作</li>
          <li>只有 selectable=true 的工具（选择工具和裁剪工具）可以保持选中状态</li>
          <li>其他工具（加号、减号、重置）点击后不会保持选中状态</li>
          <li>分隔符用于分组相关的工具</li>
          <li>工具栏支持垂直布局和自定义样式</li>
        </ul>
      </div>
    </div>
  );
}

// PropertyGrid 演示组件
function PropertyGridDemo(): JSX.Element {
  const [text, setText] = useState('示例文本');
  const [number, setNumber] = useState(42);
  const [color, setColor] = useState('#4a90e2');
  const [checked, setChecked] = useState(false);
  const [selected, setSelected] = useState('option1');
  const [petName, setPetName] = useState('Kotone');
  const [favoriteColor, setFavoriteColor] = useState('Blue');
  const [firstName, setFirstName] = useState('John');
  const [notes, setNotes] = useState('这是一段备注信息...');

  const properties: Array<Property | PropertyCategory> = [
    // 无分类的单独属性
    {
      title: '快速设置',
      render: () => (
        <div style={{ display: 'flex', gap: '8px' }}>
          <Button onClick={() => setChecked(!checked)}>
            {checked ? '禁用' : '启用'}
          </Button>
          <Button onClick={() => setNumber(prev => prev + 1)}>
            数值 +1
          </Button>
        </div>
      )
    },
    // 无标题的全宽属性
    {
      render: () => (
        <div style={{ 
          padding: '8px', 
          background: '#fff9e6', 
          borderRadius: '4px',
          fontSize: '14px',
          color: '#666'
        }}>
          提示：可以通过点击分类标题来展开或折叠属性组。
        </div>
      )
    },
    {
      title: '连接设置',
      properties: [
        {
          title: '宠物名称',
          render: () => (
            <input
              type="text"
              value={petName}
              onChange={(e) => setPetName(e.target.value)}
              style={{ width: '100%', padding: '4px' }}
            />
          )
        }
      ],
      foldable: true
    },
    // 又一个无分类的属性
    {
      title: '状态',
      render: () => (
        <span style={{ 
          padding: '4px 8px',
          borderRadius: '4px',
          backgroundColor: checked ? '#e6ffe6' : '#ffe6e6',
          color: checked ? '#006600' : '#cc0000'
        }}>
          {checked ? '已启用' : '已禁用'}
        </span>
      )
    },
    {
      title: '基本信息',
      properties: [
        {
          title: '喜欢的颜色',
          render: () => (
            <input
              type="text"
              value={favoriteColor}
              onChange={(e) => setFavoriteColor(e.target.value)}
              style={{ width: '100%', padding: '4px' }}
            />
          )
        },
        {
          title: '名字',
          render: () => (
            <input
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              style={{ width: '100%', padding: '4px' }}
            />
          )
        },
        // 分类中的无标题属性
        {
          render: () => (
            <div style={{
              padding: '8px',
              background: '#f0f0f0',
              borderRadius: '4px',
              fontSize: '14px'
            }}>
              这是基本信息分类中的一条说明文本。
            </div>
          )
        }
      ],
      foldable: true
    },
    {
      title: '其他设置',
      properties: [
        {
          title: '文本输入',
          render: () => (
            <input
              type="text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              style={{ width: '100%', padding: '4px' }}
            />
          )
        },
        {
          title: '数字输入',
          render: () => (
            <input
              type="number"
              value={number}
              onChange={(e) => setNumber(Number(e.target.value))}
              style={{ width: '100px', padding: '4px' }}
            />
          )
        },
        {
          title: '颜色选择',
          render: () => (
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <input
                type="color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
              />
              <span>{color}</span>
            </div>
          )
        },
        {
          title: '复选框',
          render: () => (
            <input
              type="checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
            />
          )
        },
        {
          title: '超长文本',
          render: () => (
            <div style={{ width: '100%', height: '100px', backgroundColor: '#f0f0f0' }}>
              {Array(100).fill("这是一个超长文本，用于测试PropertyGrid的折叠功能。").join("")}
            </div>
          )
        }
      ],
      foldable: true
    },
    // 最后添加一个备注输入框
    {
      title: '备注',
      render: () => (
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          style={{ 
            width: '100%', 
            padding: '4px',
            minHeight: '60px',
            resize: 'vertical'
          }}
        />
      )
    }
  ];

  return (
    <div>
      <h2>属性网格演示</h2>
      <div style={{ maxWidth: '600px', marginTop: '20px' }}>
        <PropertyGrid properties={properties} />
      </div>
      <div style={{ marginTop: '20px' }}>
        <h3>当前值：</h3>
        <pre style={{ 
          backgroundColor: '#f5f5f5', 
          padding: '15px', 
          borderRadius: '4px' 
        }}>
{JSON.stringify({
  petName,
  favoriteColor,
  firstName,
  text,
  number,
  color,
  checked,
  selected,
  notes
}, null, 2)}
        </pre>
      </div>
      <div>
        <h3>使用说明：</h3>
        <ul>
          <li>PropertyGrid 组件用于展示和编辑一组属性</li>
          <li>属性可以按类别分组显示，也可以单独显示</li>
          <li>属性可以有标题，也可以占据整行显示</li>
          <li>每个类别有自己的标题栏</li>
          <li>可折叠的类别可以通过点击标题栏来展开/折叠</li>
          <li>支持在分类中和分类外混合显示属性</li>
          <li>支持各种类型的输入控件：文本框、数字输入、颜色选择器等</li>
          <li>可以通过 render 函数自定义属性的展示方式</li>
          <li>所有的属性值改变都会实时反映在下方的当前值显示中</li>
        </ul>
      </div>
    </div>
  );
}

// ImageViewerModal 演示组件
function ImageViewerModalDemo(): JSX.Element {
  const { modal, openModal } = useImageViewerModal('示例图片');
  const demoImage = 'https://picsum.photos/1920/1080';

  return (
    <div>
      <h2>图片查看器模态框演示</h2>
      <ControlPanel>
        <Button onClick={() => openModal(demoImage)}>打开图片</Button>
      </ControlPanel>
      {modal}
      <div>
        <h3>使用说明：</h3>
        <ul>
          <li>点击"打开图片"按钮显示图片查看器模态框</li>
          <li>在模态框中可以使用鼠标拖动和滚轮缩放图片</li>
          <li>使用底部工具栏的按钮可以：</li>
          <ul>
            <li>放大/缩小图片</li>
            <li>将图片缩放到适合容器大小</li>
            <li>重置图片缩放</li>
          </ul>
          <li>点击右上角的 X 按钮或按 ESC 键关闭模态框</li>
          <li>模态框支持设置标题，当前显示为"示例图片"</li>
          <li>模态框使用半透明背景，可以隐约看到背景内容</li>
          <li>使用 useImageViewerModal Hook 可以更方便地集成此组件</li>
        </ul>
      </div>
    </div>
  );
}

// VSToolBar 演示组件
function VSToolBarDemo(): JSX.Element {
  const [count, setCount] = useState(0);
  const [currentAlign, setCurrentAlign] = useState<'left' | 'center' | 'right'>('left');
  const [autoSave, setAutoSave] = useState(false);
  const [selectedCPU, setSelectedCPU] = useState<string>('any');
  const [selectedOS, setSelectedOS] = useState<string>('win');
  const [selectedTool, setSelectedTool] = useState<string>('select');

  const cpuOptions: DropdownOption[] = [
    { value: 'any', label: 'Any CPU' },
    { value: 'x86', label: 'x86' },
    { value: 'x64', label: 'x64' },
    { value: 'arm', label: 'ARM' },
    { value: 'arm64', label: 'ARM64' }
  ];

  const osOptions: DropdownOption[] = [
    { value: 'win', label: 'Windows' },
    { value: 'mac', label: 'macOS' },
    { value: 'linux', label: 'Linux' }
  ];

  return (
    <div>
      <h2>VS工具栏演示</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', marginTop: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <select 
            value={currentAlign} 
            onChange={(e) => setCurrentAlign(e.target.value as 'left' | 'center' | 'right')}
            style={{
              padding: '6px 12px',
              borderRadius: '4px',
              border: '1px solid #ccc',
              fontSize: '14px'
            }}
          >
            <option value="left">左对齐</option>
            <option value="center">居中对齐</option>
            <option value="right">右对齐</option>
          </select>
        </div>

        <VSToolBar align={currentAlign}>
          <VSToolBar.Button
            id="select"
            icon={<i className="bi bi-cursor" />}
            label="选择"
            selected={selectedTool === 'select'}
            onClick={() => setSelectedTool('select')}
          />
          <VSToolBar.Button
            id="move"
            icon={<i className="bi bi-arrows-move" />}
            label="移动"
            selected={selectedTool === 'move'}
            onClick={() => setSelectedTool('move')}
          />
          <VSToolBar.Button
            id="rotate"
            icon={<i className="bi bi-arrow-clockwise" />}
            label="旋转"
            selected={selectedTool === 'rotate'}
            onClick={() => setSelectedTool('rotate')}
          />
          <VSToolBar.Separator />
          <VSToolBar.Button
            id="debug"
            icon={<i className="bi bi-bug" />}
            label="调试"
            disabled={count === 0}
            onClick={() => alert('开始调试')}
          />
          <VSToolBar.Button
            id="run"
            icon={<i className="bi bi-play-fill" />}
            label="运行"
            disabled={count === 0}
            onClick={() => alert('开始运行')}
          />
          <VSToolBar.Separator />
          <VSToolBar.Dropdown
            id="cpu"
            type="dropdown"
            options={cpuOptions}
            value={selectedCPU}
            onChange={setSelectedCPU}
            title="选择CPU架构"
          />
          <VSToolBar.Dropdown
            id="os"
            type="dropdown"
            options={osOptions}
            value={selectedOS}
            onChange={setSelectedOS}
            title="选择操作系统"
          />
          <VSToolBar.Separator />
          <VSToolBar.Button
            id="add"
            icon={<i className="bi bi-plus-lg" />}
            title="增加计数"
            onClick={() => setCount(prev => prev + 1)}
          />
          <VSToolBar.Button
            id="subtract"
            icon={<i className="bi bi-dash-lg" />}
            title="减少计数"
            disabled={count === 0}
            onClick={() => setCount(prev => prev - 1)}
          />
          <VSToolBar.Separator />
          <VSToolBar.Button
            id="reset"
            icon={<i className="bi bi-arrow-clockwise" />}
            label="重置计数"
            disabled={count === 0}
            onClick={() => setCount(0)}
          />
          <div style={{ 
            marginLeft: '8px',
            fontSize: '13px',
            color: '#666'
          }}>
            计数: {count}
          </div>
          <VSToolBar.Separator />
          <VSToolBar.Checkbox
            id="auto-save"
            label="自动保存"
            checked={autoSave}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAutoSave(e.target.checked)}
          />
        </VSToolBar>

        <div style={{ 
          marginTop: '20px',
          padding: '15px',
          backgroundColor: '#f5f5f5',
          borderRadius: '4px'
        }}>
          <h4 style={{ margin: '0 0 10px 0' }}>当前选择：</h4>
          <div>当前工具: {selectedTool}</div>
          <div>CPU架构: {cpuOptions.find(opt => opt.value === selectedCPU)?.label}</div>
          <div>操作系统: {osOptions.find(opt => opt.value === selectedOS)?.label}</div>
          <div>计数器: {count}</div>
          <div>自动保存: {autoSave ? '开启' : '关闭'}</div>
        </div>

        <div style={{ marginTop: '20px' }}>
          <h3>使用说明：</h3>
          <ul>
            <li>工具栏支持三种对齐方式：</li>
            <ul>
              <li>左对齐（默认）：工具栏项目靠左排列</li>
              <li>居中对齐：工具栏项目居中排列</li>
              <li>右对齐：工具栏项目靠右排列</li>
            </ul>
            <li>工具栏项目包括：</li>
            <ul>
              <li>可选择的工具按钮（选择、移动、旋转）- 点击后会保持选中状态</li>
              <li>禁用状态的按钮（当计数为0时，调试和运行按钮被禁用）</li>
              <li>带图标和文字的按钮</li>
              <li>只带图标的按钮（如"增加"、"减少"）- 悬停时显示提示文本</li>
              <li>下拉菜单（如"CPU架构"、"操作系统"）</li>
              <li>分隔符用于分组相关功能</li>
              <li>复选框用于开关类选项</li>
              <li>自定义内容（如计数器显示）</li>
            </ul>
            <li>按钮状态：</li>
            <ul>
              <li>选中状态：背景色变深，hover时颜色更深</li>
              <li>禁用状态：文字变灰，透明度降低，不可点击</li>
              <li>普通状态：透明背景，hover时背景色变浅</li>
            </ul>
          </ul>
        </div>
      </div>
    </div>
  );
}

// 添加 Splitable 演示组件
function SplitableDemo(): JSX.Element {
  const [direction, setDirection] = useState<'horizontal' | 'vertical'>('horizontal');
  const [panelCount, setPanelCount] = useState(2);
  const [useMemory, setUseMemory] = useState(true);

  const panels = Array.from({ length: panelCount }, (_, i) => (
    <div
      key={i}
      style={{
        height: '100%',
        padding: '1rem',
        backgroundColor: i % 2 === 0 ? '#f8f9fa' : '#e9ecef',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '1.25rem',
        color: '#495057'
      }}
    >
      面板 {i + 1}
    </div>
  ));

  return (
    <div>
      <h2>可分割面板演示</h2>
      <ControlPanel>
        <Button onClick={() => setDirection(d => d === 'horizontal' ? 'vertical' : 'horizontal')}>
          切换方向 ({direction === 'horizontal' ? '水平' : '垂直'})
        </Button>
        <Button onClick={() => setPanelCount(c => Math.min(c + 1, 5))}>
          添加面板
        </Button>
        <Button onClick={() => setPanelCount(c => Math.max(c - 1, 2))}>
          移除面板
        </Button>
        <Button onClick={() => setUseMemory(m => !m)}>
          {useMemory ? '禁用大小记忆' : '启用大小记忆'}
        </Button>
      </ControlPanel>
      <div style={{ 
        height: '500px', 
        border: '1px solid #dee2e6',
        borderRadius: '4px',
        overflow: 'hidden'
      }}>
        <Splitable 
          vertical={direction === 'vertical'}
          memorizeSizesKey={useMemory ? `demo-splitable-${direction}-${panelCount}` : undefined}
        >
          {panels}
        </Splitable>
      </div>
      <div>
        <h3>使用说明：</h3>
        <ul>
          <li>可以通过按钮切换面板的分割方向：</li>
          <ul>
            <li>水平方向：面板左右排列</li>
            <li>垂直方向：面板上下排列</li>
          </ul>
          <li>可以动态添加或移除面板（2-5个）</li>
          <li>每个面板之间都有一个可拖动的分隔条</li>
          <li>最后一个面板可以通过右上角（或底部）的按钮折叠/展开</li>
          <li>拖动分隔条时会显示蓝色的指示器</li>
          <li>面板内容会自动适应容器大小</li>
          <li>大小记忆功能：</li>
          <ul>
            <li>启用后，会自动记住每个面板的大小</li>
            <li>记忆是基于方向和面板数量的，所以切换方向或改变面板数量会使用不同的记忆</li>
            <li>可以通过"禁用大小记忆"按钮来关闭此功能</li>
            <li>记忆的大小会保存在浏览器的 localStorage 中</li>
          </ul>
        </ul>
      </div>
    </div>
  );
}

// 添加 FormModal 演示组件
function FormModalDemo(): JSX.Element {
  const [results, setResults] = useState<Array<{ time: string; data: Record<string, string> | null }>>([]);

  const simpleForm = useFormModal([
    {
      type: 'text',
      label: '用户名',
      name: 'username',
      required: true,
      placeholder: '请输入用户名'
    },
    {
      type: 'password',
      label: '密码',
      name: 'password',
      required: true,
      validator: (value) => value.length >= 6 || '密码长度至少为6位',
      placeholder: '请输入密码'
    }
  ]);

  const advancedForm = useFormModal([
    {
      type: 'text',
      label: '姓名',
      name: 'name',
      required: true,
      placeholder: '请输入姓名'
    },
    {
      type: 'email',
      label: '邮箱',
      name: 'email',
      required: true,
      validator: (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) || '请输入有效的邮箱地址',
      placeholder: 'example@domain.com'
    },
    {
      type: 'number',
      label: '年龄',
      name: 'age',
      validator: (value) => {
        const age = parseInt(value);
        return (age >= 18 && age <= 100) || '年龄必须在18-100之间';
      },
      placeholder: '请输入年龄'
    },
    {
      type: 'textarea',
      label: '简介',
      name: 'bio',
      placeholder: '请输入个人简介'
    }
  ]);

  const customForm = useFormModal([
    {
      type: 'text',
      label: '标题',
      name: 'title',
      required: true,
      placeholder: '请输入标题'
    },
    {
      type: 'custom',
      label: '标签',
      name: 'tags',
      required: true,
      placeholder: '输入标签后按回车或逗号添加',
      validator: (value) => value.split(',').filter(Boolean).length > 0 || '请至少添加一个标签',
      customComponent: TagInput
    },
    {
      type: 'textarea',
      label: '描述',
      name: 'description',
      placeholder: '请输入描述'
    }
  ]);

  const handleShowSimpleForm = async () => {
    const result = await simpleForm.show('登录');
    setResults(prev => [{
      time: new Date().toLocaleTimeString(),
      data: result
    }, ...prev]);
  };

  const handleShowAdvancedForm = async () => {
    const result = await advancedForm.show('用户注册');
    setResults(prev => [{
      time: new Date().toLocaleTimeString(),
      data: result
    }, ...prev]);
  };

  const handleShowCustomForm = async () => {
    const result = await customForm.show('带自定义组件的表单');
    setResults(prev => [{
      time: new Date().toLocaleTimeString(),
      data: result
    }, ...prev]);
  };

  return (
    <div>
      <h2>表单对话框演示</h2>
      <ControlPanel>
        <Button onClick={handleShowSimpleForm}>显示简单表单</Button>
        <Button onClick={handleShowAdvancedForm}>显示高级表单</Button>
        <Button onClick={handleShowCustomForm}>显示自定义组件表单</Button>
      </ControlPanel>
      {simpleForm.modal}
      {advancedForm.modal}
      {customForm.modal}
      
      <div style={{ marginTop: '20px' }}>
        <h3>表单提交历史：</h3>
        {results.length === 0 ? (
          <div style={{ color: '#666', padding: '10px' }}>
            暂无提交记录
          </div>
        ) : (
          <div style={{ 
            maxHeight: '300px', 
            overflowY: 'auto',
            border: '1px solid #dee2e6',
            borderRadius: '4px'
          }}>
            {results.map((result, index) => (
              <div key={index} style={{
                padding: '10px',
                borderBottom: index < results.length - 1 ? '1px solid #dee2e6' : 'none',
                backgroundColor: index % 2 === 0 ? '#f8f9fa' : 'white'
              }}>
                <div style={{ marginBottom: '5px', color: '#666' }}>
                  提交时间：{result.time}
                </div>
                {result.data === null ? (
                  <div style={{ color: '#dc3545' }}>用户取消了操作</div>
                ) : (
                  <pre style={{ margin: 0, fontSize: '0.9em' }}>
                    {JSON.stringify(result.data, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <h3>使用说明：</h3>
        <ul>
          <li>简单表单演示：</li>
          <ul>
            <li>包含基本的用户名和密码字段</li>
            <li>用户名为必填项</li>
            <li>密码必须至少6位</li>
          </ul>
          <li>高级表单演示：</li>
          <ul>
            <li>包含更多字段类型：文本、邮箱、数字、文本区域</li>
            <li>演示了不同类型的验证：</li>
            <ul>
              <li>必填项验证</li>
              <li>邮箱格式验证</li>
              <li>数字范围验证</li>
            </ul>
          </ul>
          <li>表单特性：</li>
          <ul>
            <li>支持字段验证和错误提示</li>
            <li>可以通过点击取消按钮或关闭图标来取消操作</li>
            <li>提交的数据会显示在下方的历史记录中</li>
            <li>支持异步/Promise方式获取表单结果</li>
          </ul>
          <li>自定义组件表单演示：</li>
          <ul>
            <li>包含一个自定义的标签输入组件</li>
            <li>可以通过回车或逗号添加多个标签</li>
            <li>标签可以单独删除</li>
            <li>支持必填验证</li>
            <li>与其他表单控件无缝集成</li>
          </ul>
        </ul>
      </div>
    </div>
  );
}

// 添加 AutocompleteInput 演示组件
function AutocompleteInputDemo(): JSX.Element {
  const [selectedValue, setSelectedValue] = useState('');
  const [debounceTime, setDebounceTime] = useState(300);
  const [processMode, setProcessMode] = useState<'none' | 'uppercase' | 'prefix'>('none');

  const handleAutoComplete = async (value: string) => {
    // 模拟异步请求
    await new Promise(resolve => setTimeout(resolve, 500));
    
    const fruits = [
      'Apple', 'Apricot', 'Avocado',
      'Banana', 'Blackberry', 'Blueberry',
      'Cherry', 'Coconut', 'Cranberry',
      'Dragon Fruit', 'Durian',
      'Elderberry',
      'Fig',
      'Grape', 'Grapefruit', 'Guava'
    ];

    return fruits.filter(fruit => 
      fruit.toLowerCase().includes(value.toLowerCase())
    );
  };

  const handleAutocompleteSelect = async (inputValue: string, value: string) => {
    // 模拟异步处理
    await new Promise(resolve => setTimeout(resolve, 200));

    switch (processMode) {
      case 'uppercase':
        return value.toUpperCase();
      case 'prefix':
        return `🍎 ${value}`;
      default:
        return value;
    }
  };

  return (
    <div>
      <h2>自动完成输入框演示</h2>
      <div style={{ maxWidth: '400px' }}>
        <AutocompleteInput
          placeholder="输入水果名称..."
          onAutoCompleteRequest={handleAutoComplete}
          onChange={setSelectedValue}
          onAutocompleteSelect={handleAutocompleteSelect}
          debounceTime={debounceTime}
        />
      </div>
      <ControlPanel>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span>防抖时间：</span>
          <input
            type="number"
            value={debounceTime}
            onChange={(e) => setDebounceTime(Number(e.target.value))}
            style={{ width: '80px' }}
          /> ms
          <span style={{ marginLeft: '20px' }}>选择后处理：</span>
          <select 
            value={processMode} 
            onChange={(e) => setProcessMode(e.target.value as typeof processMode)}
            style={{ padding: '4px' }}
          >
            <option value="none">不处理</option>
            <option value="uppercase">转大写</option>
            <option value="prefix">添加前缀</option>
          </select>
        </div>
      </ControlPanel>
      <div style={{ marginTop: '20px' }}>
        <div>当前选择：{selectedValue || '未选择'}</div>
      </div>
      <div>
        <h3>使用说明：</h3>
        <ul>
          <li>在输入框中输入文字，会自动显示匹配的水果名称建议</li>
          <li>支持键盘操作：</li>
          <ul>
            <li>↑/↓ 键：在建议列表中上下选择</li>
            <li>Enter 键：选择当前高亮的建议</li>
            <li>Esc 键：关闭建议列表</li>
          </ul>
          <li>可以通过鼠标点击选择建议项</li>
          <li>点击输入框外部会关闭建议列表</li>
          <li>支持自定义防抖时间，避免频繁请求</li>
          <li>支持异步加载建议列表，有加载状态提示</li>
          <li>建议列表最大高度为 200px，超出时可滚动</li>
          <li>选择后处理功能：</li>
          <ul>
            <li>不处理：直接使用选择的值</li>
            <li>转大写：将选择的值转换为大写</li>
            <li>添加前缀：在选择的值前添加水果图标</li>
          </ul>
          <li>处理是异步的，支持在选择后进行复杂的转换操作</li>
        </ul>
      </div>
    </div>
  );
}

// 添加一个自定义的标签输入组件
const TagInput: React.FC<{
  value: string;
  onChange: (value: string) => void;
  isInvalid: boolean;
  placeholder?: string;
}> = ({ value, onChange, isInvalid, placeholder }) => {
  const tags = value ? value.split(',').filter(Boolean) : [];

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const input = e.currentTarget as HTMLInputElement;
      const newTag = input.value.trim();
      if (newTag && !tags.includes(newTag)) {
        const newTags = [...tags, newTag];
        onChange(newTags.join(','));
      }
      input.value = '';
    }
  };

  const removeTag = (tagToRemove: string) => {
    const newTags = tags.filter(tag => tag !== tagToRemove);
    onChange(newTags.join(','));
  };

  return (
    <div>
      <div style={{ 
        display: 'flex', 
        flexWrap: 'wrap', 
        gap: '8px', 
        marginBottom: '8px' 
      }}>
        {tags.map((tag, index) => (
          <span
            key={index}
            style={{
              background: '#e9ecef',
              padding: '2px 8px',
              borderRadius: '4px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            {tag}
            <i
              className="bi bi-x"
              style={{ cursor: 'pointer' }}
              onClick={() => removeTag(tag)}
            />
          </span>
        ))}
      </div>
      <Form.Control
        type="text"
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        isInvalid={isInvalid}
      />
    </div>
  );
};

const GlobalStyle = styled.div`
  .modal-90w {
    width: 90vw;
    max-width: 90vw !important;
  }
`;

// 主Demo组件
function Demo() {
  const navigate = useNavigate();
  const location = useLocation();
  const currentDemo = location.pathname.split('/').pop() || 'messageBox';

  const demos = [
    { id: 'messageBox', name: '消息框', component: MessageBoxDemo },
    { id: 'spinner', name: '加载动画', component: SpinnerDemo },
    { id: 'toast', name: 'Toast 消息', component: ToastMessageDemo },
    { id: 'formModal', name: '表单对话框', component: FormModalDemo },
    { id: 'singleViewer', name: '单图片查看器', component: SingleImageViewerDemo },
    { id: 'multipleViewer', name: '多图片查看器', component: MultipleImagesViewerDemo },
    { id: 'imageViewerModal', name: '图片查看器模态框', component: ImageViewerModalDemo },
    { id: 'rectBox', name: '矩形框', component: RectBoxDemo },
    { id: 'rectMask', name: '遮罩层', component: RectMaskDemo },
    { id: 'imageEditor', name: '图片标注器', component: ImageEditorDemo },
    { id: 'nativeDiv', name: '原生 Div', component: NativeDivDemo },
    { id: 'sideToolBar', name: '工具栏', component: SideToolBarDemo },
    { id: 'propertyGrid', name: '属性网格', component: PropertyGridDemo },
    { id: 'vsToolBar', name: 'VS工具栏', component: VSToolBarDemo },
    { id: 'splitable', name: '可分割面板', component: SplitableDemo },
    { id: 'autocomplete', name: '自动完成输入框', component: AutocompleteInputDemo }
  ];

  return (
    <>
      <GlobalStyle />
      <DemoContainer>
        <Sidebar>
          {demos.map(demo => (
            <MenuItem
              key={demo.id}
              active={currentDemo === demo.id}
              onClick={() => navigate(`/demo/${demo.id}`)}
            >
              {demo.name}
            </MenuItem>
          ))}
        </Sidebar>
        <Content>
          <Routes>
            <Route path="/" element={<Navigate to="/demo/messageBox" replace />} />
            {demos.map(demo => (
              <Route 
                key={demo.id}
                path={`${demo.id}`}
                element={<demo.component />}
              />
            ))}
          </Routes>
        </Content>
      </DemoContainer>
    </>
  );
}

export default Demo;
