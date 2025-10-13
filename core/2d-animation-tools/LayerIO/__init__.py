"""
LayerIO模块 - 图层输入输出功能
包含PSD文件的导入和导出功能
"""

from .import_psd import ImportPSDNode
from .export_psd import ExportPSDAdvancedNode

# 导出的节点类
NODE_CLASS_MAPPINGS = {
    "ImportPSDNode": ImportPSDNode,
    "ExportPSDAdvancedNode": ExportPSDAdvancedNode,
}

# 节点显示名称
NODE_DISPLAY_NAME_MAPPINGS = {
    "ImportPSDNode": "导入PSD文档",
    "ExportPSDAdvancedNode": "高级PSD导出",
}

__all__ = [
    "ImportPSDNode",
    "ExportPSDAdvancedNode",
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS"
]