import ctypes
from ctypes import wintypes
import time
from typing import List, Tuple, Optional
from typing import Literal

__all__ = [
    "TaskDialog",
    "TDCBF_OK_BUTTON", "TDCBF_YES_BUTTON", "TDCBF_NO_BUTTON", "TDCBF_CANCEL_BUTTON",
    "TDCBF_RETRY_BUTTON", "TDCBF_CLOSE_BUTTON",
    "IDOK", "IDCANCEL", "IDABORT", "IDRETRY", "IDIGNORE", "IDYES", "IDNO", "IDCLOSE",
    "TD_WARNING_ICON", "TD_ERROR_ICON", "TD_INFORMATION_ICON", "TD_SHIELD_ICON"
]

# --- Windows API 常量定义 ---

# 常用按钮
TDCBF_OK_BUTTON = 0x0001
TDCBF_YES_BUTTON = 0x0002
TDCBF_NO_BUTTON = 0x0004
TDCBF_CANCEL_BUTTON = 0x0008
TDCBF_RETRY_BUTTON = 0x0010
TDCBF_CLOSE_BUTTON = 0x0020

# 对话框返回值
IDOK = 1
IDCANCEL = 2
IDABORT = 3
IDRETRY = 4
IDIGNORE = 5
IDYES = 6
IDNO = 7
IDCLOSE = 8


# 标准图标 (使用 MAKEINTRESOURCE 宏)
def MAKEINTRESOURCE(i: int) -> wintypes.LPWSTR:
    return wintypes.LPWSTR(i)


TD_WARNING_ICON = MAKEINTRESOURCE(65535)
TD_ERROR_ICON = MAKEINTRESOURCE(65534)
TD_INFORMATION_ICON = MAKEINTRESOURCE(65533)
TD_SHIELD_ICON = MAKEINTRESOURCE(65532)

# Task Dialog 标志
TDF_ENABLE_HYPERLINKS = 0x0001
TDF_USE_HICON_MAIN = 0x0002
TDF_USE_HICON_FOOTER = 0x0004
TDF_ALLOW_DIALOG_CANCELLATION = 0x0008
TDF_USE_COMMAND_LINKS = 0x0010
TDF_USE_COMMAND_LINKS_NO_ICON = 0x0020
TDF_EXPAND_FOOTER_AREA = 0x0040
TDF_EXPANDED_BY_DEFAULT = 0x0080
TDF_VERIFICATION_FLAG_CHECKED = 0x0100
TDF_SHOW_PROGRESS_BAR = 0x0200
TDF_SHOW_MARQUEE_PROGRESS_BAR = 0x0400
TDF_CALLBACK_TIMER = 0x0800
TDF_POSITION_RELATIVE_TO_WINDOW = 0x1000
TDF_RTL_LAYOUT = 0x2000
TDF_NO_DEFAULT_RADIO_BUTTON = 0x4000
TDF_CAN_BE_MINIMIZED = 0x8000

# Task Dialog 通知
TDN_CREATED = 0
TDN_NAVIGATED = 1
TDN_BUTTON_CLICKED = 2
TDN_HYPERLINK_CLICKED = 3
TDN_TIMER = 4
TDN_DESTROYED = 5
TDN_RADIO_BUTTON_CLICKED = 6
TDN_DIALOG_CONSTRUCTED = 7
TDN_VERIFICATION_CLICKED = 8
TDN_HELP = 9
TDN_EXPANDO_BUTTON_CLICKED = 10

# Windows 消息
WM_USER = 0x0400
TDM_SET_PROGRESS_BAR_POS = WM_USER + 114

CommonButtonLiteral = Literal["ok", "yes", "no", "cancel", "retry", "close"]
IconLiteral = Literal["warning", "error", "information", "shield"]


# --- C 结构体定义 (使用 ctypes) ---

class TASKDIALOG_BUTTON(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("nButtonID", ctypes.c_int),
                ("pszButtonText", wintypes.LPCWSTR)]


