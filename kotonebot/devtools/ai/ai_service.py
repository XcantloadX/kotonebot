import base64
import json
import logging
import os
from typing import Any

import cv2
# 必须在导入 litellm 之前禁用其启动时的远程 model cost map 拉取，
# 否则冷启动会发起网络请求（失败后回退本地备份），显著拖慢启动并造成抖动
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "true")
import numpy as np

from kotonebot.devtools.errors import DevtoolsError
from kotonebot.devtools.ai.types import AiConfig

logger = logging.getLogger(__name__)

SUGGEST_PATH_PROMPT = (
    "You are an assistant that suggests a storage path for a screenshot image in a project. "
    "The project folder structure is provided below.\n\n"
    "Folder structure:\n"
    "{folder_tree}\n\n"
    "Analyze the image content and suggest a suitable directory and filename. "
    "Return ONLY valid JSON with the following fields:\n"
    '{{"suggested_dir": "relative/directory/path", "suggested_filename": "filename.png", "reason": "brief explanation"}}'
)

INFER_DEFINITIONS_PROMPT = (
    "You are a UI element naming assistant. Based on the provided screenshot and folder path, "
    "infer names and properties for each highlighted UI element.\n\n"
    "Context:\n"
    "Folder path: {folder_path}\n"
    "Image filename: {image_filename}\n\n"
    "Rules:\n"
    "- name: A dot-separated hierarchical path. "
    "General format: {{Category}}[.{{SubCategory}}[.{{SubSubCategory}}[...]]].{{ElementType}}{{ElementName}}. "
    "Category is required; SubCategory levels are optional and there can be multiple nested levels. "
    "All segments should be inferred from the folder path and image context. "
    "ElementType indicates the UI element type (e.g. Button, Text, Icon, Checkbox, Radio, Switch, Image, Box, Point). "
    "ElementName is a short, descriptive identifier.\n"
    "  Each segment (Category, SubCategory, ElementType, ElementName) must be a valid Python identifier "
    "(only letters, digits, and underscores; cannot start with a digit; no spaces or special characters). "
    "ElementType and ElementName should be concatenated without a dot between them.\n"
    "  IMPORTANT: Every name must be UNIQUE. No two definitions in the same project can share the same full name.\n"
    "  When \"Current document\" examples are provided below, follow their Category structure "
    "and naming style as closely as possible.\n"
    "  Valid examples: {{'MainMenu.ButtonStart'}}, {{'Settings.Audio.VolumeSlider'}}, {{'Dialog.Confirm.ButtonOk'}}, {{'Shop.AmountDialog.ButtonConfirm'}}\n"
    "- displayName: A Chinese description of the element's general identity or semantic purpose. "
    "Describe what the element IS, not what it currently shows or its image content. "
    "For example, a label that displays a score should be described as {{'分数标签'}} (score label), "
    "not as the current numeric value. A character portrait should be {{'角色头像'}} (character portrait), "
    "not the character's name. When the element has fixed identifying text (e.g. a button label), "
    "reference that text verbatim.\n"
    "  Examples: {{'确认按钮'}} for a button labeled '确认', {{'LIVE 按钮'}} for a button with 'LIVE' text, "
    "{{'分数标签'}} for a dynamic score display, {{'角色名文本'}} for a dynamic character name label\n"
    "- fixed: Whether the element's position is fixed within its layout. "
    "This only concerns position — NOT whether the element's content (text, images, etc.) changes. "
    "true if the element is NOT inside a scrollable or draggable container "
    "(e.g. title bar, tab bar, dialog frame buttons, HUD elements). "
    "false if it is inside a scrollable list, draggable panel, or any content area that can scroll or be dragged.\n\n"
    "Below is the full screenshot followed by cropped regions for each definition "
    "(labeled with their definitionId).\n\n"
    "Return ONLY valid JSON with this structure (no other words):\n"
    '{{"<definitionId>": {{"name": "...", "displayName": "...", "fixed": true/false, "reason": "..."}}}}'
)


