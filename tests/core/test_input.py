import unittest
from unittest.mock import patch

from kotonebot.client.input import (
	InputManager,
	KeyboardController,
	MouseController,
	SimpleInputController,
	TouchController,
)
from kotonebot.client.device import Device
from kotonebot.client.protocol import Screenshotable, Touchable
from kotonebot.errors import CapabilityNotSupportedError
from kotonebot.client.scaler import AbstractScaler
from kotonebot.primitives import Point, Rect


class FakeScaler(AbstractScaler):
	def __init__(self, scale_x: float = 1.0, scale_y: float = 1.0) -> None:
		super().__init__()
		self.scale_x = scale_x
		self.scale_y = scale_y
		self.last_logic_point: tuple[int, int] | None = None

	def logic_to_physical(self, v):
		x, y = v
		self.last_logic_point = (x, y)
		return x * self.scale_x, y * self.scale_y


class FakeClickable:
	def __init__(self, rect: Rect) -> None:
		self._rect = rect

	@property
	def rect(self) -> Rect:
		return self._rect


class FakeTouchDriver:
	max_contacts = 10

	def __init__(self) -> None:
		self.events: list[tuple[str, int, int, int]] = []

	def touch_down(self, x: int, y: int, contact_id: int = 0) -> None:
		self.events.append(("down", x, y, contact_id))

	def touch_move(self, x: int, y: int, contact_id: int = 0) -> None:
		self.events.append(("move", x, y, contact_id))

	def touch_up(self, x: int, y: int, contact_id: int = 0) -> None:
		self.events.append(("up", x, y, contact_id))


class FakeMouseDriver:
	def __init__(self) -> None:
		self.events: list[tuple] = []

	def move(self, x: int, y: int) -> None:
		self.events.append(("move", x, y))

	def button_down(self, button=None) -> None:
		self.events.append(("down", button))

	def button_up(self, button=None) -> None:
		self.events.append(("up", button))

	def scroll(self, dx: int = 0, dy: int = 0) -> None:
		self.events.append(("scroll", dx, dy))


class FakeKeyboardDriver:
	def __init__(self) -> None:
		self.events: list[tuple[str, str]] = []

	def key_down(self, key: str) -> None:
		self.events.append(("down", key))

	def key_up(self, key: str) -> None:
		self.events.append(("up", key))

	def type_text(self, text: str) -> None:
		self.events.append(("type", text))


class FakeSimpleInputDriver:
	def __init__(self) -> None:
		self.events: list[tuple] = []

	def click(self, x: int, y: int) -> None:
		self.events.append(("click", x, y))

	def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float | None = None) -> None:
		self.events.append(("swipe", x1, y1, x2, y2, duration))


class FakeHybridDriver(FakeTouchDriver, FakeSimpleInputDriver):
	def __init__(self) -> None:
		self.events: list[tuple] = []

	def click(self, x: int, y: int) -> None:
		self.events.append(("click", x, y))

	def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float | None = None) -> None:
		self.events.append(("swipe", x1, y1, x2, y2, duration))

	def touch_down(self, x: int, y: int, contact_id: int = 0) -> None:
		self.events.append(("down", x, y, contact_id))

	def touch_move(self, x: int, y: int, contact_id: int = 0) -> None:
		self.events.append(("move", x, y, contact_id))

	def touch_up(self, x: int, y: int, contact_id: int = 0) -> None:
		self.events.append(("up", x, y, contact_id))


class FakeScreenshot(Screenshotable):
	def __init__(self, screen_size: tuple[int, int] = (1280, 720)) -> None:
		self._screen_size = screen_size

	@property
	def screen_size(self) -> tuple[int, int]:
		return self._screen_size

	def detect_orientation(self):
		return "portrait"

	def screenshot(self):
		return None


class FakeLegacyTouch(Touchable):
	def __init__(self, device: Device) -> None:
		self.events: list[tuple] = []

	def click(self, x: int, y: int) -> None:
		self.events.append(("click", x, y))

	def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float | None = None) -> None:
		self.events.append(("swipe", x1, y1, x2, y2, duration))


