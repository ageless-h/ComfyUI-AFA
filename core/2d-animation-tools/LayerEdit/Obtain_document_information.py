class ObtainDocumentInformationNode:
    """获取文档信息节点"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "文档": ("DOCUMENT",),
            }
        }
    
    RETURN_TYPES = ("INT", "INT", "INT", "STRING", "STRING")
    RETURN_NAMES = ("宽度", "高度", "图层数量", "文档ID", "元数据")
    FUNCTION = "obtain_document_information"
    CATEGORY = "AFA2D/图层编辑"
    
    def obtain_document_information(self, **kwargs):
        """获取文档的基本信息"""
        # 参数映射
        document = kwargs.get("文档")
        width, height = document["canvas_size"]
        layer_count = len(document["layers"])
        document_id = document["document_id"]
        metadata = str(document.get("metadata", {}))
        
        return (width, height, layer_count, document_id, metadata)