# 定义回调函数指针原型
PFTASKDIALOGCALLBACK = ctypes.WINFUNCTYPE(
    ctypes.HRESULT,  # 返回值
    wintypes.HWND,  # hwnd
    ctypes.c_uint,  # msg
    ctypes.c_size_t,  # wParam
    ctypes.c_size_t,  # lParam
    ctypes.c_ssize_t  # lpRefData
)


class TASKDIALOGCONFIG(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("hwndParent", wintypes.HWND),
        ("hInstance", wintypes.HINSTANCE),
        ("dwFlags", ctypes.c_uint),
        ("dwCommonButtons", ctypes.c_uint),
        ("pszWindowTitle", wintypes.LPCWSTR),
        ("pszMainIcon", wintypes.LPCWSTR),
        ("pszMainInstruction", wintypes.LPCWSTR),
        ("pszContent", wintypes.LPCWSTR),
        ("cButtons", ctypes.c_uint),
        ("pButtons", ctypes.POINTER(TASKDIALOG_BUTTON)),
        ("nDefaultButton", ctypes.c_int),
        ("cRadioButtons", ctypes.c_uint),
        ("pRadioButtons", ctypes.POINTER(TASKDIALOG_BUTTON)),
        ("nDefaultRadioButton", ctypes.c_int),
        ("pszVerificationText", wintypes.LPCWSTR),
        ("pszExpandedInformation", wintypes.LPCWSTR),
        ("pszExpandedControlText", wintypes.LPCWSTR),
        ("pszCollapsedControlText", wintypes.LPCWSTR),
        ("pszFooterIcon", wintypes.LPCWSTR),
        ("pszFooter", wintypes.LPCWSTR),
        ("pfCallback", PFTASKDIALOGCALLBACK),  # 使用定义好的原型
        ("lpCallbackData", ctypes.c_ssize_t),
        ("cxWidth", ctypes.c_uint)
    ]


# --- 加载 comctl32.dll 并定义函数原型 ---

comctl32 = ctypes.WinDLL('comctl32')
user32 = ctypes.WinDLL('user32')

TaskDialogIndirect = comctl32.TaskDialogIndirect
TaskDialogIndirect.restype = ctypes.HRESULT
TaskDialogIndirect.argtypes = [
    ctypes.POINTER(TASKDIALOGCONFIG),
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(wintypes.BOOL)
]


# --- Python 封装类 ---

