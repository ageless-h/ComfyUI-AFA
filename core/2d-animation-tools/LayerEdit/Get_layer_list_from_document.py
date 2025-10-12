class GetLayerListFromDocumentNode:
    """从文档获取图层列表节点"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "文档": ("DOCUMENT",),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("图层列表",)
    FUNCTION = "get_layer_list_from_document"
    CATEGORY = "AFA2D/图层编辑"
    
    def get_layer_list_from_document(self, **kwargs):
        """从文档中获取所有图层的列表"""
        # 参数映射
        document = kwargs.get("文档")
        layers = document["layers"]
        return (layers,)