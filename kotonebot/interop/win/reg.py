import winreg
from typing import Any, Literal

RegKey = Literal["HKLM", "HKCU", "HKCR", "HKU", "HKCC"]

def read_reg(key: RegKey, subkey: str, name: str, *, default: Any = None) -> Any:
    """
    读取注册表项的值。

    :param key: 注册表键，例如 "HKLM" (HKEY_LOCAL_MACHINE), "HKCU" (HKEY_CURRENT_USER) 等。
    :param subkey: 注册表子键的路径。
    :param name: 要读取的值的名称。
    :param default: 如果注册表项不存在时返回的默认值。
    :return: 注册表项的值，如果不存在则返回默认值。
    """
    try:
        hkey = {
            "HKLM": winreg.HKEY_LOCAL_MACHINE,
            "HKCU": winreg.HKEY_CURRENT_USER,
            "HKCR": winreg.HKEY_CLASSES_ROOT,
            "HKU": winreg.HKEY_USERS,
            "HKCC": winreg.HKEY_CURRENT_CONFIG,
        }[key]
    except KeyError:
        raise ValueError(f"Invalid key: {key}")

    try:
        with winreg.OpenKey(hkey, subkey) as key_handle:
            value, _ = winreg.QueryValueEx(key_handle, name)
            return value
    except FileNotFoundError:
        return default
    except OSError as e:
        if e.winerror == 2:  # 注册表项不存在
            return default
        else:
            raise  # 其他 OSError 异常，例如权限问题，重新抛出
