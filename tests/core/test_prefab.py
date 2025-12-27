import unittest
import cv2

from kotonebot.core import GameObject, TemplateMatchPrefab, OcrPrefab, Prefab
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
        # prefab 属性应指向对应的 Prefab 类
        self.assertIs(obj.prefab, _Prefab)
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
            self.assertIs(o.prefab, _Prefab)
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
        self.assertIs(obj.prefab, _Prefab)
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

    def test_kwargs_override_threshold_and_region(self):
        class _Obj(GameObject):
            pass
        class _Prefab(TemplateMatchPrefab[_Obj]):
            template = Image(file_path='tests/images/pdorinku.png')
            # 使用一个非常高的阈值以及错误的区域，默认应匹配失败
            threshold = 0.999
            region = Rect(0, 0, 10, 10)

        # 默认配置应抛出异常
        with self.assertRaises(TemplateNoMatchError):
            _Prefab.require()

        # 使用 kwargs 覆盖阈值和区域，应当可以匹配成功
        h, w, _ = self.img.shape
        full_region = Rect(0, 0, w, h)
        obj = _Prefab.require(threshold=0.7, region=full_region)
        self.assertIsNotNone(obj)
        self.assertIsInstance(obj, _Obj)
        self.assertIs(obj.prefab, _Prefab)

    def test_kwargs_colored_argument(self):
        class _Obj(GameObject):
            pass
        class _Prefab(TemplateMatchPrefab[_Obj]):
            template = Image(file_path='tests/images/pdorinku.png')
            threshold = 0.7
            colored = False

        # 仅验证 colored 参数可以通过 kwargs 传入并正常工作
        obj = _Prefab.find(colored=True)
        # 无论是否匹配成功，代码路径都不应抛异常
        # 如果匹配成功，再做一些基本断言
        if obj is not None:
            self.assertIsInstance(obj, _Obj)
            self.assertIs(obj.prefab, _Prefab)

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
        # prefab 属性应指向对应的 Prefab 类
        self.assertIs(obj.prefab, _Prefab)
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
            self.assertIs(o.prefab, _Prefab)
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
        self.assertIs(obj.prefab, _Prefab)
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

    def test_ocr_kwargs_override_region(self):
        class _Obj(GameObject):
            pass
        class _Prefab(OcrPrefab[_Obj]):
            pattern = '受け取るPドリンクを選んでください。'
            # 默认使用一个明显错误的区域，应当找不到
            region = Rect(0, 0, 10, 10)

        with self.assertRaises(TextNotFoundError):
            _Prefab.require()

        # 使用 kwargs 覆盖为正确区域，应当可以找到
        correct_region = Rect(147, 614, 417, 32)
        obj = _Prefab.require(region=correct_region)
        self.assertIsNotNone(obj)
        self.assertIsInstance(obj, _Obj)
        self.assertIs(obj.prefab, _Prefab)


class TestCompoundPrefab(unittest.TestCase):
    def test_any_of(self):
        from kotonebot.core.entities.compound import AnyOf
        
        class P1(Prefab):
            @classmethod
            def find(cls, **kwargs): return None
            @classmethod
            def exists(cls, **kwargs): return False
            @classmethod
            def find_all(cls, **kwargs): return []
            @classmethod
            def require(cls, **kwargs): raise RuntimeError("Not found")
            
        class P2(Prefab):
            @classmethod
            def find(cls, **kwargs): return GameObject()
            @classmethod
            def exists(cls, **kwargs): return True
            @classmethod
            def find_all(cls, **kwargs): return [GameObject()]
            @classmethod
            def require(cls, **kwargs): return GameObject()
            
        Compound = AnyOf[P1, P2]
        self.assertTrue(Compound.exists())
        self.assertIsNotNone(Compound.find())
        self.assertEqual(len(Compound.find_all()), 1)
        self.assertIsNotNone(Compound.require())
        
        Compound2 = AnyOf[P1]
        self.assertFalse(Compound2.exists())
        self.assertIsNone(Compound2.find())
        self.assertEqual(len(Compound2.find_all()), 0)
        with self.assertRaises(RuntimeError):
            Compound2.require()


class TestPrefabKwargsAndClickForwarding(unittest.TestCase):
    def test_wait_unpacks_kwargs_and_forwards_predicate(self):
        class _Obj(GameObject):
            pass

        class _Prefab(Prefab[_Obj]):
            @classmethod
            def find(cls, **kwargs):
                # wait should pop timeout/interval before forwarding to find
                assert 'timeout' not in kwargs
                assert 'interval' not in kwargs
                pred = kwargs.get('predicate')
                obj = _Obj()
                obj.prefab = cls
                if pred is None or pred(obj):
                    return obj
                return None

        # should return an object when predicate accepts it
        obj = _Prefab.wait(timeout=1, interval=0, predicate=lambda o: True)
        self.assertIsNotNone(obj)
        self.assertIsInstance(obj, _Obj)

    def test_try_wait_returns_none_on_timeout_without_throw(self):
        class _Obj(GameObject):
            pass

        class _Prefab(Prefab[_Obj]):
            @classmethod
            def find(cls, **kwargs):
                return None

        # timeout=0 and interval=0 should make wait return immediately with None
        res = _Prefab.try_wait(timeout=0, interval=0)
        self.assertIsNone(res)

    def test_click_and_try_click_forward_predicate(self):
        clicked = []

        class _Obj(GameObject):
            def click(self):
                clicked.append(True)

        class _Prefab(Prefab[_Obj]):
            @classmethod
            def require(cls, **kwargs):
                # click should forward predicate to require
                assert 'predicate' in kwargs
                obj = _Obj()
                obj.prefab = cls
                return obj

            @classmethod
            def find(cls, **kwargs):
                pred = kwargs.get('predicate')
                obj = _Obj()
                obj.prefab = cls
                if pred is None or pred(obj):
                    return obj
                return None

        # click should call require and thus trigger click
        _Prefab.click(predicate=lambda o: True)
        self.assertTrue(clicked)
        clicked.clear()

        # try_click should return True and click when predicate matches
        ok = _Prefab.try_click(predicate=lambda o: True)
        self.assertTrue(ok)
        self.assertTrue(clicked)
        clicked.clear()

        # try_click should return False and not click when predicate doesn't match
        ok = _Prefab.try_click(predicate=lambda o: False)
        self.assertFalse(ok)
        self.assertFalse(clicked)

if __name__ == '__main__':
    unittest.main()