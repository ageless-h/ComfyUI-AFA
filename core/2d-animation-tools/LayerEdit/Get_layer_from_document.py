class GetLayerFromDocumentNode:
    """从文档获取图层节点"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "文档": ("DOCUMENT",),
            },
            "optional": {
                "图层名称": ("STRING", {"default": ""}),
                "图层ID": ("INT", {"default": -1, "min": -1, "max": 999}),
            }
        }
    
    RETURN_TYPES = ("LAYER",)
    RETURN_NAMES = ("图层",)
    FUNCTION = "get_layer_from_document"
    CATEGORY = "AFA2D/图层编辑"
    
    def get_layer_from_document(self, **kwargs):
        """从文档中获取指定的图层"""
        # 参数映射
        document = kwargs.get("文档")
        layer_name = kwargs.get("图层名称", "")
        layer_id = kwargs.get("图层ID", -1)
        layers = document["layers"]
        
        # 如果指定了layer_id且有效，优先使用layer_id
        if layer_id >= 0:
            for layer in layers:
                if layer["layer_id"] == layer_id:
                    return (layer,)
        
        # 如果指定了layer_name，使用名称查找
        if layer_name:
            for layer in layers:
                if layer["name"] == layer_name:
                    return (layer,)
        
        # 如果都没有指定或找不到，返回第一个图层（如果存在）
        if layers:
            return (layers[0],)
        
        # 如果没有图层，返回空图层
        empty_layer = {
            "layer_id": -1,
            "name": "Empty Layer",
            "image_path": None,
            "mask_path": None,
            "position": [0, 0],
            "size": [0, 0],
            "anchor": [0.0, 0.0],
            "opacity": 1.0,
            "visible": True,
            "blend_mode": "normal",
            "metadata": {}
        }
        return (empty_layer,)