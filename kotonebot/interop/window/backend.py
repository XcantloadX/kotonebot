from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Type

from .model import WindowInfo, WindowQuery, Window, Platform, match_common, UnsupportedQueryFieldError


class WindowBackend(ABC):
    """窗口后端的抽象基类，定义了窗口查询和操作的接口。"""
    native_query_type: Type | tuple[Type, ...] | None = None

    @property
    @abstractmethod
    def platform(self) -> Platform:
        """获取此后端支持的平台。"""
        raise NotImplementedError

    def validate_query(self, query: WindowQuery) -> None:
        """验证查询条件是否与此后端兼容。

        :param query: 查询条件
        :raise ValueError: 平台不匹配
        :raise UnsupportedQueryFieldError: 不支持的原生查询类型
        """
        if query.platform and query.platform != self.platform:
            raise ValueError(
                f"Query platform '{query.platform}' does not match backend '{self.platform}'."
            )
        if query.native is None:
            return
        if self.native_query_type is None or not isinstance(query.native, self.native_query_type):
            raise UnsupportedQueryFieldError(self.platform, type(query.native))

    @abstractmethod
    def list_windows(self) -> list[WindowInfo]:
        """列出此平台上的所有窗口。

        :return: 窗口信息列表
        """
        raise NotImplementedError

    def match_native(self, info: WindowInfo, query: WindowQuery) -> bool:
        """检查窗口信息是否匹配原生查询条件。

        :param info: 窗口信息
        :param query: 查询条件
        :return: 是否匹配原生条件
        """
        return True

    def find_windows(self, query: WindowQuery) -> list[WindowInfo]:
        """查找符合条件的窗口。

        :param query: 查询条件
        :return: 匹配的窗口信息列表
        """
        self.validate_query(query)
        return [
            info
            for info in self.list_windows()
            if match_common(info, query) and self.match_native(info, query)
        ]

    @abstractmethod
    def wrap(self, info: WindowInfo) -> Window:
        """将窗口信息包装成 Window 对象。

        :param info: 窗口信息
        :return: Window 对象
        """
        raise NotImplementedError
