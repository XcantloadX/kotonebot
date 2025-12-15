import unittest
import cv2

from kotonebot.core.entities.base import GameObject, TemplateMatchPrefab, OcrPrefab
from kotonebot.primitives import Image, Rect
from kotonebot.backend.context.context import manual_context, init_context
from kotonebot.backend.image import TemplateNoMatchError
from kotonebot.backend.ocr import TextNotFoundError


class TestTemplateMatchPrefab(unittest.TestCase):
    def setUp(self):
        self.img = cv2.imread('tests/images/acquire_pdorinku.png')
        # 初始化上下文与设备
        from kotonebot.client.device import Device
        from kotonebot.client.protocol import Screenshotable, Touchable

        class _FakeScreenshot(Screenshotable):
            def __init__(self, device: Device, img):
                self.img = img
            @property
            def screen_size(self):
                return (self.img.shape[1], self.img.shape[0])
            def detect_orientation(self):
                return 'portrait'
            def screenshot(self):
                return self.img

        class _FakeTouch(Touchable):
            def __init__(self, device: Device):
                pass
            def click(self, x: int, y: int) -> None:
                pass
            def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float|None = None) -> None:
                pass

        dev = Device(platform='test')
        dev.setup(screenshot=_FakeScreenshot(dev, self.img), touch=_FakeTouch(dev))
        init_context(target_device=dev)
        # 入栈上下文（自动截图模式）
        self.ctx = manual_context('auto')
        self.ctx.begin()

    def tearDown(self):
        self.ctx.end()

    def test_find_and_exists(self):
        class _Obj(GameObject):
            pass
        class _Prefab(TemplateMatchPrefab[_Obj]):
            template = Image(file_path='tests/images/pdorinku.png')
            threshold = 0.7
        obj = _Prefab.find()
        self.assertIsNotNone(obj)
        self.assertTrue(_Prefab.exists())
        assert obj is not None
        self.assertGreater(obj.rect.w, 0)
        self.assertGreater(obj.rect.h, 0)

    def test_find_all(self):
        class _Obj(GameObject):
            pass
        class _Prefab(TemplateMatchPrefab[_Obj]):
            template = Image(file_path='tests/images/pdorinku.png')
            threshold = 0.7
        objs = _Prefab.find_all()
        self.assertGreater(len(objs), 0)
        for o in objs:
            self.assertIsInstance(o, _Obj)
            self.assertGreater(o.rect.w, 0)
            self.assertGreater(o.rect.h, 0)

    def test_require_success(self):
        class _Obj(GameObject):
            pass
        class _Prefab(TemplateMatchPrefab[_Obj]):
            template = Image(file_path='tests/images/pdorinku.png')
            threshold = 0.7
        obj = _Prefab.require()
        self.assertIsInstance(obj, _Obj)
        self.assertGreater(obj.rect.w, 0)
        self.assertGreater(obj.rect.h, 0)

    def test_require_fail_with_region(self):
        class _Obj(GameObject):
            pass
        class _Prefab(TemplateMatchPrefab[_Obj]):
            template = Image(file_path='tests/images/pdorinku.png')
            threshold = 0.999
            region = Rect(0, 0, 10, 10)
        with self.assertRaises(TemplateNoMatchError):
            _Prefab.require()

    def test_predicate_filters(self):
        class _Obj(GameObject):
            pass
        class _Prefab(TemplateMatchPrefab[_Obj]):
            template = Image(file_path='tests/images/pdorinku.png')
            threshold = 0.7
        # 使用一个总是 False 的谓词，find 应该返回 None
        obj = _Prefab.find(predicate=lambda o: False)
        self.assertIsNone(obj)
        # find_all 也应返回空列表
        objs = _Prefab.find_all(predicate=lambda o: False)
        self.assertEqual(len(objs), 0)


class TestOcrPrefab(unittest.TestCase):
    def setUp(self):
        self.img = cv2.imread('tests/images/acquire_pdorinku.png')
        from kotonebot.client.device import Device
        from kotonebot.client.protocol import Screenshotable, Touchable

        class _FakeScreenshot(Screenshotable):
            def __init__(self, device: Device, img):
                self.img = img
            @property
            def screen_size(self):
                return (self.img.shape[1], self.img.shape[0])
            def detect_orientation(self):
                return 'portrait'
            def screenshot(self):
                return self.img

        class _FakeTouch(Touchable):
            def __init__(self, device: Device):
                pass
            def click(self, x: int, y: int) -> None:
                pass
            def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float|None = None) -> None:
                pass

        dev = Device(platform='test')
        dev.setup(screenshot=_FakeScreenshot(dev, self.img), touch=_FakeTouch(dev))
        init_context(target_device=dev)
        self.ctx = manual_context('auto')
        self.ctx.begin()

    def tearDown(self):
        self.ctx.end()

    def test_find_and_exists(self):
        class _Obj(GameObject):
            pass
        class _Prefab(OcrPrefab[_Obj]):
            pattern = '受け取るPドリンクを選んでください。'
            region = Rect(147, 614, 417, 32)
        obj = _Prefab.find()
        self.assertIsNotNone(obj)
        self.assertTrue(_Prefab.exists())
        assert obj is not None
        # 位置应在区域附近
        self.assertGreaterEqual(obj.rect.x1, _Prefab.region.x1)
        self.assertGreaterEqual(obj.rect.y1, _Prefab.region.y1)

    def test_find_all(self):
        class _Obj(GameObject):
            pass
        class _Prefab(OcrPrefab[_Obj]):
            pattern = '受け取るPドリンクを選んでください。'
            region = Rect(147, 614, 417, 32)
        objs = _Prefab.find_all()
        self.assertGreaterEqual(len(objs), 1)
        for o in objs:
            self.assertIsInstance(o, _Obj)
            self.assertGreater(o.rect.w, 0)
            self.assertGreater(o.rect.h, 0)

    def test_require_success(self):
        class _Obj(GameObject):
            pass
        class _Prefab(OcrPrefab[_Obj]):
            pattern = '受け取るPドリンクを選んでください。'
            region = Rect(147, 614, 417, 32)
        obj = _Prefab.require()
        self.assertIsInstance(obj, _Obj)
        self.assertGreater(obj.rect.w, 0)
        self.assertGreater(obj.rect.h, 0)

    def test_require_fail_with_region(self):
        class _Obj(GameObject):
            pass
        class _Prefab(OcrPrefab[_Obj]):
            pattern = 'このテキストは存在しない'
            region = Rect(0, 0, 100, 100)
        with self.assertRaises(TextNotFoundError):
            _Prefab.require()

    def test_predicate_filters(self):
        class _Obj(GameObject):
            pass
        class _Prefab(OcrPrefab[_Obj]):
            pattern = '受け取るPドリンクを選んでください。'
            region = Rect(147, 614, 417, 32)
        obj = _Prefab.find(predicate=lambda o: False)
        self.assertIsNone(obj)
        objs = _Prefab.find_all(predicate=lambda o: False)
        self.assertEqual(len(objs), 0)


if __name__ == '__main__':
    unittest.main()
