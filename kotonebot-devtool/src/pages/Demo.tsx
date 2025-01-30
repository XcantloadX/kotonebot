import { useRef, useState } from 'react';
import styled from '@emotion/styled';
import { useNavigate, useLocation, Routes, Route, Navigate } from 'react-router-dom';
import ImageViewer, { ImageViewerRef } from '../components/ImageViewer';
import MultipleImagesViewer from '../components/MutipleImagesViewer';
import { useMessageBox } from '../hooks/useMessageBox';
import { useFullscreenSpinner } from '../hooks/useFullscreenSpinner';
import ImageEditor, { ImageEditorRef } from '../components/ImageEditor/ImageEditor';
import { Annotation, RectPoints, Tool } from '../components/ImageEditor/types';
import RectBox from '../components/ImageEditor/RectBox';
import RectMask from '../components/ImageEditor/RectMask';
import FormRange from 'react-bootstrap/esm/FormRange';
import NativeDiv from '../components/NativeDiv';
import { AnnotationChangedEvent } from '../components/ImageEditor/ImageEditor';
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
  const [currentTool, setCurrentTool] = useState<Tool>(Tool.Drag);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [showMask, setShowMask] = useState(true);
  const [maskAlpha, setMaskAlpha] = useState(0.5);
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
            />
          </ViewerContainer>
          <ControlPanel>
            <Button onClick={handleEditorZoomIn}>放大</Button>
            <Button onClick={handleEditorZoomOut}>缩小</Button>
            <Button onClick={handleEditorReset}>重置</Button>
            <Button onClick={() => setShowCrosshair(!showCrosshair)}>
              {showCrosshair ? '隐藏准线' : '显示准线'}
            </Button>
            <Button onClick={() => setCurrentTool(currentTool === Tool.Drag ? Tool.Rect : Tool.Drag)}>
              {currentTool === Tool.Drag ? '切换到矩形工具' : '切换到拖动工具'}
            </Button>
            <Button onClick={handleClearAnnotations}>清除标注</Button>
            <Button onClick={() => setShowMask(!showMask)}>
              {showMask ? '隐藏遮罩' : '显示遮罩'}
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
        <RectMask rects={rects} alpha={alpha} transition={enableTransition} />
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
  const [events, setEvents] = useState<Array<{ type: string; time: string; position: string }>>([]);

  const addEvent = (type: string, e: MouseEvent) => {
    const newEvent = {
      type,
      time: new Date().toLocaleTimeString(),
      position: `(${e.clientX}, ${e.clientY})`
    };
    setEvents(prev => [newEvent, ...prev].slice(0, 5));
  };

  const handleNativeMouseEnter = (e: MouseEvent) => {
    addEvent('mouseenter', e);
  };

  const handleNativeMouseMove = (e: MouseEvent) => {
    addEvent('mousemove', e);
  };

  const handleNativeMouseLeave = (e: MouseEvent) => {
    addEvent('mouseleave', e);
  };

  const handleNativeMouseDown = (e: MouseEvent) => {
    addEvent('mousedown', e);
  };

  const handleNativeClick = (e: MouseEvent) => {
    addEvent('click', e);
  };

  return (
    <div>
      <h2>原生 Div 事件演示</h2>
      <NativeDivPlayground>
        <DemoNativeDiv
          onNativeMouseEnter={handleNativeMouseEnter}
          onNativeMouseMove={handleNativeMouseMove}
          onNativeMouseLeave={handleNativeMouseLeave}
          onNativeClick={handleNativeClick}
          onNativeMouseDown={handleNativeMouseDown}
        >
          与我互动！
        </DemoNativeDiv>
      </NativeDivPlayground>
      <div style={{ marginTop: '20px' }}>
        <h3>最近的事件：</h3>
        <ul>
          {events.map((event, index) => (
            <li key={index}>
              {event.type} - 时间：{event.time} - 位置：{event.position}
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
          <li>所有事件都会显示在下方的列表中，包括触发时间和鼠标位置</li>
        </ul>
      </div>
    </div>
  );
}

// 主Demo组件
function Demo() {
  const navigate = useNavigate();
  const location = useLocation();
  const currentDemo = location.pathname.split('/').pop() || 'messageBox';

  const demos = [
    { id: 'messageBox', name: '消息框', component: MessageBoxDemo },
    { id: 'spinner', name: '加载动画', component: SpinnerDemo },
    { id: 'singleViewer', name: '单图片查看器', component: SingleImageViewerDemo },
    { id: 'multipleViewer', name: '多图片查看器', component: MultipleImagesViewerDemo },
    { id: 'rectBox', name: '矩形框', component: RectBoxDemo },
    { id: 'rectMask', name: '遮罩层', component: RectMaskDemo },
    { id: 'imageEditor', name: '图片标注器', component: ImageEditorDemo },
    { id: 'nativeDiv', name: '原生 Div', component: NativeDivDemo }
  ];

  return (
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
  );
}

export default Demo;