class TestTouchController(unittest.TestCase):
	def test_to_physical_uses_scaler_and_casts_to_int(self):
		scaler = FakeScaler(scale_x=1.5, scale_y=2.2)
		driver = FakeTouchDriver()
		controller = TouchController(scaler, driver)

		result = controller._to_physical(3, 4)

		self.assertEqual(result, (4, 8))
		self.assertEqual(scaler.last_logic_point, (3, 4))

	def test_tap_with_xy_presses_and_releases(self):
		scaler = FakeScaler(scale_x=2, scale_y=3)
		driver = FakeTouchDriver()
		controller = TouchController(scaler, driver)

		controller.tap(5, 6, contact_id=2)

		self.assertEqual(
			driver.events,
			[("down", 10, 18, 2), ("up", 10, 18, 2)],
		)

	def test_tap_supports_point_tuple_point_and_clickable(self):
		scaler = FakeScaler()

		with self.subTest("tuple"):
			driver = FakeTouchDriver()
			controller = TouchController(scaler, driver)
			controller.tap((7, 9))
			self.assertEqual(driver.events, [("down", 7, 9, 0), ("up", 7, 9, 0)])

		with self.subTest("point"):
			driver = FakeTouchDriver()
			controller = TouchController(scaler, driver)
			controller.tap(Point(3, 4))
			self.assertEqual(driver.events, [("down", 3, 4, 0), ("up", 3, 4, 0)])

		with self.subTest("clickable"):
			driver = FakeTouchDriver()
			controller = TouchController(scaler, driver)
			controller.tap(FakeClickable(Rect(10, 20, 8, 6)))
			self.assertEqual(driver.events, [("down", 14, 23, 0), ("up", 14, 23, 0)])

	def test_tap_rejects_invalid_args(self):
		scaler = FakeScaler()
		driver = FakeTouchDriver()
		controller = TouchController(scaler, driver)

		with self.assertRaises(TypeError):
			controller.tap("invalid")  # type: ignore[arg-type]

	def test_double_tap(self):
		scaler = FakeScaler()
		driver = FakeTouchDriver()
		controller = TouchController(scaler, driver)

		with patch("kotonebot.client.input.sleep") as mocked_sleep:
			controller.double_tap(1, 2, contact_id=3, interval=0.25)

		self.assertEqual(
			driver.events,
			[
				("down", 1, 2, 3),
				("up", 1, 2, 3),
				("down", 1, 2, 3),
				("up", 1, 2, 3),
			],
		)
		mocked_sleep.assert_called_once_with(0.25)

	def test_swipe(self):
		scaler = FakeScaler(scale_x=2, scale_y=2)
		driver = FakeTouchDriver()
		controller = TouchController(scaler, driver)

		controller.swipe(1, 2, 3, 4, contact_id=5)

		self.assertEqual(
			driver.events,
			[
				("down", 2, 4, 5),
				("move", 6, 8, 5),
				("up", 6, 8, 5),
			],
		)


class TestMouseController(unittest.TestCase):
	def test_click_moves_then_clicks(self):
		scaler = FakeScaler(scale_x=2, scale_y=3)
		driver = FakeMouseDriver()
		controller = MouseController(scaler, driver)

		controller.click(4, 5, button="right")

		self.assertEqual(
			driver.events,
			[("move", 8, 15), ("down", "right"), ("up", "right")],
		)

	def test_double_click_supports_clickable(self):
		scaler = FakeScaler()
		driver = FakeMouseDriver()
		controller = MouseController(scaler, driver)

		with patch("kotonebot.client.input.sleep") as mocked_sleep:
			controller.double_click(FakeClickable(Rect(10, 20, 8, 6)), interval=0.1)

		self.assertEqual(
			driver.events,
			[
				("move", 14, 23),
				("down", "left"),
				("up", "left"),
				("move", 14, 23),
				("down", "left"),
				("up", "left"),
			],
		)
		mocked_sleep.assert_called_once_with(0.1)

	def test_scroll(self):
		scaler = FakeScaler()
		driver = FakeMouseDriver()
		controller = MouseController(scaler, driver)

		controller.scroll(dx=1, dy=-2)

		self.assertEqual(driver.events, [("scroll", 1, -2)])


