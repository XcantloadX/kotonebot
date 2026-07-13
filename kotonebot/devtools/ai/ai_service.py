import base64
import json
import logging

import cv2
import litellm
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
