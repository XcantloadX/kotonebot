import ctypes
from typing import Optional, Literal, List, overload
from typing_extensions import assert_never


# 按钮常量
MB_OK = 0x00000000
MB_OKCANCEL = 0x00000001
MB_ABORTRETRYIGNORE = 0x00000002
MB_YESNOCANCEL = 0x00000003
MB_YESNO = 0x00000004
MB_RETRYCANCEL = 0x00000005
MB_CANCELTRYCONTINUE = 0x00000006

# 图标常量
MB_ICONSTOP = 0x00000010
MB_ICONERROR = 0x00000010
MB_ICONQUESTION = 0x00000020
MB_ICONWARNING = 0x00000030
MB_ICONINFORMATION = 0x00000040

# 默认按钮常量
MB_DEFBUTTON1 = 0x00000000
MB_DEFBUTTON2 = 0x00000100
MB_DEFBUTTON3 = 0x00000200
MB_DEFBUTTON4 = 0x00000300

# 模态常量
MB_APPLMODAL = 0x00000000
MB_SYSTEMMODAL = 0x00001000
MB_TASKMODAL = 0x00002000

# 其他选项
MB_HELP = 0x00004000
MB_NOFOCUS = 0x00008000
MB_SETFOREGROUND = 0x00010000
MB_DEFAULT_DESKTOP_ONLY = 0x00020000
MB_TOPMOST = 0x00040000
MB_RIGHT = 0x00080000
MB_RTLREADING = 0x00100000
MB_SERVICE_NOTIFICATION = 0x00200000

# 返回值常量
IDOK = 1
IDCANCEL = 2
IDABORT = 3
IDRETRY = 4
IDIGNORE = 5
IDYES = 6
IDNO = 7
IDCLOSE = 8
IDHELP = 9
IDTRYAGAIN = 10
IDCONTINUE = 11

# 为清晰起见，定义类型别名
ButtonsType = Literal['ok', 'ok_cancel', 'abort_retry_ignore', 'yes_no_cancel', 'yes_no', 'retry_cancel', 'cancel_try_continue']
IconType = Optional[Literal['stop', 'error', 'question', 'warning', 'information']]
DefaultButtonType = Literal['button1', 'button2', 'button3', 'button4']
ModalType = Literal['application', 'system', 'task']
OptionsType = Optional[List[Literal['help', 'no_focus', 'set_foreground', 'default_desktop_only', 'topmost', 'right', 'rtl_reading', 'service_notification']]]
ReturnType = Literal['ok', 'cancel', 'abort', 'retry', 'ignore', 'yes', 'no', 'close', 'help', 'try_again', 'continue']

user32 = ctypes.windll.user32


@overload
def message_box(
    hWnd: Optional[int],
    text: str,
    caption: str,
    buttons: Literal['ok'] = 'ok',
    icon: IconType = None,
    default_button: DefaultButtonType = 'button1',
    modal: ModalType = 'application',
    options: OptionsType = None
) -> Literal['ok']: ...


@overload
def message_box(
    hWnd: Optional[int],
    text: str,
    caption: str,
    buttons: Literal['ok_cancel'],
    icon: IconType = None,
    default_button: DefaultButtonType = 'button1',
    modal: ModalType = 'application',
    options: OptionsType = None
) -> Literal['ok', 'cancel']: ...


@overload
def message_box(
    hWnd: Optional[int],
    text: str,
    caption: str,
    buttons: Literal['abort_retry_ignore'],
    icon: IconType = None,
    default_button: DefaultButtonType = 'button1',
    modal: ModalType = 'application',
    options: OptionsType = None
) -> Literal['abort', 'retry', 'ignore']: ...


@overload
def message_box(
    hWnd: Optional[int],
    text: str,
    caption: str,
    buttons: Literal['yes_no_cancel'],
    icon: IconType = None,
    default_button: DefaultButtonType = 'button1',
    modal: ModalType = 'application',
    options: OptionsType = None
) -> Literal['yes', 'no', 'cancel']: ...


@overload
def message_box(
    hWnd: Optional[int],
    text: str,
    caption: str,
    buttons: Literal['yes_no'],
    icon: IconType = None,
    default_button: DefaultButtonType = 'button1',
    modal: ModalType = 'application',
    options: OptionsType = None
) -> Literal['yes', 'no']: ...


@overload
def message_box(
    hWnd: Optional[int],
    text: str,
    caption: str,
    buttons: Literal['retry_cancel'],
    icon: IconType = None,
    default_button: DefaultButtonType = 'button1',
    modal: ModalType = 'application',
    options: OptionsType = None
) -> Literal['retry', 'cancel']: ...