class TaskDialog:
    """
    一个用于显示 Windows TaskDialog 的 Python 封装类。
    支持自定义按钮、单选按钮、进度条、验证框等。
    """

    def __init__(self,
        parent_hwnd: Optional[int] = None,
        title: str = "Task Dialog",
        main_instruction: str = "",
        content: str = "",
        common_buttons: int | List[CommonButtonLiteral] = TDCBF_OK_BUTTON,
        main_icon: Optional[wintypes.LPWSTR | int | IconLiteral] = None,
        footer: str = "",
        custom_buttons: Optional[List[Tuple[int, str]]] = None,
        default_button: int = 0,
        radio_buttons: Optional[List[Tuple[int, str]]] = None,
        default_radio_button: int = 0,
        verification_text: Optional[str] = None,
        verification_checked_by_default: bool = False,
        show_progress_bar: bool = False,
        show_marquee_progress_bar: bool = False
    ):
        """初始化 TaskDialog 实例。

        :param parent_hwnd: 父窗口的句柄。
        :param title: 对话框窗口的标题。
        :param main_instruction: 对话框的主要指令文本。
        :param content: 对话框的详细内容文本。
        :param common_buttons: 要显示的通用按钮。可以是以下两种形式之一：
                               1. TDCBF_* 常量的按位或组合 (例如 TDCBF_OK_BUTTON | TDCBF_CANCEL_BUTTON)
                               2. 字符串列表，支持 "ok", "yes", "no", "cancel", "retry", "close"
        :param main_icon: 主图标。可以是以下几种形式之一：
                          1. TD_*_ICON 常量之一
                          2. HICON 句柄
                          3. 字符串："warning", "error", "information", "shield"
        :param footer: 页脚区域显示的文本。
        :param custom_buttons: 自定义按钮列表。每个元组包含 (按钮ID, 按钮文本)。
        :param default_button: 默认按钮的ID。可以是通用按钮ID (例如 IDOK) 或自定义按钮ID。
        :param radio_buttons: 单选按钮列表。每个元组包含 (按钮ID, 按钮文本)。
        :param default_radio_button: 默认选中的单选按钮的ID。
        :param verification_text: 验证复选框的文本。如果为 None，则不显示复选框。
        :param verification_checked_by_default: 验证复选框是否默认勾选。
        :param show_progress_bar: 是否显示标准进度条。
        :param show_marquee_progress_bar: 是否显示跑马灯式进度条。
        """
        self.config = TASKDIALOGCONFIG()
        self.config.cbSize = ctypes.sizeof(TASKDIALOGCONFIG)
        self.config.hwndParent = parent_hwnd
        self.config.dwFlags = TDF_ALLOW_DIALOG_CANCELLATION | TDF_POSITION_RELATIVE_TO_WINDOW
        self.config.dwCommonButtons = self._process_common_buttons(common_buttons)
        self.config.pszWindowTitle = title
        self.config.pszMainInstruction = main_instruction
        self.config.pszContent = content
        self.config.pszFooter = footer

        self.progress: int = 0
        if show_progress_bar or show_marquee_progress_bar:
            # 进度条暂时还没实现
            raise NotImplementedError("Progress bar is not implemented yet.")
            self.config.dwFlags |= TDF_CALLBACK_TIMER
            if show_progress_bar:
                self.config.dwFlags |= TDF_SHOW_PROGRESS_BAR
            else:
                self.config.dwFlags |= TDF_SHOW_MARQUEE_PROGRESS_BAR

        # 将实例方法转为 C 回调函数指针。
        # 必须将其保存为实例成员，否则会被垃圾回收！
        self._callback_func_ptr = PFTASKDIALOGCALLBACK(self._callback)
        self.config.pfCallback = self._callback_func_ptr
        # 将本实例的id作为lpCallbackData传递，以便在回调中识别
        self.config.lpCallbackData = id(self)

        # --- 图标设置 ---
        processed_icon = self._process_main_icon(main_icon)
        if processed_icon is not None:
            if isinstance(processed_icon, wintypes.LPWSTR):
                self.config.pszMainIcon = processed_icon
            else:
                self.config.dwFlags |= TDF_USE_HICON_MAIN
                self.config.hMainIcon = processed_icon

        # --- 自定义按钮设置 ---
        self.custom_buttons_list = []
        if custom_buttons:
            self.config.cButtons = len(custom_buttons)
            button_array_type = TASKDIALOG_BUTTON * len(custom_buttons)
            self.custom_buttons_list = button_array_type()
            for i, (btn_id, btn_text) in enumerate(custom_buttons):
                self.custom_buttons_list[i].nButtonID = btn_id
                self.custom_buttons_list[i].pszButtonText = btn_text
            self.config.pButtons = self.custom_buttons_list

        if default_button:
            self.config.nDefaultButton = default_button

        # --- 单选按钮设置 ---
        self.radio_buttons_list = []
        if radio_buttons:
            self.config.cRadioButtons = len(radio_buttons)
            radio_array_type = TASKDIALOG_BUTTON * len(radio_buttons)
            self.radio_buttons_list = radio_array_type()
            for i, (btn_id, btn_text) in enumerate(radio_buttons):
                self.radio_buttons_list[i].nButtonID = btn_id
                self.radio_buttons_list[i].pszButtonText = btn_text
            self.config.pRadioButtons = self.radio_buttons_list

        if default_radio_button:
            self.config.nDefaultRadioButton = default_radio_button

        # --- 验证复选框设置 ---
        if verification_text:
            self.config.pszVerificationText = verification_text
            if verification_checked_by_default:
                self.config.dwFlags |= TDF_VERIFICATION_FLAG_CHECKED

    def _process_common_buttons(self, common_buttons: int | List[CommonButtonLiteral]) -> int:
        """处理 common_buttons 参数，支持常量和字符串列表两种形式"""
        if isinstance(common_buttons, int):
            # 直接使用 Win32 常量
            return common_buttons
        elif isinstance(common_buttons, list):
            # 处理字符串列表
            result = 0
            for button in common_buttons:
                # 使用 match 和 assert_never 进行类型检查
                match button:
                    case "ok":
                        result |= TDCBF_OK_BUTTON
                    case "yes":
                        result |= TDCBF_YES_BUTTON
                    case "no":
                        result |= TDCBF_NO_BUTTON
                    case "cancel":
                        result |= TDCBF_CANCEL_BUTTON
                    case "retry":
                        result |= TDCBF_RETRY_BUTTON
                    case "close":
                        result |= TDCBF_CLOSE_BUTTON
                    case _:
                        # 这在实际中不会发生，因为类型检查会阻止它
                        from typing import assert_never
                        assert_never(button)
            return result
        else:
            raise TypeError("common_buttons must be either an int or a list of strings")

    def _process_main_icon(self, main_icon: Optional[wintypes.LPWSTR | int | IconLiteral]) -> Optional[wintypes.LPWSTR | int]:
        """处理 main_icon 参数，支持常量和字符串两种形式"""
        if main_icon is None:
            return None
        elif isinstance(main_icon, (wintypes.LPWSTR, int)):
            # 直接使用 Win32 常量或 HICON 句柄
            return main_icon
        elif isinstance(main_icon, str):
            # 处理字符串
            match main_icon:
                case "warning":
                    return TD_WARNING_ICON
                case "error":
                    return TD_ERROR_ICON
                case "information":
                    return TD_INFORMATION_ICON
                case "shield":
                    return TD_SHIELD_ICON
                case _:
                    # 这在实际中不会发生，因为类型检查会阻止它
                    from typing import assert_never
                    assert_never(main_icon)
        else:
            raise TypeError("main_icon must be None, a Windows constant, or a string")

    def _callback(self, hwnd: wintypes.HWND, msg: int, wParam: int, lParam: int, lpRefData: int) -> int:
        # 仅当 lpRefData 指向的是当前这个对象实例时才处理
        if lpRefData != id(self):
            return 0  # S_OK

        if msg == TDN_TIMER:
            # 更新进度条
            if self.progress < 100:
                self.progress += 5
                # 发送消息给对话框来更新进度条位置
                user32.SendMessageW(hwnd, TDM_SET_PROGRESS_BAR_POS, self.progress, 0)
            else:
                # 示例：进度达到100%后，可以模拟点击OK按钮关闭对话框
                # from ctypes import wintypes
                # user32.PostMessageW(hwnd, wintypes.UINT(1125), IDOK, 0) # TDM_CLICK_BUTTON
                pass

        elif msg == TDN_DESTROYED:
            # 对话框已销毁
            pass

        return 0  # S_OK

    def show(self) -> Tuple[int, int, bool]:
        """
        显示对话框并返回用户交互的结果。

        :return: 一个元组 (button_id, radio_button_id, verification_checked)
                 - button_id: 用户点击的按钮ID (例如 IDOK, IDCANCEL)。
                 - radio_button_id: 用户选择的单选按钮的ID。
                 - verification_checked: 验证复选框是否被勾选 (True/False)。
        """
        pnButton = ctypes.c_int(0)
        pnRadioButton = ctypes.c_int(0)
        pfVerificationFlagChecked = wintypes.BOOL(False)

        hr = TaskDialogIndirect(
            ctypes.byref(self.config),
            ctypes.byref(pnButton),
            ctypes.byref(pnRadioButton),
            ctypes.byref(pfVerificationFlagChecked)
        )

        if hr == 0:  # S_OK
            return pnButton.value, pnRadioButton.value, bool(pfVerificationFlagChecked.value)
        else:
            raise ctypes.WinError(hr)


