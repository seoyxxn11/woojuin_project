from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .base import ImageModelProvider


class GemmaProvider(ImageModelProvider):
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self._processor: Any = None
        self._model: Any = None

    @property
    def model_id(self) -> str:
        return str(self.config["model_id"])

    def load(self) -> None:
        try:
            import torch
            from transformers import (
                AutoModelForImageTextToText,
                AutoProcessor,
                BitsAndBytesConfig,
            )
        except ImportError as exc:
            raise RuntimeError(
                "로컬 모델 의존성이 없습니다. "
                "`pip install -r requirements.txt`를 먼저 실행하세요."
            ) from exc

        quantization = str(self.config.get("quantization", "none")).lower()
        device_map_config = self.config.get("device_map", "auto")
        if device_map_config == "gemma_12b_laptop":
            device_map: str | dict[str, str | int] = {
                "model.vision_tower": "cpu",
                "model.multi_modal_projector": 0,
                "model.language_model.embed_tokens": "cpu",
                "model.language_model.layers": 0,
                "model.language_model.norm": 0,
                "model.language_model.rotary_emb": 0,
                "model.language_model.rotary_emb_local": 0,
                "lm_head": "cpu",
            }
        else:
            device_map = str(device_map_config)

        model_kwargs: dict[str, Any] = {
            "device_map": device_map,
            "dtype": torch.bfloat16,
        }

        if quantization == "4bit":
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                llm_int8_enable_fp32_cpu_offload=bool(
                    self.config.get("cpu_offload", False)
                ),
            )
        elif quantization not in {"none", "bf16"}:
            raise ValueError("quantization은 4bit, bf16, none 중 하나여야 합니다.")

        self._processor = AutoProcessor.from_pretrained(
            self.model_id,
            use_fast=False,
        )
        self._model = AutoModelForImageTextToText.from_pretrained(
            self.model_id,
            **model_kwargs,
        )
        self._model.eval()

    def analyze(self, image_path: Path, prompt: str) -> tuple[str, dict[str, Any]]:
        if self._model is None or self._processor is None:
            raise RuntimeError("analyze() 전에 load()를 호출해야 합니다.")

        import torch
        from PIL import Image

        with Image.open(image_path) as opened_image:
            image = opened_image.convert("RGB")

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        started = time.perf_counter()
        inputs = self._processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        inputs = {
            key: value.to(self._model.device) if hasattr(value, "to") else value
            for key, value in inputs.items()
        }
        input_length = inputs["input_ids"].shape[-1]

        temperature = float(self.config.get("temperature", 0.0))
        generation_kwargs: dict[str, Any] = {
            "max_new_tokens": int(self.config.get("max_new_tokens", 512)),
            "do_sample": temperature > 0,
        }
        if temperature > 0:
            generation_kwargs["temperature"] = temperature

        with torch.inference_mode():
            generated = self._model.generate(**inputs, **generation_kwargs)

        generated_tokens = generated[0][input_length:]
        text = self._processor.decode(generated_tokens, skip_special_tokens=True).strip()
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)

        return text, {
            "latency_ms": elapsed_ms,
            "input_tokens": int(input_length),
            "output_tokens": int(generated_tokens.shape[-1]),
            "quantization": self.config.get("quantization", "none"),
            "cpu_offload": bool(self.config.get("cpu_offload", False)),
            "device_map": self.config.get("device_map", "auto"),
        }