class TestKeyboardController(unittest.TestCase):
	def test_press_and_type_text(self):
		scaler = FakeScaler()
		driver = FakeKeyboardDriver()
		controller = KeyboardController(scaler, driver)

		controller.press("enter")
		controller.type_text("hello")

		self.assertEqual(
			driver.events,
			[("down", "enter"), ("up", "enter"), ("type", "hello")],
		)

	def test_hotkey_presses_in_order_and_releases_in_reverse(self):
		scaler = FakeScaler()
		driver = FakeKeyboardDriver()
		controller = KeyboardController(scaler, driver)

		controller.hotkey("ctrl", "shift", "p")

		self.assertEqual(
			driver.events,
			[
				("down", "ctrl"),
				("down", "shift"),
				("down", "p"),
				("up", "p"),
				("up", "shift"),
				("up", "ctrl"),
			],
		)

	def test_hotkey_requires_at_least_one_key(self):
		scaler = FakeScaler()
		driver = FakeKeyboardDriver()
		controller = KeyboardController(scaler, driver)

		with self.assertRaises(ValueError):
			controller.hotkey()


class TestSimpleInputController(unittest.TestCase):
	def test_tap(self):
		scaler = FakeScaler(scale_x=2, scale_y=2)
		driver = FakeSimpleInputDriver()
		controller = SimpleInputController(scaler, driver)

		controller.tap(Point(3, 4))

		self.assertEqual(driver.events, [("click", 6, 8)])

	def test_double_tap(self):
		scaler = FakeScaler()
		driver = FakeSimpleInputDriver()
		controller = SimpleInputController(scaler, driver)

		with patch("kotonebot.client.input.sleep") as mocked_sleep:
			controller.double_tap((1, 2), interval=0.2)

		self.assertEqual(driver.events, [("click", 1, 2), ("click", 1, 2)])
		mocked_sleep.assert_called_once_with(0.2)

	def test_swipe(self):
		scaler = FakeScaler(scale_x=2, scale_y=3)
		driver = FakeSimpleInputDriver()
		controller = SimpleInputController(scaler, driver)

		controller.swipe((1, 2), (3, 4), duration=0.5)

		self.assertEqual(driver.events, [("swipe", 2, 6, 6, 12, 0.5)])


