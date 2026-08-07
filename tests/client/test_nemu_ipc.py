import ctypes
import platform
import time
import unittest
from ctypes import wintypes

from kotonebot.client.implements.nemu_ipc.external_renderer_ipc import _StdIoRedirector

# Windows 标准输出 / 错误句柄常量（与 _StdIoRedirector 保持一致）
_STD_OUTPUT_HANDLE = -11
_STD_ERROR_HANDLE = -12


@unittest.skipUnless(
    platform.system() == "Windows",
    "该功能强依赖 Windows stdout/stderr 管道重定向",
)
class TestStdIoRedirector(unittest.TestCase):
    """测试 _StdIoRedirector 的 begin / end / drain 生命周期与句柄还原逻辑。"""

    def setUp(self) -> None:
        # 记录 begin 前的原始进程级 stdout/stderr 句柄，便于还原断言与兜底还原
        self._original_stdout = self._get_std_handle(_STD_OUTPUT_HANDLE)
        self._original_stderr = self._get_std_handle(_STD_ERROR_HANDLE)

    def tearDown(self) -> None:
        # 兜底：确保测试进程的 stdout/stderr 始终还原为原始句柄
        self._set_std_handle(_STD_OUTPUT_HANDLE, self._original_stdout)
        self._set_std_handle(_STD_ERROR_HANDLE, self._original_stderr)

    def _get_kernel32(self) -> ctypes.WinDLL:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetStdHandle.argtypes = [wintypes.DWORD]
        kernel32.GetStdHandle.restype = wintypes.HANDLE
        kernel32.SetStdHandle.argtypes = [wintypes.DWORD, wintypes.HANDLE]
        kernel32.SetStdHandle.restype = wintypes.BOOL
        kernel32.WriteFile.argtypes = [
            wintypes.HANDLE,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPVOID,
        ]
        kernel32.WriteFile.restype = wintypes.BOOL
        return kernel32

    def _get_std_handle(self, handle_id: int) -> int:
        handle = self._get_kernel32().GetStdHandle(handle_id)
        # GetStdHandle 的 restype 为 c_void_p，非 NULL 时直接返回整数地址
        assert handle is not None
        return handle

    def _set_std_handle(self, handle_id: int, handle: int) -> None:
        self._get_kernel32().SetStdHandle(handle_id, handle)

    def _write_stdout(self, data: bytes) -> None:
        """向当前进程级 stdout 句柄（即管道写端）写入字节。"""
        self._write_std(_STD_OUTPUT_HANDLE, data)

    def _write_stderr(self, data: bytes) -> None:
        """向当前进程级 stderr 句柄（即管道写端）写入字节。"""
        self._write_std(_STD_ERROR_HANDLE, data)

    def _write_std(self, handle_id: int, data: bytes) -> None:
        """向指定标准句柄写入字节。"""
        kernel32 = self._get_kernel32()
        handle = kernel32.GetStdHandle(handle_id)
        buf = ctypes.create_string_buffer(data)
        written = wintypes.DWORD(0)
        kernel32.WriteFile(handle, ctypes.byref(buf), len(data), ctypes.byref(written), None)

    def _poll_until(
        self,
        redirector: _StdIoRedirector,
        predicate: object,
        timeout: float = 3.0,
    ) -> list[str]:
        """轮询 drain，直到收集到满足 predicate 的行或超时。"""
        deadline = time.time() + timeout
        collected: list[str] = []
        while time.time() < deadline:
            collected.extend(redirector.drain_logs())
            if predicate(collected):
                return collected
            time.sleep(0.05)
        return collected

    def _drain_until(self, redirector: _StdIoRedirector, timeout: float = 3.0) -> list[str]:
        """轮询 drain，直到取到日志或超时。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            lines = redirector.drain_logs()
            if lines:
                return lines
            time.sleep(0.05)
        return []

    def test_begin_drain_and_restore(self) -> None:
        """begin 后 stdout/stderr 都被重定向；drain 可取回两个流的日志；end 还原。"""
        redirector = _StdIoRedirector()
        redirector.begin()
        try:
            # begin 后进程级 stdout/stderr 句柄都应指向管道（原始句柄已被替换）
            self.assertNotEqual(self._get_std_handle(_STD_OUTPUT_HANDLE), self._original_stdout)
            self.assertNotEqual(self._get_std_handle(_STD_ERROR_HANDLE), self._original_stderr)
            self._write_stderr(b"err: 10, y: 20\r\n")
            self._write_stdout(b"out: 10, y: 20\r\n")
            lines = self._poll_until(
                redirector, lambda c: "err: 10, y: 20" in c and "out: 10, y: 20" in c
            )
            self.assertEqual(sorted(lines), ["err: 10, y: 20", "out: 10, y: 20"])
        finally:
            redirector.end()
        # end 后进程级 stdout/stderr 句柄都应还原为原始句柄
        self.assertEqual(self._get_std_handle(_STD_OUTPUT_HANDLE), self._original_stdout)
        self.assertEqual(self._get_std_handle(_STD_ERROR_HANDLE), self._original_stderr)

    def test_newline_splitting_multiple_lines(self) -> None:
        """一次写入多行（跨 stdout/stderr）应被正确按行拆分收集。"""
        redirector = _StdIoRedirector()
        redirector.begin()
        try:
            self._write_stdout(b"line one\n")
            self._write_stderr(b"line two\n")
            lines = self._poll_until(
                redirector, lambda c: "line one" in c and "line two" in c
            )
            self.assertIn("line one", lines)
            self.assertIn("line two", lines)
        finally:
            redirector.end()

    def test_context_manager_restores_on_exit(self) -> None:
        """作为上下文管理器时，退出（__exit__）后 stdout/stderr 句柄应还原。"""
        with _StdIoRedirector() as redirector:
            self._write_stdout(b"ctx line\r\n")
            lines = self._drain_until(redirector)
            self.assertEqual(lines, ["ctx line"])
        self.assertEqual(self._get_std_handle(_STD_OUTPUT_HANDLE), self._original_stdout)
        self.assertEqual(self._get_std_handle(_STD_ERROR_HANDLE), self._original_stderr)

    def test_drain_is_clearing(self) -> None:
        """drain 应返回并清空日志列表。"""
        redirector = _StdIoRedirector()
        redirector.begin()
        try:
            self._write_stdout(b"first\r\n")
            self._write_stderr(b"second\r\n")
            first = self._drain_until(redirector)
            self.assertTrue(first)
            # 二次 drain 不应再返回同一批数据
            self.assertEqual(redirector.drain_logs(), [])
        finally:
            redirector.end()

    def test_log_capacity_limit(self) -> None:
        """日志行数超过上限时，应丢弃最旧的行而不是无限增长。"""
        redirector = _StdIoRedirector(max_log_lines=3)
        redirector.begin()
        try:
            # 连续写入超过上限的日志行
            for i in range(1, 5):
                self._write_stdout(f"line{i}\n".encode())
            # 等待后台线程处理完所有写入后再一次性取回（避免 drain 清空导致断言竞态）
            time.sleep(0.5)
            collected = redirector.drain_logs()
            # 有界队列应只保留最新的 3 行，最旧的 line1 被丢弃
            self.assertEqual(collected, ["line2", "line3", "line4"])
        finally:
            redirector.end()


if __name__ == "__main__":
    unittest.main()