@overload
def message_box(
    hWnd: Optional[int],
    text: str,
    caption: str,
    buttons: Literal['cancel_try_continue'],
    icon: IconType = None,
    default_button: DefaultButtonType = 'button1',
    modal: ModalType = 'application',
    options: OptionsType = None
) -> Literal['cancel', 'try_again', 'continue']: ...


def message_box(
    hWnd: Optional[int],
    text: str,
    caption: str,
    buttons: ButtonsType = 'ok',
    icon: IconType = None,
    default_button: DefaultButtonType = 'button1',
    modal: ModalType = 'application',
    options: OptionsType = None
) -> ReturnType:
    """
    显示消息框。

    :param hWnd: 所属窗口的句柄。可以为 None。
    :param text: 要显示的消息。
    :param caption: 消息框的标题。
    :param buttons: 要显示的按钮。
    :param icon: 要显示的图标。
    :param default_button: 默认按钮。
    :param modal: 消息框的模态。
    :param options: 其他杂项选项列表。
    :return: 表示用户点击的按钮的字符串。
    """
    uType = 0

    # --- 按钮类型 ---
    match buttons:
        case 'ok':
            uType |= MB_OK
        case 'ok_cancel':
            uType |= MB_OKCANCEL
        case 'abort_retry_ignore':
            uType |= MB_ABORTRETRYIGNORE
        case 'yes_no_cancel':
            uType |= MB_YESNOCANCEL
        case 'yes_no':
            uType |= MB_YESNO
        case 'retry_cancel':
            uType |= MB_RETRYCANCEL
        case 'cancel_try_continue':
            uType |= MB_CANCELTRYCONTINUE
        case _:
            assert_never(buttons)

    # --- 图标类型 ---
    if icon:
        match icon:
            case 'stop' | 'error':
                uType |= MB_ICONSTOP
            case 'question':
                uType |= MB_ICONQUESTION
            case 'warning':
                uType |= MB_ICONWARNING
            case 'information':
                uType |= MB_ICONINFORMATION
            case _:
                assert_never(icon)

    # --- 默认按钮 ---
    match default_button:
        case 'button1':
            uType |= MB_DEFBUTTON1
        case 'button2':
            uType |= MB_DEFBUTTON2
        case 'button3':
            uType |= MB_DEFBUTTON3
        case 'button4':
            uType |= MB_DEFBUTTON4
        case _:
            assert_never(default_button)

    # --- 模态 ---
    match modal:
        case 'application':
            uType |= MB_APPLMODAL
        case 'system':
            uType |= MB_SYSTEMMODAL
        case 'task':
            uType |= MB_TASKMODAL
        case _:
            assert_never(modal)

    # --- 其他选项 ---
    if options:
        for option in options:
            match option:
                case 'help':
                    uType |= MB_HELP
                case 'no_focus':
                    uType |= MB_NOFOCUS
                case 'set_foreground':
                    uType |= MB_SETFOREGROUND
                case 'default_desktop_only':
                    uType |= MB_DEFAULT_DESKTOP_ONLY
                case 'topmost':
                    uType |= MB_TOPMOST
                case 'right':
                    uType |= MB_RIGHT
                case 'rtl_reading':
                    uType |= MB_RTLREADING
                case 'service_notification':
                    uType |= MB_SERVICE_NOTIFICATION
                case _:
                    assert_never(option)

    result = user32.MessageBoxW(hWnd, text, caption, uType)

    match result:
        case 1:  # IDOK
            return 'ok'
        case 2:  # IDCANCEL
            return 'cancel'
        case 3:  # IDABORT
            return 'abort'
        case 4:  # IDRETRY
            return 'retry'
        case 5:  # IDIGNORE
            return 'ignore'
        case 6:  # IDYES
            return 'yes'
        case 7:  # IDNO
            return 'no'
        case 8:  # IDCLOSE
            return 'close'
        case 9:  # IDHELP
            return 'help'
        case 10:  # IDTRYAGAIN
            return 'try_again'
        case 11:  # IDCONTINUE
            return 'continue'
        case _:
            # 对于标准消息框，不应发生这种情况
            raise RuntimeError(f"Unknown MessageBox return code: {result}")


if __name__ == '__main__':
    # 示例用法
    response = message_box(
        None,
        "是否要退出程序？",
        "确认",
        buttons='yes_no',
        icon='question'
    )

    if response == 'yes':
        print("程序退出。")
    else:
        print("程序继续运行。")

    message_box(
        None,
        "操作已完成。",
        "通知",
        buttons='ok',
        icon='information'
    )