def _compress_image_to_max_edge(image_bytes: bytes, max_edge: int = 1024) -> bytes:
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise DevtoolsError("Failed to decode image")
    height, width = img.shape[:2]
    longest = max(width, height)
    if longest > max_edge:
        scale = max_edge / float(longest)
        new_width = max(1, int(round(width * scale)))
        new_height = max(1, int(round(height * scale)))
        img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
    success, encoded = cv2.imencode(".png", img)
    if not success:
        raise DevtoolsError("Failed to encode compressed image")
    return encoded.tobytes()


def _build_folder_tree_text(folder_tree: list[dict]) -> str:
    def _render(node: dict, indent: int = 0) -> str:
        prefix = "  " * indent
        name = node.get("name", "")
        children = node.get("children", [])
        lines = [f"{prefix}{name}/"]
        for child in children:
            lines.append(_render(child, indent + 1))
        return "\n".join(lines)

    parts = []
    for root_node in folder_tree:
        parts.append(_render(root_node))
    return "\n".join(parts)


def suggest_document_path(
    image_bytes: bytes,
    folder_tree: list[dict],
    ai_config: AiConfig,
) -> dict:
    compressed = _compress_image_to_max_edge(image_bytes, 1024)
    b64_image = base64.b64encode(compressed).decode("utf-8")

    folder_tree_text = _build_folder_tree_text(folder_tree)

    prompt = SUGGEST_PATH_PROMPT.format(folder_tree=folder_tree_text)

    provider_type = ai_config.provider_type
    model = ai_config.model
    api_key = ai_config.api_key
    endpoint = ai_config.endpoint

    litellm_params = {
        "model": f"{provider_type}/{model}",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64_image}"},
                    },
                ],
            }
        ],
        "response_format": {"type": "json_object"},
        "stream": False,
    }

    if api_key:
        litellm_params["api_key"] = api_key

    if endpoint:
        litellm_params["api_base"] = endpoint

    import litellm
    try:
        response = litellm.completion(**litellm_params)
        content = response.choices[0].message.content
        if not content:
            raise DevtoolsError("AI returned empty response")
        result = json.loads(content)
        return {
            "suggestedDir": result.get("suggested_dir", ""),
            "suggestedFilename": result.get("suggested_filename", ""),
            "reason": result.get("reason", ""),
        }
    except json.JSONDecodeError:
        logger.exception("Failed to parse AI response as JSON")
        raise DevtoolsError("AI response was not valid JSON")
    except Exception:
        logger.exception("AI service call failed")
        raise DevtoolsError("AI service call failed")


def build_name_tree(names: list[str]) -> dict[str, Any]:
    tree: dict[str, Any] = {}
    for name in names:
        parts = name.split(".")
        node = tree
        for part in parts:
            if part not in node:
                node[part] = {}
            node = node[part]
        node["__leaf__"] = True
    return tree


def render_name_tree(tree: dict[str, Any], indent: int = 0) -> list[str]:
    lines: list[str] = []
    keys = sorted(k for k in tree if not k.startswith("__"))
    for key in keys:
        prefix = "  " * indent
        children = tree[key]
        non_leaf_children = {k: v for k, v in children.items() if not k.startswith("__")}
        if non_leaf_children:
            lines.append(f"{prefix}{key}")
            lines.extend(render_name_tree(children, indent + 1))
        else:
            lines.append(f"{prefix}{key}")
    return lines


