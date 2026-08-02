# pyright: reportUnusedExpression=false
"""覆盖 Pipeline 的结构化构图、冻结与节点约束语义。

主路径：@node 工厂 + 调用工厂得 Node + Pipeline(entry=..., exit=...)。

>> 约束：一个 Node 只能作为右侧操作数一次；已有_source 的节点不可再次用作 >> 左侧。
后继冲突时改用 .next = [...] 覆盖。
"""

import threading
import time
import unittest
from dataclasses import dataclass
from typing import cast

from kotonebot.pipeline import (
    Node,
    NodeAlreadyWiredError,
    NodeFactory,
    Pipeline,
    PipelineGraphError,
    PipelineGraphFrozenError,
    PipelineRunningError,
    Fragment,
    node,
    run_node,
)


# ---------------------------------------------------------------------------
# 函数式辅助工厂
# ---------------------------------------------------------------------------


def make_structured_pipeline() -> tuple[Pipeline, dict[str, Node]]:
    """装配包含链、分支和回边的测试图。

    利用嵌套表达式规避 >> 的 _source 约束；共享目标通过 .next 连接。
    :returns: 已冻结 Pipeline 与命名节点映射。
    """
    @node(id="node1", label="节点一")
    def node1() -> bool:
        return True

    @node(id="node2")
    def node2() -> bool:
        return True

    @node(id="node3")
    def node3() -> bool:
        return True

    @node(id="node4")
    def node4() -> bool:
        return True

    @node(id="node5")
    def node5() -> bool:
        return True

    @node(id="node6")
    def node6() -> bool:
        return True

    @node(id="node7")
    def node7() -> bool:
        return True

    n1, n2, n3, n4, n5, n6, n7 = (
        node1(), node2(), node3(), node4(),
        node5(), node6(), node7(),
    )

    # 单次嵌套表达式：n1 → [n2 → n5 → [n6, n7], n3, n4]
    # 回边与共享目标用 .next 绕过 _source 检查
    n1 >> [n2 >> n5 >> [n6, n7], n3, n4]
    n7.next = [n1]
    n3.next = [n6]
    n4.next = [n6]

    pipeline = Pipeline(entry=n1, exit=n6)
    nodes = {
        "node1": n1, "node2": n2, "node3": n3, "node4": n4,
        "node5": n5, "node6": n6, "node7": n7,
    }
    return pipeline, nodes


def make_recording_pipeline(events: list[str]) -> Pipeline:
    """记录候选按优先级检查与链式执行的顺序。

    :param events: 用于记录节点调用顺序的列表。
    :returns: 已冻结 Pipeline。
    """
    @node(id="start")
    def start() -> bool:
        events.append("start")
        return True

    @node(id="miss")
    def miss() -> bool:
        events.append("miss")
        return False

    @node(id="middle")
    def middle() -> bool:
        events.append("middle")
        return True

    @node(id="done")
    def done() -> bool:
        events.append("done")
        return True

    s, m1, m2, d = start(), miss(), middle(), done()
    # 嵌套表达式让 m1 作为 source 参与而不被设 _source
    s >> [m1 >> d, m2]
    m2.next = [d]
    return Pipeline(entry=s, exit=d)


def make_always_miss_pipeline(counter: list[int] | None = None) -> Pipeline:
    """入口命中后候选始终未命中。

    :param counter: 长度为 1 的列表，用于累计候选调用次数。
    :returns: 已冻结 Pipeline。
    """
    hits = counter if counter is not None else [0]

    @node(id="start")
    def start() -> bool:
        return True

    @node(id="never")
    def never() -> bool:
        hits[0] += 1
        return False

    @node(id="done")
    def done() -> bool:
        return True

    s, n, d = start(), never(), done()
    s >> n
    n.next = [d]
    return Pipeline(entry=s, exit=d)


# ---------------------------------------------------------------------------
# 测试类
# ---------------------------------------------------------------------------