class TestInputManager(unittest.TestCase):
	def test_controller_and_driver_properties(self):
		scaler = FakeScaler()
		touch = FakeTouchDriver()
		mouse = FakeMouseDriver()
		keyboard = FakeKeyboardDriver()
		simple = FakeSimpleInputDriver()
		manager = InputManager(scaler, [touch, mouse, keyboard, simple])

		self.assertIsInstance(manager.touch, TouchController)
		self.assertIsInstance(manager.mouse, MouseController)
		self.assertIsInstance(manager.keyboard, KeyboardController)
		self.assertIsInstance(manager.simple, SimpleInputController)
		self.assertIs(manager.touch_driver, touch)
		self.assertIs(manager.mouse_driver, mouse)
		self.assertIs(manager.keyboard_driver, keyboard)
		self.assertIs(manager.simple_driver, simple)

	def test_tap_prefers_simple_then_touch_then_mouse(self):
		scaler = FakeScaler(scale_x=2, scale_y=2)

		with self.subTest("simple"):
			simple = FakeSimpleInputDriver()
			manager = InputManager(scaler, [simple, FakeTouchDriver(), FakeMouseDriver()])
			manager.tap(1, 2)
			self.assertEqual(simple.events, [("click", 2, 4)])

		with self.subTest("touch"):
			touch = FakeTouchDriver()
			manager = InputManager(scaler, [touch, FakeMouseDriver()])
			manager.tap(1, 2)
			self.assertEqual(touch.events, [("down", 2, 4, 0), ("up", 2, 4, 0)])

		with self.subTest("mouse"):
			mouse = FakeMouseDriver()
			manager = InputManager(scaler, [mouse])
			manager.tap(1, 2)
			self.assertEqual(mouse.events, [("move", 2, 4), ("down", "left"), ("up", "left")])

	def test_double_tap_prefers_simple_then_touch_then_mouse(self):
		scaler = FakeScaler()

		with self.subTest("simple"):
			simple = FakeSimpleInputDriver()
			manager = InputManager(scaler, [simple])
			with patch("kotonebot.client.input.sleep"):
				manager.double_tap(1, 2, interval=0.1)
			self.assertEqual(simple.events, [("click", 1, 2), ("click", 1, 2)])

		with self.subTest("touch"):
			touch = FakeTouchDriver()
			manager = InputManager(scaler, [touch])
			with patch("kotonebot.client.input.sleep"):
				manager.double_tap(1, 2, interval=0.1)
			self.assertEqual(
				touch.events,
				[("down", 1, 2, 0), ("up", 1, 2, 0), ("down", 1, 2, 0), ("up", 1, 2, 0)],
			)

		with self.subTest("mouse"):
			mouse = FakeMouseDriver()
			manager = InputManager(scaler, [mouse])
			with patch("kotonebot.client.input.sleep"):
				manager.double_tap(1, 2, interval=0.1)
			self.assertEqual(
				mouse.events,
				[
					("move", 1, 2),
					("down", "left"),
					("up", "left"),
					("move", 1, 2),
					("down", "left"),
					("up", "left"),
				],
			)

	def test_drag_prefers_simple_then_touch_then_mouse(self):
		scaler = FakeScaler(scale_x=2, scale_y=3)

		with self.subTest("simple"):
			simple = FakeSimpleInputDriver()
			manager = InputManager(scaler, [simple])
			manager.drag(1, 2, 3, 4, duration=0.5)
			self.assertEqual(simple.events, [("swipe", 2, 6, 6, 12, 0.5)])

		with self.subTest("touch"):
			touch = FakeTouchDriver()
			manager = InputManager(scaler, [touch])
			manager.drag(1, 2, 3, 4)
			self.assertEqual(
				touch.events,
				[("down", 2, 6, 0), ("move", 6, 12, 0), ("up", 6, 12, 0)],
			)

		with self.subTest("mouse"):
			mouse = FakeMouseDriver()
			manager = InputManager(scaler, [mouse])
			manager.drag(1, 2, 3, 4)
			self.assertEqual(
				mouse.events,
				[("move", 2, 6), ("down", "left"), ("move", 6, 12), ("up", "left")],
			)

	def test_actions_raise_when_no_supported_driver(self):
		manager = InputManager(FakeScaler(), [])

		with self.assertRaises(CapabilityNotSupportedError):
			manager.tap(1, 2)
		with self.assertRaises(CapabilityNotSupportedError):
			manager.double_tap(1, 2)
		with self.assertRaises(CapabilityNotSupportedError):
			manager.drag(1, 2, 3, 4)

	def test_hybrid_driver_registers_all_supported_roles(self):
		scaler = FakeScaler()
		hybrid = FakeHybridDriver()
		manager = InputManager(scaler, [hybrid])

		self.assertIs(manager.touch_driver, hybrid)
		self.assertIs(manager.simple_driver, hybrid)

		manager.tap(1, 2)
		self.assertEqual(hybrid.events, [("click", 1, 2)])


class TestDeviceCompatibility(unittest.TestCase):
	def test_click_hooks_still_apply_with_legacy_touchable(self):
		scaler = FakeScaler()
		device = Device(platform="test", scaler=scaler)
		screenshot = FakeScreenshot()
		touch = FakeLegacyTouch(device)
		device.setup(screenshot=screenshot, touch=touch)
		device.click_hooks_before.append(lambda x, y: (x + 10, y + 20))

		device.click(1, 2)

		self.assertEqual(touch.events, [("click", 11, 22)])

	def test_click_rect_still_applies_hooks(self):
		scaler = FakeScaler()
		device = Device(platform="test", scaler=scaler)
		screenshot = FakeScreenshot()
		touch = FakeLegacyTouch(device)
		device.setup(screenshot=screenshot, touch=touch)
		device.click_hooks_before.append(lambda x, y: (x + 10, y + 20))

		with patch("kotonebot.client.device.np.random.randint", side_effect=[0, 0]):
			device.click(Rect(10, 20, 8, 6))

		self.assertEqual(touch.events, [("click", 24, 43)])

	def test_swipe_falls_back_to_legacy_touchable_when_no_modern_driver(self):
		scaler = FakeScaler(scale_x=2, scale_y=3)
		device = Device(platform="test", scaler=scaler)
		screenshot = FakeScreenshot()
		touch = FakeLegacyTouch(device)
		device.setup(screenshot=screenshot, touch=touch)

		device.swipe(1, 2, 3, 4, duration=0.5)

		self.assertEqual(touch.events, [("swipe", 2, 6, 6, 12, 0.5)])


if __name__ == "__main__":
	unittest.main()
