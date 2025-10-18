import json
import time
import requests
import os

# -------------------------------------------------------------------
# 飞书数据配置节点
# -------------------------------------------------------------------
class FeishuConfigNode:
    @classmethod
    def IS_CHANGED(s, **kwargs): 
        return time.time()
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "sheet_url": ("STRING", {"default": "", "multiline": False}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("feishu_config",)
    FUNCTION = "create_config"
    CATEGORY = "AFA/飞书表格"
    
    def create_config(self, sheet_url):
        """
        创建飞书配置字符串
        
        Args:
            sheet_url: 表格URL
            
        Returns:
            配置字符串（JSON格式）
        """
        try:
            # 从配置文件读取app_id和app_secret
            app_id, app_secret = self._load_feishu_credentials()
            if not app_id or not app_secret:
                return ("Error: 请在config/feishu_config.json中配置app_id和app_secret",)
            
            # 验证必需参数
            if not sheet_url:
                return ("Error: sheet_url是必需的",)
            
            # 从URL自动提取spreadsheet_token和sheet_id
            spreadsheet_token = self._extract_spreadsheet_token(sheet_url.strip())
            sheet_id = self._extract_sheet_id_from_url(sheet_url.strip())
            
            # 如果URL中没有sheet参数，尝试通过API获取第一个工作表的ID
            if not sheet_id:
                sheet_id = self._get_first_sheet_id(app_id.strip(), app_secret.strip(), spreadsheet_token)
                if not sheet_id:
                    sheet_id = spreadsheet_token  # 如果都获取失败，使用spreadsheet_token作为fallback
            
            # 创建配置字典
            config = {
                "app_id": app_id.strip(),
                "app_secret": app_secret.strip(),
                "sheet_url": sheet_url.strip(),
                "sheet_id": sheet_id,  # 真正的工作表ID
                "spreadsheet_token": spreadsheet_token,  # 表格token
                "created_at": time.time()
            }
            
            # 转换为JSON字符串
            config_str = json.dumps(config, ensure_ascii=False)
            
            print(f"[飞书配置] 配置创建成功，从URL自动提取的表格ID: {spreadsheet_token}")
            
            return (config_str,)
            
        except Exception as e:
            error_msg = f"Error: 创建飞书配置失败: {str(e)}"
            print(f"[飞书配置] {error_msg}")
            return (error_msg,)
    
    def _load_feishu_credentials(self):
        """从配置文件加载飞书凭据"""
        try:
            # 获取配置文件路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, "..", "..", "..", "config", "feishu_config.json")
            config_path = os.path.normpath(config_path)
            
            if not os.path.exists(config_path):
                print(f"[飞书配置] 配置文件不存在: {config_path}")
                return None, None
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            feishu_config = config.get("feishu", {})
            app_id = feishu_config.get("app_id", "").strip()
            app_secret = feishu_config.get("app_secret", "").strip()
            
            if not app_id or not app_secret:
                print("[飞书配置] 配置文件中的app_id或app_secret为空")
                return None, None
            
            print("[飞书配置] 成功从配置文件加载飞书凭据")
            return app_id, app_secret
            
        except Exception as e:
            print(f"[飞书配置] 加载配置文件失败: {str(e)}")
            return None, None
    
    def _extract_spreadsheet_token(self, sheet_url):
        """从飞书表格URL中提取spreadsheet_token"""
        try:
            # 从URL中提取spreadsheet_token
            # URL格式: https://xxx.feishu.cn/sheets/{spreadsheet_token}?sheet={sheet_id}
            if "/sheets/" in sheet_url:
                parts = sheet_url.split("/sheets/")[1]
                spreadsheet_token = parts.split("?")[0]
                print(f"[飞书配置] 从URL自动提取的表格token: {spreadsheet_token}")
                return spreadsheet_token
            else:
                print("[飞书配置] 无法从URL中提取表格token")
                return None
        except Exception as e:
            print(f"[飞书配置] 提取表格token时出错: {str(e)}")
            return None
    
    def _extract_sheet_id_from_url(self, sheet_url):
        """从飞书表格URL中提取sheet_id"""
        try:
            # 从URL中提取sheet_id
            # URL格式: https://xxx.feishu.cn/sheets/{spreadsheet_token}?sheet={sheet_id}
            if "?sheet=" in sheet_url:
                sheet_id = sheet_url.split("?sheet=")[1].split("&")[0]
                print(f"[飞书配置] 从URL自动提取的工作表ID: {sheet_id}")
                return sheet_id
            else:
                print("[飞书配置] URL中没有sheet参数，将尝试获取第一个工作表")
                return None
        except Exception as e:
            print(f"[飞书配置] 提取工作表ID时出错: {str(e)}")
            return None
    
    def _get_access_token(self, app_id, app_secret):
        """获取飞书访问令牌"""
        try:
            url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            headers = {"Content-Type": "application/json; charset=utf-8"}
            data = {
                "app_id": app_id,
                "app_secret": app_secret
            }
            
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    return result.get("tenant_access_token")
            return None
        except Exception as e:
            print(f"[飞书配置] 获取访问令牌失败: {str(e)}")
            return None
    
    def _get_first_sheet_id(self, app_id, app_secret, spreadsheet_token):
        """获取第一个工作表的ID"""
        try:
            # 获取访问令牌
            access_token = self._get_access_token(app_id, app_secret)
            if not access_token:
                print("[飞书配置] 无法获取访问令牌，使用默认sheet_id")
                return None
            
            # 获取表格信息
            url = f"https://open.feishu.cn/open-apis/sheets/v1/spreadsheets/{spreadsheet_token}/sheets/query"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    sheets = result.get("data", {}).get("sheets", [])
                    if sheets:
                        first_sheet_id = sheets[0].get("sheet_id")
                        print(f"[飞书配置] 自动获取的工作表ID: {first_sheet_id}")
                        return first_sheet_id
            
            print("[飞书配置] 无法获取工作表信息，使用默认sheet_id")
            return None
        except Exception as e:
            print(f"[飞书配置] 获取工作表ID失败: {str(e)}")
            return None