def sample_name_tree(names: list[str], max_tokens: int = 600) -> str:
    if not names:
        return ""
    names = sorted(set(n for n in names if n and "." in n))
    if not names:
        return ""

    import re
    token_estimate = lambda s: max(1, len(s) // 3)

    tree = build_name_tree(names)
    full_lines = render_name_tree(tree)
    full_text = "\n".join(full_lines)

    if token_estimate(full_text) <= max_tokens:
        return full_text

    categories: dict[str, list[str]] = {}
    for name in names:
        cat = name.split(".")[0]
        categories.setdefault(cat, []).append(name)

    budget = max_tokens
    included_cats: list[str] = []
    cat_budget_per_line = 2
    total_cats = len(categories)
    cats_with_lines: dict[str, list[str]] = {}
    for cat in sorted(categories):
        cat_tree = build_name_tree(categories[cat])
        cat_lines = render_name_tree(cat_tree)
        cat_text = "\n".join(cat_lines)
        cost = token_estimate(cat_text)
        if cost <= budget // max(1, total_cats - len(included_cats) + 1):
            cats_with_lines[cat] = cat_lines
            included_cats.append(cat)
            budget -= cost

    result_lines: list[str] = []
    for cat in sorted(cats_with_lines):
        result_lines.extend(cats_with_lines[cat])

    result = "\n".join(result_lines)

    if not result:
        shallow: list[str] = []
        for name in names:
            parts = name.split(".")
            top = parts[0]
            second = parts[1] if len(parts) > 1 else "?"
            item = f"{top}.{second}.*" if len(parts) > 2 else f"{top}.{second}"
            if token_estimate("\n".join(shallow + [item])) <= max_tokens:
                shallow.append(item)
        result = "\n".join(shallow)

    return result


def _crop_region(image_bytes: bytes, rect: dict) -> bytes:
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise DevtoolsError("Failed to decode image for cropping")
    x1 = int(round(rect["x1"]))
    y1 = int(round(rect["y1"]))
    x2 = int(round(rect["x2"]))
    y2 = int(round(rect["y2"]))
    height, width = img.shape[:2]
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(width, x2)
    y2 = min(height, y2)
    if x2 <= x1 or y2 <= y1:
        raise DevtoolsError(f"Invalid crop rect: ({x1},{y1})-({x2},{y2})")
    cropped = img[y1:y2, x1:x2]
    success, encoded = cv2.imencode(".png", cropped)
    if not success:
        raise DevtoolsError("Failed to encode cropped region")
    return encoded.tobytes()


def infer_definitions(
    image_bytes: bytes,
    definitions: list[dict],
    folder_path: str,
    image_filename: str,
    ai_config: AiConfig,
    name_examples: str | None = None,
) -> dict[str, Any]:
    compressed_image = _compress_image_to_max_edge(image_bytes, 1024)
    b64_full = base64.b64encode(compressed_image).decode("utf-8")

    prompt = INFER_DEFINITIONS_PROMPT.format(
        folder_path=folder_path,
        image_filename=image_filename,
    )

    if name_examples:
        prompt += (
            "\n\nExisting naming references from this project "
            "(use these as style reference for the {{name}} field):\n"
            f"{name_examples}"
        )

    print(prompt)  # Debugging: print the prompt to verify its content

    content_parts: list[dict] = [
        {"type": "text", "text": prompt},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64_full}"},
        },
    ]

    def_id_by_index: dict[int, str] = {}
    for i, def_req in enumerate(definitions):
        def_id = def_req.get("defId") or def_req.get("definitionId", "")
        rect = def_req.get("templateRect") or def_req.get("template_rect")
        if rect:
            try:
                crop_bytes = _crop_region(image_bytes, rect)
                b64_crop = base64.b64encode(crop_bytes).decode("utf-8")
                content_parts.append({
                    "type": "text",
                    "text": f"Cropped region for definition [{def_id}]:",
                })
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64_crop}"},
                })
                def_id_by_index[len(def_id_by_index)] = def_id
            except DevtoolsError:
                logger.warning("Failed to crop region for def %s, skipping", def_id)

    provider_type = ai_config.provider_type
    model = ai_config.model
    api_key = ai_config.api_key
    endpoint = ai_config.endpoint

    litellm_params = {
        "model": f"{provider_type}/{model}",
        "messages": [
            {
                "role": "user",
                "content": content_parts,
            }
        ],
        "response_format": {"type": "json_object"},
        "stream": False,
    }

    if api_key:
        litellm_params["api_key"] = api_key
    if endpoint:
        litellm_params["api_base"] = endpoint

    # 懒加载 litellm：重依赖，仅在实际调用 AI 时导入（参见模块顶部注释）
    import litellm
    try:
        response = litellm.completion(**litellm_params)
        content = response.choices[0].message.content
        if not content:
            raise DevtoolsError("AI returned empty response")
        result: dict[str, Any] = json.loads(content)
        return result
    except json.JSONDecodeError:
        logger.exception("Failed to parse AI response as JSON")
        raise DevtoolsError("AI response was not valid JSON")
    except Exception:
        logger.exception("AI service call failed")
        raise DevtoolsError("AI service call failed")
