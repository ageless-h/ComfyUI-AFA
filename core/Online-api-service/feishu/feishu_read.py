import json
import time
import requests
import base64

# -------------------------------------------------------------------
# 飞书读取数据节点
# -------------------------------------------------------------------
class FeishuReadNode:
    @classmethod
    def IS_CHANGED(s, **kwargs): 
        return time.time()
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "feishu_config": ("STRING", {"forceInput": True}),
                "row": ("INT", {"default": 1, "min": 1, "max": 10000}),
                "column": ("INT", {"default": 1, "min": 1, "max": 1000}),
                "force_refresh": ("BOOLEAN", {"default": False}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("cell_data",)
    FUNCTION = "read_cell"
    CATEGORY = "AFA/飞书表格"
    
    def read_cell(self, feishu_config, row, column, force_refresh):
        """
        从飞书表格读取指定单元格的数据
        
        Args:
            feishu_config: 飞书配置字符串（JSON格式）
            row: 行号（从1开始）
            column: 列号（从1开始）
            force_refresh: 是否强制刷新
            
        Returns:
            单元格数据字符串
        """
        try:
            # 解析配置
            if feishu_config.startswith("Error:"):
                return (feishu_config,)
                
            config = json.loads(feishu_config)
            app_id = config.get("app_id")
            app_secret = config.get("app_secret")
            sheet_url = config.get("sheet_url")
            sheet_id = config.get("sheet_id")
            
            if not all([app_id, app_secret, sheet_url, sheet_id]):
                return ("Error: 飞书配置信息不完整",)
            
            # 获取访问令牌
            access_token = self._get_access_token(app_id, app_secret)
            if access_token.startswith("Error:"):
                return (access_token,)
            
            # 将行列号转换为A1格式
            cell_range = self._convert_to_a1_notation(row, column)
            
            # 构建API请求
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # 检测表格类型并使用对应的API端点
            if "base" in sheet_url:
                # 多维表格API
                api_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{sheet_id}/tables"
                print(f"[飞书读取] 使用多维表格API")
            else:
                # 飞书表格API - 需要从URL中提取spreadsheet_token
                spreadsheet_token = self._extract_spreadsheet_token(sheet_url, sheet_id)
                
                # 从URL中提取sheet名称
                sheet_name = self._extract_sheet_from_url(sheet_url, sheet_id)
                
                # 如果URL中没有sheet参数，通过API获取工作表列表
                if sheet_name is None:
                    sheet_name = self._get_sheet_list(access_token, spreadsheet_token)
                    if sheet_name is None:
                        return ("Error: 无法获取工作表信息，请检查表格权限或提供包含sheet参数的完整URL",)
                
                # 构建正确的v2 API URL格式：range参数在URL路径中
                range_param = f"{sheet_name}!{cell_range}"
                api_url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/{range_param}"
                print(f"[飞书读取] 使用飞书表格API v2，spreadsheet_token: {spreadsheet_token}, range: {range_param}")
            
            print(f"[飞书读取] 读取单元格 {cell_range} (行{row}, 列{column})")
            print(f"[飞书读取] API URL: {api_url}")
            
            response = requests.get(api_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                error_msg = f"Error: 飞书API请求失败 (状态码: {response.status_code})"
                print(f"[飞书读取] {error_msg}")
                return (error_msg,)
            
            result = response.json()
            print(f"[飞书读取] API完整响应: {result}")
            
            # 解析响应数据 - 根据飞书API文档修正响应格式
            if "data" in result:
                data = result["data"]
                # 检查不同的响应格式
                if "valueRange" in data and "values" in data["valueRange"]:
                    # 格式1: {"data": {"valueRange": {"values": [...]}}}
                    values = data["valueRange"]["values"]
                elif "values" in data:
                    # 格式2: {"data": {"values": [...]}}
                    values = data["values"]
                elif "valueRanges" in data and len(data["valueRanges"]) > 0:
                    # 格式3: {"data": {"valueRanges": [{"values": [...]}]}}
                    values = data["valueRanges"][0].get("values", [])
                else:
                    values = []
                
                if values and len(values) > 0 and len(values[0]) > 0:
                    cell_value = str(values[0][0])
                    print(f"[飞书读取] 成功读取数据: {cell_value}")
                    return (cell_value,)
                else:
                    print(f"[飞书读取] 单元格为空")
                    return ("",)
            else:
                error_msg = f"Error: 飞书API响应格式异常，实际响应: {result}"
                print(f"[飞书读取] {error_msg}")
                return (error_msg,)
                
        except json.JSONDecodeError:
            return ("Error: 飞书配置格式错误",)
        except Exception as e:
            error_msg = f"Error: 读取飞书数据失败: {str(e)}"
            print(f"[飞书读取] {error_msg}")
            return (error_msg,)
    
    def _get_access_token(self, app_id, app_secret):
        """获取飞书访问令牌"""
        try:
            url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            headers = {"Content-Type": "application/json"}
            data = {
                "app_id": app_id,
                "app_secret": app_secret
            }
            
            print(f"[飞书读取] 正在获取访问令牌，app_id: {app_id[:10]}...")
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code != 200:
                error_msg = f"Error: 获取访问令牌失败 (状态码: {response.status_code}), 响应: {response.text}"
                print(f"[飞书读取] {error_msg}")
                return error_msg
            
            result = response.json()
            print(f"[飞书读取] Token API响应: {result}")
            
            if result.get("code") == 0:
                token = result.get("tenant_access_token")
                print(f"[飞书读取] 访问令牌获取成功")
                return token
            else:
                error_msg = f"Error: 获取访问令牌失败: code={result.get('code')}, msg={result.get('msg', '未知错误')}"
                print(f"[飞书读取] {error_msg}")
                return error_msg
                
        except Exception as e:
            error_msg = f"Error: 获取访问令牌异常: {str(e)}"
            print(f"[飞书读取] {error_msg}")
            return error_msg
    
    def _convert_to_a1_notation(self, row, column):
        """将行列号转换为A1:A1格式（飞书API要求的范围格式）"""
        # 将列号转换为字母
        column_letter = ""
        while column > 0:
            column -= 1
            column_letter = chr(65 + column % 26) + column_letter
            column //= 26
        
        cell_ref = f"{column_letter}{row}"
        return f"{cell_ref}:{cell_ref}"  # 返回A1:A1格式
    
    def _extract_spreadsheet_token(self, sheet_url, sheet_id):
        """从飞书表格URL中提取spreadsheet_token"""
        if "sheets/" in sheet_url:
            # 从URL中提取：https://xxx.feishu.cn/sheets/shtxxxxx
            parts = sheet_url.split("sheets/")[1]
            spreadsheet_token = parts.split("?")[0].split("/")[0]
            return spreadsheet_token
        else:
            # 如果无法从URL提取，使用sheet_id作为fallback
            return sheet_id
    
    def _extract_sheet_from_url(self, url, sheet_id):
        """从URL中提取sheet参数，如果没有则通过API获取第一个工作表名称"""
        try:
            from urllib.parse import urlparse, parse_qs
            
            # 去除URL中的锚点
            url = url.split("#")[0]
            
            # 解析URL参数
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            
            # 检查是否有sheet参数
            if 'sheet' in query_params:
                sheet_param = query_params['sheet'][0]
                print(f"[飞书读取] 从URL中提取到sheet参数: {sheet_param}")
                return sheet_param
            else:
                # 当URL中没有sheet参数时，通过API获取第一个工作表名称
                print(f"[飞书读取] URL中没有sheet参数，尝试通过API获取工作表列表")
                return None  # 返回None表示需要通过API获取
        except Exception as e:
            print(f"[飞书读取] 解析URL时发生错误: {str(e)}")
            # 如果解析失败，返回None
            return None
    
    def _get_sheet_list(self, access_token, spreadsheet_token):
        """获取工作表列表 - 使用metainfo端点"""
        try:
            # 使用正确的metainfo端点
            url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/metainfo"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            print(f"[飞书读取] 正在获取工作表列表...")
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                error_msg = f"Error: 获取工作表列表失败 (状态码: {response.status_code})"
                print(f"[飞书读取] {error_msg}")
                return None
            
            result = response.json()
            
            if result.get("code") == 0 and "data" in result:
                sheets = result["data"].get("sheets", [])
                if sheets:
                    # 使用第一个工作表的sheetId作为sheet名称（符合飞书API要求）
                    first_sheet = sheets[0]
                    sheet_id = first_sheet.get("sheetId", "")
                    print(f"[飞书读取] 使用第一个工作表的sheetId: {sheet_id}")
                    return sheet_id
                else:
                    print(f"[飞书读取] 未找到任何工作表")
                    return None
            else:
                error_msg = f"Error: 获取工作表列表失败: code={result.get('code')}, msg={result.get('msg', '未知错误')}"
                print(f"[飞书读取] {error_msg}")
                return None
                
        except Exception as e:
            error_msg = f"Error: 获取工作表列表异常: {str(e)}"
            print(f"[飞书读取] {error_msg}")
            return None