class PipelineTests(unittest.TestCase):
    """验证 Pipeline 图装配和运行规则。"""

    # ---- 基本构图 ----

    def test_nested_connection_uses_expression_head(self) -> None:
        """嵌套连接应把表达式入口放入外层候选。"""
        _pipeline, nodes = make_structured_pipeline()

        self.assertEqual(
            nodes["node1"].next,
            [nodes["node2"], nodes["node3"], nodes["node4"]],
        )
        self.assertEqual(nodes["node2"].next, [nodes["node5"]])
        self.assertEqual(nodes["node5"].next, [nodes["node6"], nodes["node7"]])
        self.assertEqual(nodes["node7"].next, [nodes["node1"]])

    def test_nodes_are_isolated_between_pipeline_instances(self) -> None:
        """工厂每次调用应产生独立节点与连接。"""
        _first, first_nodes = make_structured_pipeline()
        _second, second_nodes = make_structured_pipeline()

        self.assertIsNot(first_nodes["node1"], second_nodes["node1"])
        self.assertEqual(
            first_nodes["node1"].next,
            [first_nodes["node2"], first_nodes["node3"], first_nodes["node4"]],
        )
        self.assertEqual(
            second_nodes["node1"].next,
            [second_nodes["node2"], second_nodes["node3"], second_nodes["node4"]],
        )

    def test_later_connection_overwrites_earlier(self) -> None:
        """后一次 .next 应覆盖前一次 >>。"""

        @node(id="start")
        def start() -> bool:
            return True

        @node(id="first")
        def first() -> bool:
            return True

        @node(id="replacement")
        def replacement() -> bool:
            return True

        s, f, r = start(), first(), replacement()
        s >> f
        s.next = [r]
        pipeline = Pipeline(entry=s, exit=r)

        self.assertEqual(s.next, [r])
        self.assertTrue(pipeline.run(timeout=0))

    def test_empty_candidates_clear_next(self) -> None:
        """`next = []` 应清空后继。"""

        @node(id="start")
        def start() -> bool:
            return True

        @node(id="first")
        def first() -> bool:
            return True

        @node(id="done")
        def done() -> bool:
            return True

        s, f, d = start(), first(), done()
        s >> f
        s.next = []
        self.assertEqual(s.next, [])
        s >> d
        self.assertEqual(s.next, [d])

    def test_tuple_candidates_are_supported_by_rshift(self) -> None:
        """>> 应接受由候选组成的 tuple。"""

        @node(id="start")
        def start() -> bool:
            return True

        @node(id="first")
        def first() -> bool:
            return True

        @node(id="done")
        def done() -> bool:
            return True

        s, f, d = start(), first(), done()
        s >> (f, d)
        f.next = [d]
        pipeline = Pipeline(entry=s, exit=d)

        self.assertEqual(s.next, [f, d])
        self.assertEqual(f.next, [d])
        self.assertTrue(pipeline.run(timeout=0))

    def test_invalid_candidate_fails_during_build(self) -> None:
        """非法候选应在构图阶段报告具体类型。"""

        @node(id="start")
        def start() -> bool:
            return True

        @node(id="first")
        def first() -> bool:
            return True

        s, f = start(), first()
        with self.assertRaisesRegex(
            TypeError,
            "invalid next candidate: expected Node, Fragment, or ConnectionExpression, got int",
        ):
            s >> [f, 123]

    # ---- 冻结 ----

    def test_pipeline_graph_freezes(self) -> None:
        """Pipeline(entry=..., exit=...) 完成后图应冻结。"""
        pipeline, nodes = make_structured_pipeline()

        with self.assertRaises(PipelineGraphFrozenError):
            nodes["node1"] >> nodes["node6"]
        with self.assertRaises(PipelineGraphFrozenError):
            nodes["node1"].next = [nodes["node6"]]

    def test_next_getter_does_not_bypass_freeze(self) -> None:
        """修改 next 返回列表不应改变已冻结图。"""
        _pipeline, nodes = make_structured_pipeline()
        candidates = nodes["node1"].next

        candidates.clear()

        self.assertEqual(
            nodes["node1"].next,
            [nodes["node2"], nodes["node3"], nodes["node4"]],
        )

    def test_connection_expression_cannot_mutate_frozen_graph(self) -> None:
        """持有连接表达式不应绕过冻结保护。"""

        @node(id="a")
        def a() -> bool:
            return True

        @node(id="b")
        def b() -> bool:
            return True

        @node(id="c")
        def c() -> bool:
            return True

        n_a, n_b, n_c = a(), b(), c()
        expr = n_a >> n_b
        Pipeline(entry=n_a, exit=n_b)

        with self.assertRaises(PipelineGraphFrozenError):
            expr >> n_c

    def test_fragment_cannot_mutate_frozen_graph(self) -> None:
        """持有 Fragment 不应绕过冻结保护。"""

        @node(id="entry")
        def entry() -> bool:
            return True

        @node(id="exit_inner")
        def exit_inner() -> bool:
            return True

        @node(id="start")
        def start() -> bool:
            return True

        @node(id="finish")
        def finish() -> bool:
            return True

        e, x, s, f = entry(), exit_inner(), start(), finish()
        e >> x
        fragment = Fragment(entry=e, exit=x)
        s >> fragment
        Pipeline(entry=s, exit=x)

        with self.assertRaises(PipelineGraphFrozenError):
            fragment >> f

    # ---- 运行 ----

    def test_run_checks_candidates_in_priority_order(self) -> None:
        """Runner 应按列表顺序检查候选并沿命中节点继续。"""
        events: list[str] = []
        pipeline = make_recording_pipeline(events)

        result = pipeline.run(timeout=0)

        self.assertTrue(result)
        self.assertEqual(events, ["start", "miss", "middle", "done"])

    def test_timeout_zero_miss_and_hit(self) -> None:
        """timeout=0 时全未命中返回 False，有路径时返回 True。"""
        miss_pipeline = make_always_miss_pipeline()
        hit_events: list[str] = []
        hit_pipeline = make_recording_pipeline(hit_events)

        self.assertFalse(miss_pipeline.run(timeout=0, interval=0))
        self.assertTrue(hit_pipeline.run(timeout=0, interval=0))
        self.assertEqual(hit_events, ["start", "miss", "middle", "done"])

    def test_timeout_positive_rescans_until_candidate_hits(self) -> None:
        """timeout>0 应重扫直到延迟候选命中。"""

        def make_delayed_hit_pipeline(hits_after: int) -> tuple[Pipeline, list[int]]:
            """候选在前几次检查未命中，之后命中。

            :param hits_after: 第几次检查时命中（从 1 起）。
            :returns: 已冻结 Pipeline 与 attempts 可变计数。
            """
            attempts = [0]

            @node(id="start")
            def start() -> bool:
                return True

            @node(id="delayed")
            def delayed() -> bool:
                attempts[0] += 1
                return attempts[0] >= hits_after

            @node(id="done")
            def done() -> bool:
                return True

            s, d1, d2 = start(), delayed(), done()
            s >> d1
            d1.next = [d2]
            return Pipeline(entry=s, exit=d2), attempts

        pipeline, attempts = make_delayed_hit_pipeline(hits_after=3)

        result = pipeline.run(timeout=1.0, interval=0)

        self.assertTrue(result)
        self.assertGreaterEqual(attempts[0], 3)

    def test_cancel_stops_run_with_false(self) -> None:
        """cancel 返回 True 时应停止并返回 False。"""
        pipeline = make_always_miss_pipeline()
        self.assertFalse(
            pipeline.run(timeout=None, interval=0, cancel=lambda: True)
        )

        counter = [0]
        pipeline2 = make_always_miss_pipeline(counter)

        def cancel_after_two() -> bool:
            return counter[0] >= 2

        self.assertFalse(
            pipeline2.run(timeout=None, interval=0, cancel=cancel_after_two)
        )
        self.assertGreaterEqual(counter[0], 2)

    def test_try_run_defaults_to_single_pass(self) -> None:
        """try_run 默认 timeout=0，路径不通时立即 False。"""
        self.assertFalse(make_always_miss_pipeline().try_run())
        events: list[str] = []
        self.assertTrue(make_recording_pipeline(events).try_run())
        self.assertEqual(events, ["start", "miss", "middle", "done"])

    # ---- interval ----

    def test_interval_throttles_when_candidates_hit(self) -> None:
        """候选命中时 interval 也应生效，保证最小轮次间隔。"""

        @node(id="always")
        def always() -> bool:
            return True

        @node(id="done")
        def done() -> bool:
            return True

        s, d = always(), done()
        s >> d
        pipeline = Pipeline(entry=s, exit=d)

        t0 = time.monotonic()
        pipeline.run(timeout=0, interval=0.5)
        elapsed = time.monotonic() - t0
        # 至少一轮 interval 等待（入口命中后，从 entry 到 exit 有一轮循环）
        self.assertGreaterEqual(elapsed, 0.45)

    def test_interval_throttles_when_candidates_miss(self) -> None:
        """全部候选未命中时 interval 同样应生效。"""

        @node(id="start")
        def start() -> bool:
            return True

        @node(id="never")
        def never() -> bool:
            return False

        s, n = start(), never()
        s >> n
        # exit = n（恒不命中），需要在 start 出重扫直到超时
        pipeline = Pipeline(entry=s, exit=n)

        t0 = time.monotonic()
        pipeline.run(timeout=0.5, interval=0.3)
        elapsed = time.monotonic() - t0
        # 应等待至少一次 interval（约 0.3s 的重扫间隔），然后超时
        self.assertGreaterEqual(elapsed, 0.25)
        self.assertLess(elapsed, 1.5)

    def test_interval_zero_no_throttle(self) -> None:
        """interval=0 时不等待。"""

        @node(id="start")
        def start() -> bool:
            return True

        @node(id="done")
        def done() -> bool:
            return True

        s, d = start(), done()
        s >> d
        pipeline = Pipeline(entry=s, exit=d)

        t0 = time.monotonic()
        pipeline.run(timeout=0, interval=0)
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 0.1)

    # ---- 节点工厂 ----

    def test_node_factory_must_be_called_to_obtain_node(self) -> None:
        """@node 返回 NodeFactory，必须调用才能得到 Node。"""

        @node
        def my_func() -> bool:
            return True

        self.assertIsInstance(my_func, NodeFactory)
        inst = my_func()
        self.assertIsInstance(inst, Node)
        # NodeFactory 本身不可参与连线
        with self.assertRaises(TypeError):
            my_func >> inst  # type: ignore[operator]

    def test_multiple_factory_calls_produce_different_instances(self) -> None:
        """多次调用工厂产生不同的 Node 实例。"""

        @node(id="test")
        def my_func() -> bool:
            return True

        n1 = my_func()
        n2 = my_func()
        self.assertIsNot(n1, n2)
        self.assertNotEqual(n1.instance_id, n2.instance_id)

    def test_node_default_id_contains_module_and_qualname(self) -> None:
        """默认 definition_id 应包含模块名与 qualname。"""

        @node
        def free_home() -> bool:
            return True

        self.assertIsInstance(free_home, NodeFactory)
        n1 = free_home()
        self.assertIsInstance(n1, Node)
        self.assertTrue(n1.definition_id.startswith(f"{__name__}."))
        self.assertIn("free_home", n1.definition_id)

        @node(id="explicit_home")
        def named_home() -> bool:
            return True

        n2 = named_home(id="explicit_home")
        self.assertEqual(n2.definition_id, "explicit_home")
        self.assertEqual(n2.instance_id, "explicit_home")

    # ---- 结构校验 ----

    def test_entry_exit_requires_both(self) -> None:
        """strict 模式下必须有 entry 和 exit。"""

        @node(id="only")
        def only() -> bool:
            return True

        n1 = only()
        with self.assertRaisesRegex(PipelineGraphError, "pipeline must configure exit"):
            Pipeline(entry=n1)

    def test_missing_entry_fails_during_build(self) -> None:
        """entry 未提供（None）时应在装配阶段抛 PipelineGraphError。"""

        @node(id="done")
        def done() -> bool:
            return True

        d = done()
        with self.assertRaisesRegex(PipelineGraphError, "entry must be a Node"):
            Pipeline(entry=None, exit=d)  # type: ignore[arg-type]

    def test_non_node_entry_fails_during_build(self) -> None:
        """entry 非 Node 类型时应在装配阶段抛 PipelineGraphError。"""

        @node(id="done")
        def done() -> bool:
            return True

        d = done()
        with self.assertRaisesRegex(PipelineGraphError, "entry must be a Node"):
            Pipeline(entry=object(), exit=d)  # type: ignore[arg-type]

    def test_exit_with_next_fails_during_build(self) -> None:
        """exit.next 非空时应在装配阶段失败。"""

        @node(id="start")
        def start() -> bool:
            return True

        @node(id="done")
        def done() -> bool:
            return True

        @node(id="extra")
        def extra() -> bool:
            return True

        s, d, e = start(), done(), extra()
        s >> d
        d.next = [e]

        with self.assertRaisesRegex(
            PipelineGraphError,
            "pipeline exit must be a leaf node with empty next",
        ):
            Pipeline(entry=s, exit=d)

    def test_unreachable_exit_fails_during_build(self) -> None:
        """exit 从 entry 不可达时应在装配阶段失败。"""

        @node(id="start")
        def start() -> bool:
            return True

        @node(id="middle")
        def middle() -> bool:
            return True

        @node(id="done")
        def done() -> bool:
            return True

        s, m, d = start(), middle(), done()
        s >> m

        with self.assertRaisesRegex(
            PipelineGraphError,
            "pipeline exit is not reachable from entry",
        ):
            Pipeline(entry=s, exit=d)

    def test_non_exit_leaf_fails_during_build(self) -> None:
        """可达的非 exit Node 叶子应在装配阶段失败。"""

        @node(id="home")
        def home() -> bool:
            return True

        @node(id="popup")
        def popup() -> bool:
            return True

        @node(id="done")
        def done() -> bool:
            return True

        h, p, d = home(), popup(), done()
        h >> [p, d]

        with self.assertRaisesRegex(
            PipelineGraphError,
            "reachable leaf node is not exit",
        ):
            Pipeline(entry=h, exit=d)

    def test_leaf_exit_and_cycle_to_exit_succeed(self) -> None:
        """单点 exit 与「环上出边到 exit」的合法图应装配成功。"""

        @node(id="only")
        def only() -> bool:
            return True

        n1 = only()
        pipeline = Pipeline(entry=n1, exit=n1)
        self.assertTrue(pipeline.run(timeout=0))

        @node(id="a")
        def a() -> bool:
            return True

        @node(id="b")
        def b() -> bool:
            return True

        @node(id="done")
        def done() -> bool:
            return True

        n_a, n_b, n_d = a(), b(), done()
        # 单表达式链避免 _source 冲突
        n_a >> n_b >> [n_a, n_d]
        _cycled = Pipeline(entry=n_a, exit=n_d)
        self.assertEqual(n_b.next, [n_a, n_d])

    # ---- 状态与并发 ----

    def test_state_via_dataclass_closure(self) -> None:
        """跨节点状态应通过闭包 / 局部 dataclass 共享。"""

        @dataclass
        class BattleState:
            rounds: int = 0

        state = BattleState()

        @node(id="start")
        def start() -> bool:
            state.rounds += 1
            return True

        @node(id="done")
        def done() -> bool:
            return state.rounds >= 1

        s, d = start(), done()
        s >> d
        pipeline = Pipeline(entry=s, exit=d)

        self.assertTrue(pipeline.run(timeout=0))
        self.assertEqual(state.rounds, 1)

    def test_concurrent_run_raises(self) -> None:
        """同一实例并发/重入 run 应抛出 PipelineRunningError。"""

        # 重入：节点内尝试重入同一实例的 run
        captured_error: list[BaseException | None] = [None]
        pipeline_ref: list[Pipeline | None] = [None]

        @node(id="reenter")
        def reenter() -> bool:
            try:
                pipeline_ref[0].run(timeout=0)  # type: ignore[union-attr]
            except Exception as exc:
                captured_error[0] = exc
            return True

        n = reenter()
        p = Pipeline(entry=n, exit=n)
        pipeline_ref[0] = p

        self.assertTrue(p.run(timeout=0))
        self.assertIsInstance(captured_error[0], PipelineRunningError)

        # 并发：后台线程占用 run，主线程再调应失败
        hold = threading.Event()
        release = threading.Event()
        background_error: list[BaseException] = []

        @node(id="hold_start")
        def hold_start() -> bool:
            hold.set()
            release.wait(timeout=2.0)
            return True

        hs = hold_start()
        concurrent = Pipeline(entry=hs, exit=hs)

        def worker() -> None:
            try:
                concurrent.run(timeout=0)
            except Exception as exc:
                background_error.append(exc)

        thread = threading.Thread(target=worker)
        thread.start()
        self.assertTrue(hold.wait(timeout=2.0))
        with self.assertRaises(PipelineRunningError):
            concurrent.run(timeout=0)
        release.set()
        thread.join(timeout=2.0)
        self.assertEqual(background_error, [])

    def test_run_node_non_bool_fails_fast(self) -> None:
        """run_node 对非 bool 返回值应快速失败。"""
        bad = Node(lambda: cast(bool, "yes"), definition_id="bad", instance_id="bad")

        with self.assertRaisesRegex(TypeError, "expected bool"):
            run_node(bad)

    # ---- >> 约束 ----

    def test_node_can_have_multiple_parents_via_rshift(self) -> None:
        """一个 Node 可以通过 >> 被多个父节点连接。"""

        @node(id="a")
        def a() -> bool:
            return True

        @node(id="b")
        def b() -> bool:
            return True

        @node(id="shared")
        def shared() -> bool:
            return True

        n_a, n_b, n_s = a(), b(), shared()

        n_a >> n_s
        n_b >> n_s

        self.assertIs(n_a._next[0], n_s)
        self.assertIs(n_b._next[0], n_s)

    def test_node_already_wired_error(self) -> None:
        """对已有后继的节点再次使用 >> 应抛出 NodeAlreadyWiredError。"""

        @node(id="a")
        def a() -> bool:
            return True

        @node(id="first")
        def first() -> bool:
            return True

        @node(id="second")
        def second() -> bool:
            return True

        n_a, n_f, n_s = a(), first(), second()

        n_a >> n_f
        with self.assertRaisesRegex(NodeAlreadyWiredError, "already has successors"):
            n_a >> n_s

    def test_duplicate_candidates_error(self) -> None:
        """>> 的候选列表中包含重复项应抛出 ValueError。"""

        @node(id="a")
        def a() -> bool:
            return True

        @node(id="b")
        def b() -> bool:
            return True

        n_a, n_b = a(), b()

        with self.assertRaisesRegex(ValueError, "duplicate candidates"):
            n_a >> [n_b, n_b]

    def test_chained_rshift_checks_duplicate_candidates(self) -> None:
        """链式 >> 的候选重复同样应抛出 ValueError。"""

        @node(id="a")
        def a() -> bool:
            return True

        @node(id="b")
        def b() -> bool:
            return True

        @node(id="c")
        def c() -> bool:
            return True

        n_a, n_b, n_c = a(), b(), c()
        expr = n_a >> [n_b]

        with self.assertRaisesRegex(ValueError, "duplicate candidates"):
            expr >> [n_c, n_c]

    def test_bare_connection_expression_as_rshift_target(self) -> None:
        """>> 应直接接受连接表达式作为右侧候选。"""

        @node(id="a")
        def a() -> bool:
            return True

        @node(id="b")
        def b() -> bool:
            return True

        @node(id="c")
        def c() -> bool:
            return True

        @node(id="done")
        def done() -> bool:
            return True

        n_a, n_b, n_c, n_d = a(), b(), c(), done()
        expr = n_b >> n_c

        # 裸连接表达式直接作为右侧候选：expr 入口成为候选，末端保留供继续链式连接
        n_a >> expr >> n_d
        self.assertEqual(n_a.next, [n_b])
        self.assertEqual(n_b.next, [n_c])
        self.assertEqual(n_c.next, [n_d])

    def test_node_cannot_belong_to_two_pipelines(self) -> None:
        """节点不能属于两个不同的 Pipeline。"""

        @node(id="a")
        def a() -> bool:
            return True

        @node(id="b")
        def b() -> bool:
            return True

        n_a, n_b = a(), b()
        n_a >> n_b
        Pipeline(entry=n_a, exit=n_b)

        # 尝试在另一个 Pipeline 中重用已冻结节点
        n_c = a()
        n_c.next = [n_b]
        with self.assertRaisesRegex(PipelineGraphError, "already belongs to another"):
            Pipeline(entry=n_c, exit=n_b)

    # ---- Fragment ----

    def test_fragment_basic_connection(self) -> None:
        """Fragment 的基本连接语义。"""

        @node(id="entry")
        def entry() -> bool:
            return True

        @node(id="inner")
        def inner() -> bool:
            return True

        @node(id="exit_inner")
        def exit_inner() -> bool:
            return True

        @node(id="start")
        def start() -> bool:
            return True

        @node(id="finish")
        def finish() -> bool:
            return True

        e, i, x, s, f = entry(), inner(), exit_inner(), start(), finish()

        # Fragment 内部链（单表达式）
        e >> i >> x

        fragment = Fragment(entry=e, exit=x)

        # Node >> Fragment：连接 source 到 fragment.entry
        s >> fragment
        self.assertEqual(s.next, [e])

        # Fragment >> Node：连接 fragment.exit 到 target
        fragment >> f
        self.assertEqual(x.next, [f])

        # 完整 Pipeline 运行：s → e → i → x → f
        pipeline = Pipeline(entry=s, exit=f)
        self.assertTrue(pipeline.run(timeout=0))

    def test_fragment_chained_rshift_preserves_internal_chain(self) -> None:
        """start >> fragment >> finish 应展开 Fragment 内部节点，不跳过内部链。"""

        @node(id="page")
        def page() -> bool:
            return True

        @node(id="submit")
        def submit() -> bool:
            return True

        @node(id="done")
        def done() -> bool:
            return True

        @node(id="start")
        def start() -> bool:
            return True

        @node(id="finish")
        def finish() -> bool:
            return True

        pg, sb, dn, st, fi = page(), submit(), done(), start(), finish()
        pg >> sb >> dn
        fragment = Fragment(entry=pg, exit=dn)

        st >> fragment >> fi
        self.assertEqual(st.next, [pg])
        self.assertEqual(pg.next, [sb])
        self.assertEqual(sb.next, [dn])
        self.assertEqual(dn.next, [fi])

        pipeline = Pipeline(entry=st, exit=fi)
        self.assertTrue(pipeline.run(timeout=0))

    # ---- 类路径回归 ----

    def test_class_based_build_returns_fragment(self) -> None:
        """独立类通过 build() 返回 Fragment 的模式。"""

        class MyFlow:
            @node
            def start(self) -> bool:
                return True

            @node
            def done(self) -> bool:
                return True

            def build(self) -> Fragment:
                s, d = self.start(), self.done()
                s >> d
                return Fragment(entry=s, exit=d)

        flow = MyFlow()
        fragment = flow.build()
        pipeline = Pipeline(entry=fragment.entry, exit=fragment.exit)

        self.assertIsInstance(fragment, Fragment)
        self.assertTrue(pipeline.run(timeout=0))

    def test_class_nodes_are_isolated(self) -> None:
        """每次调用 build() 应产生独立节点。"""

        class MyFlow:
            @node
            def start(self) -> bool:
                return True

            @node
            def done(self) -> bool:
                return True

            def build(self) -> Fragment:
                s, d = self.start(), self.done()
                s >> d
                return Fragment(entry=s, exit=d)

        f1 = MyFlow().build()
        f2 = MyFlow().build()

        self.assertIsNot(f1.entry, f2.entry)
        self.assertIsNot(f1.exit, f2.exit)


if __name__ == "__main__":
    unittest.main()
