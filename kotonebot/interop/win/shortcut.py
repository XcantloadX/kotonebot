import os
import typing

import pythoncom
from win32comext.shell import shell, shellcon

def create_shortcut(target_file: str, target_args: str, link_file: str | None, *,
                    link_name: str | None = None,
                    icon_path: str, description: str = ""):
    """
    Creates a shortcut.

    :param target_file: The path to the target file.
    :param target_args: The arguments for the target file.
    :param link_file: The path to the shortcut file. If None, creates on the desktop.
    :param link_name: The name of the shortcut file. If None, it is derived from the target file name.
                        Only used when link_file is None.
    :param icon_path: The path to the icon file.
    :param description: The description of the shortcut.
    """
    pythoncom.CoInitialize()
    if link_file is None:
        desktop_path = shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOP, 0, 0)
        if link_name is None:
            link_name = os.path.splitext(os.path.basename(target_file))[0]
        link_file = os.path.join(desktop_path, f"{link_name}.lnk")

    shortcut = pythoncom.CoCreateInstance(
        shell.CLSID_ShellLink,
        None,
        pythoncom.CLSCTX_INPROC_SERVER,
        shell.IID_IShellLink
    )
    # TODO: 下面这些方法都没有 typing，会报错，需要一种方法加入 typing
    shortcut.SetPath(target_file) # type: ignore
    shortcut.SetArguments(target_args) # type: ignore
    shortcut.SetDescription(description) # type: ignore
    shortcut.SetIconLocation(icon_path, 0) # type: ignore

    persist_file = shortcut.QueryInterface(pythoncom.IID_IPersistFile)
    persist_file.Save(link_file, 0) # type: ignore
    pythoncom.CoUninitialize()

