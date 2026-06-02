"""Sprite loading and variant caching for the Aura window."""

from __future__ import annotations

from pathlib import Path


class SpriteStore:
    """Load and cache sprite assets for Tk canvas drawing."""

    def __init__(self, asset_dir: Path, tk):
        self.asset_dir = Path(asset_dir)
        self._tk = tk
        self._sprite_images: dict[str, object] = {}
        self._sprite_variants: dict[tuple[str, int], object] = {}

    def load(self):
        self._sprite_images = {}
        self._sprite_variants = {}
        for sprite_path in sorted(self.asset_dir.glob("*.png")):
            if not sprite_path.exists():
                continue
            try:
                image = self._tk.PhotoImage(file=str(sprite_path))
                self._sprite_images[sprite_path.name] = image
            except Exception:
                continue

    def clear(self):
        self._sprite_images = {}
        self._sprite_variants = {}

    def get(self, sprite_name: str, size: int, crop_box: tuple[int, int, int, int] | None = None):
        cached = self._sprite_variants.get((sprite_name, size))
        if cached is not None:
            return cached

        source = self._sprite_images.get(sprite_name)
        if source is None:
            return None

        image = source
        if crop_box is not None:
            cropped = self._tk.PhotoImage()
            cropped.tk.call(cropped, "copy", source, "-from", *crop_box)
            image = cropped

        max_dimension = max(image.width(), image.height())
        scale = max(1, int(-(-max_dimension // size)))
        if scale > 1:
            image = image.subsample(scale, scale)

        self._sprite_variants[(sprite_name, size)] = image
        return image