# --- 示例用法 ---
if __name__ == '__main__':

    print("--- 示例 1: 简单信息框 ---")
    dlg_simple = TaskDialog(
        title="操作成功",
        main_instruction="您的操作已成功完成。",
        content="文件已保存到您的文档目录。",
        common_buttons=["ok"],
        main_icon="information"
    )
    result_simple, _, _ = dlg_simple.show()
    print(f"用户点击了按钮: {result_simple} (1=OK)\n")

    print("--- 示例 2: 确认框 ---")
    dlg_confirm = TaskDialog(
        title="确认删除",
        main_instruction="您确定要永久删除这个文件吗?",
        content="这个操作无法撤销。文件将被立即删除。",
        common_buttons=["yes", "no", "cancel"],
        main_icon="warning",
        default_button=IDNO
    )
    result_confirm, _, _ = dlg_confirm.show()
    if result_confirm == IDYES:
        print("用户选择了“是”。")
    elif result_confirm == IDNO:
        print("用户选择了“否”。")
    elif result_confirm == IDCANCEL:
        print("用户选择了“取消”。")
    print(f"返回的按钮ID: {result_confirm}\n")

    # 示例 3
    print("--- 示例 3: 自定义按钮 ---")
    CUSTOM_BUTTON_SAVE_ID = 101
    CUSTOM_BUTTON_DONT_SAVE_ID = 102
    my_buttons = [
        (CUSTOM_BUTTON_SAVE_ID, "保存并退出"),
        (CUSTOM_BUTTON_DONT_SAVE_ID, "不保存直接退出")
    ]
    dlg_custom = TaskDialog(
        title="未保存的更改",
        main_instruction="文档中有未保存的更改，您想如何处理？",
        custom_buttons=my_buttons,
        common_buttons=["cancel"],
        main_icon="warning",
        footer="这是一个重要的提醒！"
    )
    result_custom, _, _ = dlg_custom.show()
    if result_custom == CUSTOM_BUTTON_SAVE_ID:
        print("用户选择了“保存并退出”。")
    elif result_custom == CUSTOM_BUTTON_DONT_SAVE_ID:
        print("用户选择了“不保存直接退出”。")
    elif result_custom == IDCANCEL:
        print("用户选择了“取消”。")
    print(f"返回的按钮ID: {result_custom}\n")

    # 示例 4: 带单选按钮和验证框的对话框
    print("--- 示例 4: 单选按钮和验证框 ---")
    RADIO_BTN_WORD_ID = 201
    RADIO_BTN_EXCEL_ID = 202
    RADIO_BTN_PDF_ID = 203

    radio_buttons = [
        (RADIO_BTN_WORD_ID, "保存为 Word 文档 (.docx)"),
        (RADIO_BTN_EXCEL_ID, "保存为 Excel 表格 (.xlsx)"),
        (RADIO_BTN_PDF_ID, "导出为 PDF 文档 (.pdf)")
    ]

    dlg_radio = TaskDialog(
        title="选择导出格式",
        main_instruction="请选择您想要导出的文件格式。",
        content="选择一个格式后，点击“确定”继续。",
        common_buttons=["ok", "cancel"],
        main_icon="information",
        radio_buttons=radio_buttons,
        default_radio_button=RADIO_BTN_PDF_ID,  # 默认选中PDF
        verification_text="设为我的默认导出选项",
        verification_checked_by_default=True
    )
    btn_id, radio_id, checked = dlg_radio.show()

    if btn_id == IDOK:
        print(f"用户点击了“确定”。")
        if radio_id == RADIO_BTN_WORD_ID:
            print("选择了导出为 Word。")
        elif radio_id == RADIO_BTN_EXCEL_ID:
            print("选择了导出为 Excel。")
        elif radio_id == RADIO_BTN_PDF_ID:
            print("选择了导出为 PDF。")

        if checked:
            print("用户勾选了“设为我的默认导出选项”。")
        else:
            print("用户未勾选“设为我的默认导出选项”。")
    else:
        print("用户点击了“取消”。")
    print(f"返回的按钮ID: {btn_id}, 单选按钮ID: {radio_id}, 验证框状态: {checked}\n")
