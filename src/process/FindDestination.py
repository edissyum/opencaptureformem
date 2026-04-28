# This file is part of Open-Capture For MEM Courrier.

# Open-Capture is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Open-Capture For MEM Courrier is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Open-Capture For MEM Courrier.  If not, see <https://www.gnu.org/licenses/>.

# @dev: Serena tetart <serena.tetart@edissyum.com>

import io
import os
import pickle
import requests
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Union

from PIL import Image

import torch
import torch.nn as nn
import torch.nn.functional as F
from contextlib import nullcontext

from transformers import AutoImageProcessor, AutoModel

from .AuthJWT import (
    build_jwt_headers,
    clear_jwt_cache,
    get_ca_crt_path,
    get_runtime_files_state,
)

# =========================
# Architecture modèle
# =========================
class ResidualMLP(nn.Module):
    def __init__(self, dim: int, hidden_dim: int, dropout: float = 0.2):
        super().__init__()
        self.net = nn.Sequential(
            nn.LayerNorm(dim),
            nn.Linear(dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, dim),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.net(x)


class CosineHead(nn.Module):
    def __init__(self, in_dim: int, n_classes: int, scale: float = 30.0):
        super().__init__()
        self.W = nn.Parameter(torch.randn(n_classes, in_dim))
        self.scale = nn.Parameter(torch.tensor(scale, dtype=torch.float32))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = F.normalize(x, dim=-1)
        W = F.normalize(self.W, dim=-1)
        return self.scale * (x @ W.t())


class MultiTaskMLP(nn.Module):
    def __init__(
        self,
        in_dim: int,
        hidden_dims: List[int],
        n_dest: int,
        n_type: int,
        dropout: float = 0.3,
    ):
        super().__init__()

        self.in_norm = nn.LayerNorm(in_dim)
        self.in_drop = nn.Dropout(dropout)

        blocks = []
        for h in hidden_dims:
            blocks.append(ResidualMLP(in_dim, h, dropout=dropout))
        self.trunk = nn.Sequential(*blocks) if blocks else nn.Identity()

        self.dest_head = CosineHead(in_dim, n_dest)
        self.type_head = CosineHead(in_dim, n_type)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        x = self.in_norm(x)
        x = self.in_drop(x)
        h = self.trunk(x)
        return self.dest_head(h), self.type_head(h)


# =========================
# Config / cache
# =========================
@dataclass(frozen=True)
class InferenceConfig:
    model_name: str = "DINOv3_L"
    local_files_only: bool = True
    processor_shortest_edge: int = 672
    processor_center_crop: bool = False
    use_cls_token: bool = True
    hidden_dims: Tuple[int, ...] = (1024, 512)
    dropout: float = 0.3
    threshold: float = 0.6
    fallback_class_idx: int = 6
    amp: bool = True
    use_fast_processor: bool = True


class LoadedModel:
    def __init__(
        self,
        config: InferenceConfig,
        device: torch.device,
        processor,
        crop_size: Dict[str, int],
        backbone: nn.Module,
        mlp: nn.Module,
        dest_idx_to_label: Dict[int, str],
        type_idx_to_label: Dict[int, str],
        doctype_id_to_text: Dict[str, str] = None,
    ):
        self.config = config
        self.device = device
        self.processor = processor
        self.crop_size = crop_size
        self.backbone = backbone
        self.mlp = mlp
        self.dest_idx_to_label = dest_idx_to_label
        self.type_idx_to_label = type_idx_to_label
        self.doctype_id_to_text = doctype_id_to_text or {}


_MODEL_CACHE: Dict[str, LoadedModel] = {}
_MODEL_CACHE_LOCK = threading.Lock()


# =========================
# Utilitaires
# =========================
def _normalize_hidden_dims(value: Any, default: Tuple[int, ...]) -> List[int]:
    if value is None:
        return list(default)
    if isinstance(value, (list, tuple)):
        return [int(v) for v in value]
    return list(default)


def _invert_mapping(mapping: Dict[str, int]) -> Dict[int, str]:
    return {int(v): str(k) for k, v in mapping.items()}


def _ensure_pil_image(image: Union[Image.Image, bytes, bytearray]) -> Image.Image:
    if isinstance(image, Image.Image):
        return image.convert("RGB")

    if isinstance(image, (bytes, bytearray)):
        with Image.open(io.BytesIO(image)) as im:
            return im.convert("RGB").copy()

    raise TypeError("image must be a PIL.Image.Image, bytes or bytearray")


def _configure_processor(processor, shortest_edge: int, center_crop: bool):
    crop_size = {"height": shortest_edge, "width": shortest_edge}

    processor.do_resize = True
    processor.do_center_crop = bool(center_crop)
    processor.crop_size = crop_size

    try:
        processor.size = {"shortest_edge": shortest_edge}
    except Exception:
        processor.size = crop_size

    return processor, crop_size


def _pad_pixel_values(pixel_values_list: List[torch.Tensor], pad_value: float = 0.0) -> torch.Tensor:
    max_h = max(p.shape[1] for p in pixel_values_list)
    max_w = max(p.shape[2] for p in pixel_values_list)

    padded = []
    for p in pixel_values_list:
        _, h, w = p.shape
        p = F.pad(p, (0, max_w - w, 0, max_h - h), value=pad_value)
        padded.append(p)

    return torch.stack(padded, dim=0)


def _sync_if_cuda(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize()


def load_checkpoint(path: str, model: nn.Module, device: torch.device) -> Dict[str, Any]:
    ckpt = torch.load(path, map_location=device)
    state_dict = ckpt["state_dict"] if isinstance(ckpt, dict) and "state_dict" in ckpt else ckpt
    model.load_state_dict(state_dict)
    return ckpt if isinstance(ckpt, dict) else {"state_dict": state_dict}


@torch.no_grad()
def infer_embedding_dim(dino_model, processor, device, shortest_edge: int) -> int:
    img = Image.new("RGB", (shortest_edge, shortest_edge), (255, 255, 255))
    inputs = processor(
        images=img,
        return_tensors="pt",
        do_center_crop=False,
        crop_size={"height": shortest_edge, "width": shortest_edge},
    )
    inputs = {k: v.to(device) for k, v in inputs.items()}
    out = dino_model(**inputs)
    return int(out.last_hidden_state.shape[-1])


def _build_config_from_checkpoint_and_defaults(
    ckpt: Dict[str, Any],
    defaults: InferenceConfig,
) -> InferenceConfig:
    cfg = ckpt.get("config", {}) if isinstance(ckpt, dict) else {}

    return InferenceConfig(
        model_name=str(cfg.get("model_name", defaults.model_name)),
        local_files_only=bool(cfg.get("local_files_only", defaults.local_files_only)),
        processor_shortest_edge=int(cfg.get("processor_shortest_edge", defaults.processor_shortest_edge)),
        processor_center_crop=bool(cfg.get("processor_center_crop", defaults.processor_center_crop)),
        use_cls_token=bool(cfg.get("use_cls_token", defaults.use_cls_token)),
        hidden_dims=tuple(_normalize_hidden_dims(cfg.get("hidden_dims"), defaults.hidden_dims)),
        dropout=float(cfg.get("dropout", defaults.dropout)),
        threshold=float(cfg.get("threshold", defaults.threshold)),
        fallback_class_idx=int(cfg.get("fallback_class_idx", defaults.fallback_class_idx)),
        amp=bool(cfg.get("amp", defaults.amp)),
        use_fast_processor=bool(cfg.get("use_fast_processor", defaults.use_fast_processor)),
    )


def _resolve_model_name(model_path: str, config: InferenceConfig) -> str:
    if os.path.isdir(model_path):
        return model_path
    return config.model_name


@torch.no_grad()
def _extract_embedding(
    image: Image.Image,
    processor,
    crop_size: Dict[str, int],
    backbone,
    device: torch.device,
    use_cls_token: bool = True,
    amp: bool = True,
) -> torch.Tensor:
    out = processor(
        images=image,
        return_tensors="pt",
        do_center_crop=False,
        crop_size=crop_size,
    )

    pixel_values = out["pixel_values"]
    if pixel_values.ndim == 4:
        pixel_values = pixel_values.squeeze(0)

    pixel_values = _pad_pixel_values([pixel_values]).to(device=device, dtype=torch.float32)

    if device.type == "cuda" and amp:
        amp_ctx = torch.autocast("cuda", dtype=torch.float32)
    else:
        amp_ctx = nullcontext()

    backbone.eval()
    with torch.inference_mode(), amp_ctx:
        out = backbone(pixel_values=pixel_values)
        hs = out.last_hidden_state
        emb = hs[:, 0, :] if use_cls_token else hs.mean(dim=1)

    return emb.to(torch.float32)


@torch.no_grad()
def _predict_logits(image: Image.Image, loaded: LoadedModel) -> Tuple[torch.Tensor, torch.Tensor]:
    emb = _extract_embedding(
        image=image,
        processor=loaded.processor,
        crop_size=loaded.crop_size,
        backbone=loaded.backbone,
        device=loaded.device,
        use_cls_token=loaded.config.use_cls_token,
        amp=loaded.config.amp,
    ).to(loaded.device)

    logits_dest, logits_type = loaded.mlp(emb)
    return logits_dest, logits_type


def _decode_with_threshold(
    pred_idx: int,
    confidence: float,
    idx_to_label: Dict[int, str],
    threshold: float,
    fallback_class_idx: int,
) -> str:
    if confidence < threshold and fallback_class_idx in idx_to_label:
        pred_idx = fallback_class_idx

    if pred_idx not in idx_to_label:
        if fallback_class_idx in idx_to_label:
            return idx_to_label[fallback_class_idx]
        raise KeyError(f"class index {pred_idx} not found in mapping")

    return str(idx_to_label[pred_idx])


def _load_model(model_path: str) -> LoadedModel:
    cache_key = os.path.abspath(model_path)

    with _MODEL_CACHE_LOCK:
        if cache_key in _MODEL_CACHE:
            return _MODEL_CACHE[cache_key]

    best_path = os.path.join(model_path, "best_mlp.pth")
    dest_map_path = os.path.join(model_path, "dest_mapping.pkl")
    type_map_path = os.path.join(model_path, "type_mapping.pkl")
    doctype_text_map_path = os.path.join(model_path, "doctype_id_to_text.pkl")

    if not os.path.isfile(best_path):
        raise FileNotFoundError(f"checkpoint not found: {best_path}")
    if not os.path.isfile(dest_map_path):
        raise FileNotFoundError(f"destination mapping not found: {dest_map_path}")
    if not os.path.isfile(type_map_path):
        raise FileNotFoundError(f"type mapping not found: {type_map_path}")

    with open(dest_map_path, "rb") as f:
        dest_map = pickle.load(f)
    with open(type_map_path, "rb") as f:
        type_map = pickle.load(f)

    doctype_id_to_text = {}
    if os.path.isfile(doctype_text_map_path):
        with open(doctype_text_map_path, "rb") as f:
            loaded_doctype_text_map = pickle.load(f)
        if isinstance(loaded_doctype_text_map, dict):
            doctype_id_to_text = {
                str(k): str(v) for k, v in loaded_doctype_text_map.items()
            }

    if not isinstance(dest_map, dict) or not dest_map:
        raise ValueError("dest_mapping.pkl must contain a non-empty dict[str, int]")
    if not isinstance(type_map, dict) or not type_map:
        raise ValueError("type_mapping.pkl must contain a non-empty dict[str, int]")

    dest_idx_to_label = _invert_mapping(dest_map)
    type_idx_to_label = _invert_mapping(type_map)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(best_path, map_location="cpu")
    config = _build_config_from_checkpoint_and_defaults(ckpt, InferenceConfig())

    model_name_or_path = _resolve_model_name(model_path, config)

    processor = AutoImageProcessor.from_pretrained(
        model_name_or_path,
        local_files_only=config.local_files_only,
        use_fast=config.use_fast_processor,
    )
    processor, crop_size = _configure_processor(
        processor=processor,
        shortest_edge=config.processor_shortest_edge,
        center_crop=config.processor_center_crop,
    )

    backbone = AutoModel.from_pretrained(
        model_name_or_path,
        local_files_only=config.local_files_only,
        torch_dtype=torch.float32,
    ).to(device)
    backbone.eval()
    for p in backbone.parameters():
        p.requires_grad_(False)

    emb_dim = ckpt.get("config", {}).get("emb_dim")
    if emb_dim is None:
        emb_dim = infer_embedding_dim(backbone, processor, device, config.processor_shortest_edge)

    mlp = MultiTaskMLP(
        in_dim=int(emb_dim),
        hidden_dims=list(config.hidden_dims),
        n_dest=len(dest_map),
        n_type=len(type_map),
        dropout=config.dropout,
    ).to(device)

    load_checkpoint(best_path, mlp, device)
    mlp.eval()

    loaded = LoadedModel(
        config=config,
        device=device,
        processor=processor,
        crop_size=crop_size,
        backbone=backbone,
        mlp=mlp,
        dest_idx_to_label=dest_idx_to_label,
        type_idx_to_label=type_idx_to_label,
        doctype_id_to_text=doctype_id_to_text,
    )

    with _MODEL_CACHE_LOCK:
        _MODEL_CACHE[cache_key] = loaded

    return loaded

def _decode_doctype_text(doctype_id: str, doctype_id_to_text: Dict[str, str]) -> str:
    if not isinstance(doctype_id_to_text, dict) or not doctype_id_to_text:
        return doctype_id
    return str(doctype_id_to_text.get(doctype_id, doctype_id))

# =========================
# Inférence
# =========================
def run_inference_destination(
    model_path: str,
    image
):
    pil_image = _ensure_pil_image(image)
    loaded = _load_model(model_path)

    _sync_if_cuda(loaded.device)
    logits_dest, logits_type = _predict_logits(pil_image, loaded)

    probs_dest = torch.softmax(logits_dest, dim=-1)
    probs_type = torch.softmax(logits_type, dim=-1)

    conf_dest, pred_dest = probs_dest.max(dim=-1)
    conf_type, pred_type = probs_type.max(dim=-1)
    _sync_if_cuda(loaded.device)

    destination = _decode_with_threshold(
        pred_idx=int(pred_dest.item()),
        confidence=float(conf_dest.item()),
        idx_to_label=loaded.dest_idx_to_label,
        threshold=loaded.config.threshold,
        fallback_class_idx=loaded.config.fallback_class_idx,
    )

    doctype_id = _decode_with_threshold(
        pred_idx=int(pred_type.item()),
        confidence=float(conf_type.item()),
        idx_to_label=loaded.type_idx_to_label,
        threshold=loaded.config.threshold,
        fallback_class_idx=loaded.config.fallback_class_idx,
    )

    doctype = _decode_doctype_text(
        doctype_id=doctype_id,
        doctype_id_to_text=loaded.doctype_id_to_text,
    )

    return {
        "destination": destination,
        "doctype": doctype,
    }

def run_inference_destination_remote(config, image):
    timeout = int(config.get("_remote_timeout", 300))

    with open(image.filename, "rb") as img_file:
        img_data = img_file.read()

    url = config.get("doctype_remote_url")
    if not url:
        return False, "Remote destination inference not configured"
        
    if config.get('doctype_remote_password') and config.get('doctype_remote_token'):
        # OLD login method using password/API-KEY
        try:
            auth = requests.auth.HTTPBasicAuth(config.get('doctype_remote_login'), config.get('doctype_remote_password'))
            response = requests.post(
                url,
                auth=auth,
                headers={
                    "X-Api-Key": config.get('doctype_remote_token'),
                    "Content-Type": "image/jpeg",
                    "Accept": "application/json",
                },
                data=img_data,
                timeout=timeout,
            )
        except (Exception, ) as e:
            return False, str(e)
            
        if response.status_code == 200:
            data = response.json()
            return True, data
        else:
            return False, response.text
    else:
        # HTTPS login method
        files_ok, files_error = get_runtime_files_state(config, "doctype")
        if not files_ok:
            return False, files_error

        ca_cert = get_ca_crt_path(config, "doctype")

        try:
            headers = build_jwt_headers(config, "doctype", content_type="image/jpeg")

            response = requests.post(
                url,
                headers=headers,
                data=img_data,
                timeout=timeout,
                verify=ca_cert,
            )

            if response.status_code == 401:
                clear_jwt_cache(config, "doctype"
                )
                headers = build_jwt_headers(config, "doctype", content_type="image/jpeg", force_refresh=True)
                response = requests.post(
                    url,
                    headers=headers,
                    data=img_data,
                    timeout=timeout,
                    verify=ca_cert,
                )

        except Exception as e:
            return False, str(e)

        if response.status_code == 200:
            try:
                return True, response.json()
            except Exception:
                return False, "Réponse JSON invalide du serveur distant"

    return False, response.text
