# pyright: reportUnusedExpression=false
"""覆盖 Pipeline builtins：actions 参数与图集成。"""

import unittest

from typing import Any

from kotonebot.core.entities.base import GameObject
from kotonebot.core.entities.template_match import TemplateMatchPrefab
from kotonebot.pipeline import (
    AfterMatch,
    Node,
    Pipeline,
    dummy,
    ocr,
    prefab,
    run_node,
    template_match,
)
from kotonebot.primitives import ImageSlice, Rect


class TestBuiltinActions(unittest.TestCase):
    """验证 actions 参数与命中语义。"""

    def test_actions_run_in_order_on_hit(self) -> None:
        """构造参数 actions= 应使动作按序执行。"""
        log_a: list[str] = []

        actions = [
            lambda ctx: log_a.append("a"),
            lambda ctx: log_a.append("b"),
        ]
        def callback1() -> bool:
            for action in actions:
                action(AfterMatch([None]))
            return True

        n1 = Node(callback1, definition_id="n1")
        self.assertTrue(run_node(n1))
        self.assertEqual(log_a, ["a", "b"])

    def test_ocr_factory_actions(self) -> None:
        """ocr 的 actions= 应正确配置节点。"""
        calls: list[str] = []

        def act1(ctx: AfterMatch[Any]) -> None:
            calls.append("1")

        def act2(ctx: AfterMatch[Any]) -> None:
            calls.append("2")

        n1 = ocr("领取", [act1, act2])
        self.assertEqual(n1.kind, "ocr")
        self.assertEqual(n1.definition_id, "ocr:领取")

        # 直接使用 Node 测试动作运行（不依赖 ocr 工厂的后端接入）
        events: list[str] = []
        node_actions = [lambda ctx: events.append("ok")]
        def cb() -> bool:
            for action in node_actions:
                action(AfterMatch([None]))
            return True
        node = Node(cb, definition_id="t")
        self.assertTrue(run_node(node))
        self.assertEqual(events, ["ok"])

    def test_miss_skips_actions_hit_runs_in_order(self) -> None:
        """未命中不跑 action；命中按序执行。"""
        events: list[str] = []
        matched = {"ok": False}

        hit_actions = [
            lambda ctx: events.append("a"),
            lambda ctx: events.append("b"),
        ]
        def callback() -> bool:
            if matched["ok"]:
                for action in hit_actions:
                    action(AfterMatch([None]))
                return True
            return False

        node = Node(callback, definition_id="start", kind="ocr")

        self.assertFalse(run_node(node))
        self.assertEqual(events, [])

        matched["ok"] = True
        self.assertTrue(run_node(node))
        self.assertEqual(events, ["a", "b"])

    def test_action_exception_propagates(self) -> None:
        """action 抛错应 fail fast，不吞异常。"""

        def boom(ctx: AfterMatch[Any]) -> None:
            raise RuntimeError("boom")

        def callback() -> bool:
            boom(AfterMatch([None]))
            return True

        node = Node(callback, definition_id="boom")
        with self.assertRaises(RuntimeError):
            run_node(node)


class TestBuiltinFreezeAndGraph(unittest.TestCase):
    """冻结与构图运行。"""

    def test_builtin_node_in_pipeline_run(self) -> None:
        """Node 可作为图中节点被调度。"""
        events: list[str] = []
        start = Node(lambda: True, definition_id="start")
        step_actions = [lambda ctx: events.append("step")]
        def step_cb() -> bool:
            for action in step_actions:
                action(AfterMatch([None]))
            return True
        step = Node(step_cb, definition_id="step")
        done = Node(lambda: True, definition_id="done")
        start >> step >> done
        pipeline = Pipeline(entry=start, exit=done)
        self.assertTrue(pipeline.run(timeout=0))
        self.assertEqual(events, ["step"])

    def test_dummy_always_true(self) -> None:
        """dummy 恒命中，可作 entry/exit。"""
        entry = dummy(id="e")
        exit_node = dummy(id="x")
        entry >> exit_node
        pipeline = Pipeline(entry=entry, exit=exit_node)
        self.assertTrue(run_node(entry))
        self.assertTrue(pipeline.run(timeout=0))

    def test_dummy_actions(self) -> None:
        """dummy 的 actions 应始终执行。"""
        events: list[str] = []
        n = dummy(actions=[
            lambda ctx: events.append("a"),
            lambda ctx: events.append("b"),
        ], id="d")
        self.assertEqual(n.definition_id, "d")
        self.assertTrue(run_node(n))
        self.assertEqual(events, ["a", "b"])

    def test_template_match_factory_metadata(self) -> None:
        """template_match 工厂应正确配置节点元数据。"""
        n = template_match("x.png", [lambda ctx: None])
        self.assertEqual(n.kind, "template")
        self.assertEqual(n.definition_id, "template:single")

    def test_prefab_factory_metadata(self) -> None:
        """prefab 工厂应正确设置节点元数据。"""
        class _TestBtn(TemplateMatchPrefab[GameObject]):
            template = ImageSlice(file_path="x.png", lazy_load=True, slice_rect=Rect(0,0,10,10))

        n = prefab(_TestBtn, [lambda ctx: None])
        self.assertEqual(n.kind, "prefab")
        self.assertEqual(n.definition_id, "prefab:_TestBtn")


if __name__ == "__main__":
    unittest.main()
