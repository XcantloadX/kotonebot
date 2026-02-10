import unittest
import threading
from typing import cast

from kotonebot.client.device import Device
from kotonebot.core import KotoneBot, BotStopReason, Event, BotContext
from kotonebot.backend.context import Task, init_context, vars


class DummyDevice:
    def screenshot(self):
        raise NotImplementedError


class TestEvent(unittest.TestCase):
    def test_listener_management(self):
        event = Event()
        calls = []

        def listener(value):
            calls.append(value)

        event.add_listener(listener)
        event.add_listener(listener)
        event.trigger(1)
        self.assertEqual(calls, [1])

        event.remove_listener(listener)
        event.trigger(2)
        self.assertEqual(calls, [1])

    def test_iadd_isub(self):
        event = Event()
        calls = []

        def listener(value):
            calls.append(value)

        event += listener
        event.trigger(1)
        event -= listener
        event.trigger(2)
        self.assertEqual(calls, [1])


class TestKotoneBotRun(unittest.TestCase):
    def setUp(self):
        init_context(target_device=DummyDevice()) # type: ignore
        vars.flow.clear_interrupt()

    def test_run_middlewares_and_events(self):
        calls = []
        statuses = []
        stopped = []

        def device_factory():
            return cast(Device, DummyDevice())

        def task_func():
            calls.append("core")

        task = Task("t1", "t1", "task 1", task_func, 0)

        def m1(ctx, t, nxt):
            calls.append("m1_pre")
            nxt()
            calls.append("m1_post")

        def m2(ctx, t, nxt):
            calls.append("m2_pre")
            nxt()
            calls.append("m2_post")

        bot = KotoneBot(device_factory=device_factory, middlewares=[m1, m2])

        def on_status(t, status):
            statuses.append((t.name, status))

        def on_stopped(reason, exc):
            stopped.append((reason, exc))

        bot.events.task_status_changed += on_status
        bot.events.stopped += on_stopped

        bot.run([task])

        self.assertEqual(calls, ["m1_pre", "m2_pre", "core", "m2_post", "m1_post"])
        self.assertEqual(statuses, [("t1", "running"), ("t1", "finished")])
        self.assertEqual(stopped[0][0], BotStopReason.COMPLETED)
        self.assertIsNone(stopped[0][1])

    def test_run_stop_via_context(self):
        calls = []

        def device_factory():
            return cast(Device, DummyDevice())

        def task_func_a():
            calls.append("a")

        def task_func_b():
            calls.append("b")

        task_a = Task("a", "a", "task a", task_func_a, 0)
        task_b = Task("b", "b", "task b", task_func_b, 0)

        def stopper(ctx: BotContext, t, nxt):
            ctx.stop()
            nxt()

        bot = KotoneBot(device_factory=device_factory, middlewares=[stopper])
        bot.run([task_a, task_b])

        self.assertEqual(calls, ["a"])

    def test_run_throwable_iterator(self):
        calls = []
        stopped = []

        def device_factory():
            return cast(Device, DummyDevice())

        def task_fail():
            calls.append("fail")
            raise ValueError("boom")

        def task_after():
            calls.append("after")

        task1 = Task("t1", "t1", "task 1", task_fail, 0)
        task2 = Task("t2", "t2", "task 2", task_after, 0)

        class ThrowableIterator:
            def __init__(self, tasks):
                self._it = iter(tasks)
                self.thrown = []

            def __iter__(self):
                return self

            def __next__(self):
                return next(self._it)

            def throw(self, typ, val=None, tb=None):
                self.thrown.append(typ)
                return next(self._it)

        it = ThrowableIterator([task1, task2])
        bot = KotoneBot(device_factory=device_factory)
        bot.events.stopped += lambda reason, exc: stopped.append((reason, exc))

        bot.run(it)

        self.assertEqual(calls, ["fail", "after"])
        self.assertEqual(len(it.thrown), 1)
        self.assertIsInstance(it.thrown[0], ValueError)
        self.assertEqual(stopped[0][0], BotStopReason.COMPLETED)
        self.assertIsNone(stopped[0][1])

    def test_run_throwable_generator(self):
        calls = []
        stopped = []
        caught = []

        def device_factory():
            return cast(Device, DummyDevice())

        def task_fail():
            calls.append("fail")
            raise ValueError("boom")

        def task_after():
            calls.append("after")

        task1 = Task("t1", "t1", "task 1", task_fail, 0)
        task2 = Task("t2", "t2", "task 2", task_after, 0)

        def task_gen():
            try:
                yield task1
            except ValueError as exc:
                caught.append(exc)
                yield task2

        bot = KotoneBot(device_factory=device_factory)
        bot.events.stopped += lambda reason, exc: stopped.append((reason, exc))

        bot.run(task_gen())

        self.assertEqual(calls, ["fail", "after"])
        self.assertEqual(len(caught), 1)
        self.assertIsInstance(caught[0], ValueError)
        self.assertEqual(stopped[0][0], BotStopReason.COMPLETED)
        self.assertIsNone(stopped[0][1])

    def test_run_non_throwable_exception_emits_error(self):
        stopped = []
        statuses = []

        def device_factory():
            return cast(Device, DummyDevice())

        def task_fail():
            raise ValueError("boom")

        task1 = Task("t1", "t1", "task 1", task_fail, 0)
        bot = KotoneBot(device_factory=device_factory)
        bot.events.stopped += lambda reason, exc: stopped.append((reason, exc))
        bot.events.task_status_changed += lambda t, s: statuses.append((t.name, s))

        bot.run([task1])

        self.assertEqual(statuses, [("t1", "running"), ("t1", "finished")])
        self.assertEqual(stopped[0][0], BotStopReason.ERROR)
        self.assertIsInstance(stopped[0][1], RuntimeError)

    def test_start_updates_run_status(self):
        calls = []
        stopped = []
        gate = threading.Event()

        def device_factory():
            return cast(Device, DummyDevice())

        def task_func():
            gate.wait(timeout=2)
            calls.append("done")

        task = Task("t1", "t1", "task 1", task_func, 0)
        bot = KotoneBot(device_factory=device_factory)
        bot.events.stopped += lambda reason, exc: stopped.append((reason, exc))

        status = bot.start([task])
        gate.set()
        status.thread.join(timeout=2)

        self.assertEqual(calls, ["done"])
        self.assertFalse(status.thread.is_alive())
        self.assertFalse(status.running)
        self.assertEqual(stopped[0][0], BotStopReason.COMPLETED)
        self.assertIsNone(stopped[0][1])

    def test_run_keyboard_interrupt(self):
        calls = []
        statuses = []
        stopped = []

        def device_factory():
            return cast(Device, DummyDevice())

        def task_func():
            calls.append("done")

        task = Task("t1", "t1", "task 1", task_func, 0)
        bot = KotoneBot(device_factory=device_factory)
        bot.events.task_status_changed += lambda t, s: statuses.append((t.name, s))
        bot.events.stopped += lambda reason, exc: stopped.append((reason, exc))

        vars.flow.request_interrupt()
        bot.run([task])

        self.assertEqual(calls, [])
        self.assertEqual(statuses, [("t1", "running")])
        self.assertEqual(stopped[0][0], BotStopReason.USER_REQUEST)
        self.assertIsNone(stopped[0][1])
        self.assertFalse(vars.flow.is_interrupted)
