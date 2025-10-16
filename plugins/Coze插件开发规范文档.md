# Coze 插件开发规范文档

> 基于抖音无水印视频解析插件开发经验总结

## 目录
- [1. 基本结构](#1-基本结构)
- [2. 导入规范](#2-导入规范)
- [3. 输入输出规范](#3-输入输出规范)
- [4. handler 函数规范](#4-handler-函数规范)
- [5. 依赖库管理](#5-依赖库管理)
- [6. 错误处理规范](#6-错误处理规范)
- [7. 日志使用规范](#7-日志使用规范)
- [8. 常见问题与解决方案](#8-常见问题与解决方案)
- [9. 部署与测试](#9-部署与测试)
- [10. 最佳实践](#10-最佳实践)

---

## 1. 基本结构

### 1.1 文件命名
- 插件主文件通常命名为与功能相关的名称，如 `douyin.py`
- 文件路径格式：`/api/{插件名}/{插件名}.py`

### 1.2 文件模板
```python
# -*- coding: utf-8 -*-
"""
插件功能描述
"""

import re
import json
from runtime import Args
from typings.{插件名}.{插件名} import Input, Output

# 全局变量和常量定义
HEADERS = [...]

# 辅助函数
def helper_function():
    pass

# 主处理函数
def handler(args: Args[Input]) -> Output:
    """
    Coze 插件入口函数
    """
    pass
```

---

## 2. 导入规范

### 2.1 必须的导入
```python
from runtime import Args
from typings.{插件名}.{插件名} import Input, Output
```

⚠️ **重要规则**：
- **必须**从 `runtime` 导入 `Args`
- **必须**从 `typings` 导入 `Input` 和 `Output`
- **不要**使用 `try-except` 来兼容本地环境
- **不要**自定义 `Input` 和 `Output` 类型

### 2.2 标准库导入
```python
import re
import json
import pycurl
from io import BytesIO
```

### 2.3 错误示例 ❌
```python
# 错误：尝试兼容本地环境
try:
    from runtime import Args
except ImportError:
    class Args:
        pass

# 错误：自定义类型
from typing import TypedDict
class Input(TypedDict):
    share_url: str
```

---

## 3. 输入输出规范

### 3.1 Input 定义
Input 由 Coze 平台的 Metadata 定义，不在代码中定义。

**Metadata 配置示例**：
```json
{
  "type": "object",
  "properties": {
    "share_url": {
      "type": "string",
      "description": "抖音分享链接或包含链接的文本"
    }
  },
  "required": ["share_url"]
}
```

### 3.2 Output 定义
Output 也由 Metadata 定义，代码中只需要返回符合格式的字典。

**Metadata 配置示例**：
```json
{
  "type": "object",
  "properties": {
    "status": {"type": "string"},
    "title": {"type": "string"},
    "video_id": {"type": "string"},
    "download_url": {"type": "string"},
    "error": {"type": "string"}
  }
}
```

### 3.3 返回值格式
```python
# 成功时
return {
    "status": "success",
    "title": "视频标题",
    "video_id": "123456",
    "download_url": "https://...",
    "error": ""
}

# 失败时
return {
    "status": "error",
    "title": "",
    "video_id": "",
    "download_url": "",
    "error": "错误描述信息"
}
```

⚠️ **重要规则**：
- **所有字段**都必须存在，即使为空值
- 使用 `status` 字段标识成功/失败
- 失败时，`error` 字段必须包含错误描述

---

## 4. handler 函数规范

### 4.1 函数签名
```python
def handler(args: Args[Input]) -> Output:
    """
    Each file needs to export a function named `handler`.
    This function is the entrance to the Tool.

    Parameters:
    args: parameters of the entry function.
    args.input - input parameters
    args.logger - logger instance used to print logs

    Returns:
    Output: 包含结果的字典
    """
```

⚠️ **关键点**：
- 函数名**必须**是 `handler`
- 签名**必须**是 `handler(args: Args[Input]) -> Output`
- 必须有文档字符串

### 4.2 获取输入参数

**问题**：`args.input` 的类型在不同情况下可能不同

**解决方案**：使用多种方式兼容
```python
def handler(args: Args[Input]) -> Output:
    try:
        # 获取输入参数 - args.input 可能是字符串、字典或对象
        share_url = ""

        # 方式1: 直接是字符串（单参数情况）
        if isinstance(args.input, str):
            share_url = args.input
        # 方式2: 对象属性方式
        elif hasattr(args.input, 'share_url'):
            share_url = args.input.share_url
        # 方式3: 字典方式
        elif isinstance(args.input, dict):
            share_url = args.input.get("share_url", "")

        if not share_url:
            return {...}  # 返回错误
```

**检查顺序很重要**：
1. 先检查 `isinstance(args.input, str)` - 最常见
2. 再检查 `hasattr(args.input, 'share_url')` - 对象属性
3. 最后检查 `isinstance(args.input, dict)` - 字典

### 4.3 完整的 handler 模板
```python
def handler(args: Args[Input]) -> Output:
    try:
        # 1. 获取输入参数
        share_url = ""
        if isinstance(args.input, str):
            share_url = args.input
        elif hasattr(args.input, 'share_url'):
            share_url = args.input.share_url
        elif isinstance(args.input, dict):
            share_url = args.input.get("share_url", "")

        # 2. 参数验证
        if not share_url:
            return {
                "status": "error",
                # ... 所有字段的默认值
                "error": "缺少share_url参数"
            }

        # 3. 记录日志
        if hasattr(args, 'logger'):
            args.logger.info(f"开始处理: {share_url}")

        # 4. 执行业务逻辑
        result = process_business_logic(share_url)

        # 5. 记录成功日志
        if hasattr(args, 'logger'):
            args.logger.info(f"处理成功")

        # 6. 返回结果
        return result

    except Exception as e:
        # 7. 错误处理
        if hasattr(args, 'logger'):
            args.logger.error(f"处理失败: {str(e)}")

        return {
            "status": "error",
            # ... 所有字段的默认值
            "error": str(e)
        }
```

---

## 5. 依赖库管理

### 5.1 可用的标准库
以下标准库可以直接使用：
- `re` - 正则表达式
- `json` - JSON 处理
- `os`, `sys` - 系统操作
- `datetime` - 日期时间
- `io` - IO 操作
- `urllib` - URL 处理

### 5.2 第三方库

#### 可用的第三方库
- `pycurl` - HTTP 请求（高性能）
- `requests` - HTTP 请求（简单易用）
- 其他需要在 Coze 平台配置中声明

#### 安装方式
在 Coze 平台的"依赖配置"中添加：
```
pycurl
requests
```

⚠️ **注意**：
- 必须在 Coze 平台配置依赖，不能只在代码中导入
- 部署后需要等待依赖安装完成

### 5.3 pycurl 使用示例
```python
import pycurl
from io import BytesIO

def curl_get(url, headers=None, follow_redirects=True):
    """使用 pycurl 发送 GET 请求"""
    buffer = BytesIO()
    header_buffer = BytesIO()

    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.WRITEDATA, buffer)
    c.setopt(c.HEADERFUNCTION, header_buffer.write)

    if headers:
        c.setopt(c.HTTPHEADER, headers)

    if follow_redirects:
        c.setopt(c.FOLLOWLOCATION, True)

    c.setopt(c.TIMEOUT, 30)
    c.setopt(c.CONNECTTIMEOUT, 10)

    try:
        c.perform()
        status_code = c.getinfo(c.RESPONSE_CODE)
        final_url = c.getinfo(c.EFFECTIVE_URL)
        c.close()

        body = buffer.getvalue().decode('utf-8')
        return {
            'status_code': status_code,
            'body': body,
            'final_url': final_url
        }
    except Exception as e:
        c.close()
        raise Exception(f"请求失败: {str(e)}")
```

---

## 6. 错误处理规范

### 6.1 统一的错误返回格式
```python
def create_error_response(error_msg: str) -> dict:
    """创建统一的错误响应"""
    return {
        "status": "error",
        "title": "",
        "author": "",
        "download_url_no_watermark": "",
        "download_url_with_watermark": "",
        "video_id": "",
        "digg_count": 0,
        "comment_count": 0,
        "share_count": 0,
        "collect_count": 0,
        "duration": 0.0,
        "width": 0,
        "height": 0,
        "error": error_msg
    }
```

### 6.2 异常捕获层次
```python
def handler(args: Args[Input]) -> Output:
    try:
        # 主逻辑
        try:
            result = risky_operation()
        except SpecificError as e:
            # 处理特定错误
            return create_error_response(f"特定错误: {str(e)}")

        return result

    except Exception as e:
        # 捕获所有未处理的异常
        if hasattr(args, 'logger'):
            args.logger.error(f"未预期的错误: {str(e)}")
        return create_error_response(str(e))
```

### 6.3 常见错误类型
```python
# 参数错误
if not param:
    return create_error_response("缺少必需参数")

# 网络错误
try:
    response = curl_get(url)
except Exception as e:
    return create_error_response(f"网络请求失败: {str(e)}")

# 数据解析错误
try:
    data = json.loads(json_str)
except json.JSONDecodeError as e:
    return create_error_response(f"JSON解析失败: {str(e)}")

# 业务逻辑错误
if not video_info:
    return create_error_response("未找到视频信息")
```

---

## 7. 日志使用规范

### 7.1 日志级别
```python
# INFO - 正常流程信息
args.logger.info("开始处理请求")
args.logger.info(f"解析视频ID: {video_id}")

# ERROR - 错误信息
args.logger.error(f"请求失败: {error}")
args.logger.error(f"解析失败: {str(e)}")
```

### 7.2 日志使用模板
```python
# 开始处理
if hasattr(args, 'logger'):
    args.logger.info(f"开始处理: {input_param}")

# 关键步骤
if hasattr(args, 'logger'):
    args.logger.info(f"步骤完成: {step_name}")

# 成功完成
if hasattr(args, 'logger'):
    args.logger.info(f"处理成功: {result_summary}")

# 错误处理
if hasattr(args, 'logger'):
    args.logger.error(f"处理失败: {error_detail}")
```

### 7.3 日志注意事项
⚠️ **重要**：
- 始终使用 `if hasattr(args, 'logger')` 检查
- 不要在日志中输出敏感信息
- 日志信息要简洁明了
- 使用 f-string 格式化

---

## 8. 常见问题与解决方案

### 8.1 'NoneType' object is not callable

**问题原因**：
```python
# 错误代码
share_url = args.input.get("share_url", "")
# args.input 可能不是字典，没有 get 方法
```

**解决方案**：
```python
# 正确代码
if isinstance(args.input, str):
    share_url = args.input
elif hasattr(args.input, 'share_url'):
    share_url = args.input.share_url
elif isinstance(args.input, dict):
    share_url = args.input.get("share_url", "")
```

### 8.2 ModuleNotFoundError: No module named 'pycurl'

**问题原因**：
- 依赖未在 Coze 平台配置
- 依赖正在安装中

**解决方案**：
1. 在 Coze 平台的"依赖配置"中添加 `pycurl`
2. 保存并重新部署
3. 等待几分钟让依赖安装完成

### 8.3 sub function not found

**问题原因**：
- 函数未正确部署
- 函数路径配置错误

**解决方案**：
1. 检查文件名和路径是否正确
2. 重新部署插件
3. 确保 handler 函数存在且签名正确

### 8.4 Invalid Request

**问题原因**：
- 返回值格式不符合 Output 定义
- 缺少必需的字段

**解决方案**：
```python
# 确保返回所有定义的字段
return {
    "status": "success",      # 必需
    "video_id": video_id,     # 必需
    "title": title,           # 必需
    # ... 所有其他字段
    "error": ""               # 失败时为空字符串
}
```

---

## 9. 部署与测试

### 9.1 部署流程
1. **编写代码** - 在 Coze IDE 中编写 `handler` 函数
2. **配置依赖** - 在"依赖配置"中添加第三方库
3. **配置 Metadata**：
   - Input Schema
   - Output Schema
   - 函数描述
4. **保存** - 保存代码和配置
5. **部署** - 点击"部署"按钮
6. **等待** - 等待部署完成（约 10-30 秒）

### 9.2 测试方法

#### 方法 1: 在线测试
```
Test run "插件名" started
Executing...
[日志输出]
Execute success, cost: XXms
```

#### 方法 2: 本地测试
创建测试脚本：
```python
class MockArgs:
    class MockInput:
        def get(self, key, default=""):
            return "测试输入"

    input = MockInput()

    class MockLogger:
        @staticmethod
        def info(msg):
            print(f"[INFO] {msg}")

        @staticmethod
        def error(msg):
            print(f"[ERROR] {msg}")

    logger = MockLogger()

# 测试
from douyin import handler
args = MockArgs()
result = handler(args)
print(json.dumps(result, ensure_ascii=False, indent=2))
```

### 9.3 测试检查清单
- [ ] 正常输入能返回正确结果
- [ ] 空输入返回错误信息
- [ ] 无效输入返回错误信息
- [ ] 所有字段都存在
- [ ] 日志输出正常
- [ ] 性能符合预期（< 10秒）

---

## 10. 最佳实践

### 10.1 代码组织
```python
# 1. 导入
from runtime import Args
from typings.xxx.xxx import Input, Output

# 2. 常量定义
TIMEOUT = 30
MAX_RETRIES = 3

# 3. 辅助函数
def helper_function():
    pass

# 4. 主函数
def handler(args: Args[Input]) -> Output:
    pass
```

### 10.2 性能优化
```python
# 1. 设置合理的超时
c.setopt(c.TIMEOUT, 30)
c.setopt(c.CONNECTTIMEOUT, 10)

# 2. 避免重复请求
cache = {}
if url in cache:
    return cache[url]

# 3. 使用高性能库
import pycurl  # 而不是 requests
```

### 10.3 安全性
```python
# 1. 参数验证
if not share_url or not isinstance(share_url, str):
    return error_response("无效的输入参数")

# 2. URL 白名单
ALLOWED_DOMAINS = ['douyin.com', 'iesdouyin.com']
if not any(domain in url for domain in ALLOWED_DOMAINS):
    return error_response("不支持的域名")

# 3. 错误信息脱敏
return error_response("处理失败")  # 而不是暴露详细错误
```

### 10.4 可维护性
```python
# 1. 函数拆分
def extract_video_id(url: str) -> str:
    """提取视频ID"""
    pass

def parse_video_info(data: dict) -> dict:
    """解析视频信息"""
    pass

# 2. 清晰的注释
def handler(args: Args[Input]) -> Output:
    """
    处理抖音视频解析请求

    步骤：
    1. 提取分享链接
    2. 访问页面获取数据
    3. 解析JSON
    4. 返回结果
    """
    pass

# 3. 常量提取
VIDEO_ID_PAGE_KEY = "video_(id)/page"
NOTE_ID_PAGE_KEY = "note_(id)/page"
```

### 10.5 调试技巧
```python
# 1. 详细的日志
args.logger.info(f"步骤1: 提取URL - {share_url}")
args.logger.info(f"步骤2: 访问页面 - {standard_url}")
args.logger.info(f"步骤3: 解析JSON - 找到 {len(item_list)} 条记录")

# 2. 错误信息包含上下文
except Exception as e:
    error_msg = f"在步骤{step_name}失败: {str(e)}"
    args.logger.error(error_msg)
    return error_response(error_msg)

# 3. 返回调试信息（开发阶段）
return {
    "status": "success",
    "result": result,
    "debug_info": {
        "video_id": video_id,
        "url": standard_url
    }
}
```

---

## 附录

### A. 完整示例代码
参考文件：[douyin.py](douyin.py)

### B. 测试用例
参考文件：[test_douyin_plugin.py](test_douyin_plugin.py)

### C. 错误代码对照表

| 错误代码 | 含义 | 解决方案 |
|---------|------|---------|
| 304000001 | sub function not found | 重新部署插件 |
| 400 | Invalid Request | 检查返回值格式 |
| 500 | Internal Server Error | 检查代码逻辑错误 |

### D. 快速参考

#### 最小可用模板
```python
from runtime import Args
from typings.xxx.xxx import Input, Output

def handler(args: Args[Input]) -> Output:
    try:
        # 获取输入
        input_data = args.input if isinstance(args.input, str) else args.input.field_name

        # 处理逻辑
        result = process(input_data)

        # 返回结果
        return {
            "status": "success",
            "data": result,
            "error": ""
        }
    except Exception as e:
        return {
            "status": "error",
            "data": "",
            "error": str(e)
        }
```

---

## 总结

### 核心规则
1. ✅ **必须**使用 `from runtime import Args`
2. ✅ **必须**使用 `def handler(args: Args[Input]) -> Output`
3. ✅ **必须**返回所有定义的字段
4. ✅ **必须**使用多种方式兼容 `args.input`
5. ✅ **必须**在 Coze 平台配置依赖

### 常见错误
1. ❌ 自定义 Input/Output 类型
2. ❌ 使用 `args.input.get()` 而不检查类型
3. ❌ 返回值缺少字段
4. ❌ 未配置依赖就导入库
5. ❌ 忘记检查 logger 是否存在

### 开发流程
```
编写代码 → 配置依赖 → 配置 Metadata → 部署 → 测试 → 上线
```

---

**文档版本**: v1.0
**更新日期**: 2025-10-16
**基于项目**: 抖音无水印视频解析插件
