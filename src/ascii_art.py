"""
宝可梦终端精灵图展示模块
使用 term-image 将 PokeAPI 精灵图直接在终端中渲染展示
"""
from __future__ import annotations

import logging
import os
import sys
import ssl
import urllib.error
import urllib.request
from typing import Optional

try:
    from PIL import Image as PILImage
    from term_image.image import auto_image_class
    _HAS_TERM_IMAGE = True
except ImportError:
    _HAS_TERM_IMAGE = False

try:
    from rich.console import Console
except ImportError:
    Console = None  # type: ignore[assignment]

_logger = logging.getLogger(__name__)

# 图片缓存目录
_SPRITE_CACHE_DIR: str = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".sprite_cache",
)

# 内存缓存：name_en -> 缓存文件路径
_cache: dict[str, str] = {}

# PokeAPI 精灵图 URL 模板
_SPRITE_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/"
    "PokeAPI/sprites/master/sprites/pokemon/{pokemon_id}.png"
)


# ══════════════════════════════════════════════
#  图片下载
# ══════════════════════════════════════════════

def _download_sprite(pokemon_id: int) -> Optional[str]:
    """从 PokeAPI 下载精灵图，返回本地缓存路径

    优先从本地缓存读取，否则从 GitHub 下载并缓存
    """
    os.makedirs(_SPRITE_CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(_SPRITE_CACHE_DIR, f"{pokemon_id}.png")

    # 检查缓存
    if os.path.exists(cache_path):
        return cache_path

    # 下载
    url = _SPRITE_URL_TEMPLATE.format(pokemon_id=pokemon_id)
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={"User-Agent": "pokemonle-tui/1.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = resp.read()
    except (urllib.error.URLError, OSError, ValueError):
        return None

    # 缓存
    try:
        with open(cache_path, "wb") as f:
            f.write(data)
    except (IOError, OSError):
        return None

    return cache_path


# ══════════════════════════════════════════════
#  公开接口
# ══════════════════════════════════════════════

def get_sprite_path(name_en: str, pokemon_id: int = 0) -> Optional[str]:
    """根据宝可梦英文名获取精灵图缓存路径

    优先查找已有缓存文件，若无则从 PokeAPI 下载。

    Args:
        name_en: 宝可梦英文名（如 "Pikachu", "Charizard"）
        pokemon_id: PokeAPI 编号（用于下载精灵图）

    Returns:
        缓存 PNG 文件的路径，或 None
    """
    if name_en in _cache:
        cached = _cache[name_en]
        if os.path.exists(cached):
            return cached

    # 1) 尝试已有缓存文件（按编号）
    if pokemon_id > 0:
        sprite_path = os.path.join(_SPRITE_CACHE_DIR, f"{pokemon_id}.png")
        if os.path.exists(sprite_path):
            _cache[name_en] = sprite_path
            return sprite_path

    # 2) 自动下载
    if pokemon_id > 0 and _HAS_TERM_IMAGE:
        sprite_path = _download_sprite(pokemon_id)
        if sprite_path:
            _cache[name_en] = sprite_path
            return sprite_path

    return None


def show_sprite(name_en: str, pokemon_id: int = 0, max_width: int = 40,
                crop_ratio: float = 0.05, h_align: str = "left",
                v_align: Optional[str] = None, console=None) -> bool:
    """在终端中直接渲染展示宝可梦精灵图

    展示前会对图片进行裁剪，去掉四周空白区域。

    Args:
        name_en: 宝可梦英文名
        pokemon_id: PokeAPI 编号
        max_width: 最大渲染宽度（字符数）
        crop_ratio: 四边裁剪比例，默认 0.05 即各裁 5%
        h_align: 水平对齐，默认 "left"（居左）
        v_align: 垂直对齐，默认 None（当前位置显示）
        console: Rich Console 实例，用于换行（避免新建实例导致输出流不一致）

    Returns:
        是否成功展示
    """
    if not _HAS_TERM_IMAGE:
        _logger.warning("term-image 未安装，无法渲染精灵图")
        return False

    sprite_path = get_sprite_path(name_en, pokemon_id)
    if not sprite_path:
        _logger.warning("未找到精灵图: %s (#%d)", name_en, pokemon_id)
        return False

    try:
        pil_img = PILImage.open(sprite_path)
        w, h = pil_img.size
        left = int(w * crop_ratio)
        top = int(h * crop_ratio)
        right = w - left
        bottom = h - top
        cropped = pil_img.crop((left, top, right, bottom))

        term_img = auto_image_class()(cropped, width=max_width)
        # Avoid filling the whole terminal with blank padding.
        # Use a small pad_height and top alignment so the image renders at the current cursor
        # position instead of clearing the screen and leaving a large blank gap.
        term_img.draw(
            h_align=h_align,
            v_align=v_align or "top",
            pad_height=1,
            scroll=True,
        )
        if console is not None:
            console.print()
        elif Console is not None:
            Console().print()
        else:
            sys.stdout.write("\n")
        return True
    except Exception:
        return False
