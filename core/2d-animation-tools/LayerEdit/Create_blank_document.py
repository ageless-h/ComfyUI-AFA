import uuid
import torch
import numpy as np
from PIL import Image


class CreateBlankDocumentNode:
    """创建空白文档节点"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "宽度": ("INT", {"default": 1280, "min": 1, "max": 8192, "step": 1}),
                "高度": ("INT", {"default": 720, "min": 1, "max": 8192, "step": 1}),
            }
        }
    
    RETURN_TYPES = ("DOCUMENT",)
    RETURN_NAMES = ("文档",)
    FUNCTION = "create_blank_document"
    CATEGORY = "AFA2D/图层编辑"
    
    def create_blank_document(self, **kwargs):
        """创建一个空白文档对象"""
        # 参数映射
        width = kwargs.get("宽度")
        height = kwargs.get("高度")
        document = {
            "document_id": str(uuid.uuid4()),
            "version": "1.0",
            "canvas_size": [width, height],
            "layers": [],
            "metadata": {
                "description": "Blank document created by ComfyUI-AFA"
            }
        }
        return (document,)