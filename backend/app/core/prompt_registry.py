"""
Prompt 版本管理与统一注册

方案 A: 建立 Prompt 版本管理，支持灰度、回滚、可测试。
- 支持 .md 文件 frontmatter 指定 version
- list_versions(name) 列出可回滚版本
- get_prompt_hash(name, version) 用于回归测试
"""
import hashlib
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_PROMPTS: Dict[str, Dict] = {}


def _parse_frontmatter(content: str) -> tuple[str, str]:
    """解析 frontmatter，返回 (body, version)"""
    version = "v1"
    body = content
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
    if match:
        fm, body = match.group(1), match.group(2)
        for line in fm.split("\n"):
            if line.strip().startswith("version:"):
                version = line.split(":", 1)[1].strip().strip('"\'')
                break
    return body.strip(), version


def register_prompt(
    name: str,
    template: str,
    version: str = "v1",
    description: str = "",
) -> None:
    """注册 Prompt 模板"""
    key = f"{name}@{version}"
    _PROMPTS[key] = {
        "name": name,
        "version": version,
        "template": template,
        "description": description,
        "hash": hashlib.sha256(template.encode()).hexdigest()[:16],
    }
    logger.debug("Registered prompt: %s", key)


def get_prompt(name: str, version: Optional[str] = None, **kwargs) -> str:
    """获取 Prompt，支持变量替换。version=None 时取最新版本"""
    if version:
        key = f"{name}@{version}"
    else:
        keys = [k for k in _PROMPTS if k.startswith(f"{name}@")]
        key = keys[-1] if keys else None
    if not key or key not in _PROMPTS:
        return ""
    tpl = _PROMPTS[key]["template"]
    try:
        return tpl.format(**kwargs)
    except KeyError:
        return tpl


def get_prompt_hash(name: str, version: Optional[str] = None) -> str:
    """获取 Prompt 内容哈希，用于回归测试"""
    if version:
        key = f"{name}@{version}"
    else:
        keys = [k for k in _PROMPTS if k.startswith(f"{name}@")]
        key = keys[-1] if keys else None
    if not key or key not in _PROMPTS:
        return ""
    return _PROMPTS[key]["hash"]


def list_versions(name: str) -> List[str]:
    """列出某 Prompt 的所有版本（用于回滚）"""
    return sorted(
        [k.split("@", 1)[1] for k in _PROMPTS if k.startswith(f"{name}@")],
        reverse=True,
    )


def list_prompts() -> Dict[str, Dict]:
    """列出所有已注册 Prompt"""
    return dict(_PROMPTS)


def load_prompts_from_dir(dir_path: str) -> int:
    """从目录加载 .md 文件为 Prompt，支持 frontmatter 指定 version"""
    base = Path(dir_path)
    if not base.exists():
        return 0
    count = 0
    for f in base.glob("*.md"):
        name = f.stem
        content = f.read_text(encoding="utf-8")
        body, version = _parse_frontmatter(content)
        register_prompt(
            name,
            body,
            version=version,
            description=f"From {f.name}",
        )
        count += 1
    return count
