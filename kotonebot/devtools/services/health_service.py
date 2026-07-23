"""健康检查服务。"""

from .types import HealthResult


class HealthService:
    """健康检查服务。"""

    @staticmethod
    def check() -> HealthResult:
        """返回健康状态。

        :returns: 健康检查结果
        """
        return HealthResult(status="ok", service="kotonebot-devtools")
