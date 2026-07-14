# KotoneBot DevTools Frontend 开发指南

## 代码风格

### 错误提示

- 用户可见的错误/警告/成功提示必须使用 `toaster.show()`（从 `../../ui/toaster` 导入），禁止使用内联 `div` 展示错误信息。
- 仅在对话框内部状态管理或开发调试时可例外。
