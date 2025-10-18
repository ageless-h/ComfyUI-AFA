import json
import time
import requests

# -------------------------------------------------------------------
# 飞书写入数据节点
# -------------------------------------------------------------------
class FeishuWriteNode:
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
                "data": ("STRING", {"default": "", "multiline": True}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("write_result",)
    FUNCTION = "write_cell"
    CATEGORY = "AFA/飞书表格"
    
    def write_cell(self, feishu_config, row, column, data):
        """
        向飞书表格写入数据到指定单元格
        
        Args:
            feishu_config: 飞书配置字符串（JSON格式）
            row: 行号（从1开始）
            column: 列号（从1开始）
            data: 要写入的数据
            
        Returns:
            写入操作结果字符串
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
                # 多维表格API (暂不支持)
                return ("Error: 多维表格写入功能暂未实现",)
            else:
                # 飞书表格API
                spreadsheet_token = self._extract_spreadsheet_token(sheet_url, sheet_id)
                
                # 从URL中提取sheet名称
                sheet_name = self._extract_sheet_from_url(sheet_url, sheet_id)
                
                # 如果URL中没有sheet参数，通过API获取工作表列表
                if sheet_name is None:
                    sheet_name = self._get_sheet_list(access_token, spreadsheet_token)
                    if sheet_name is None:
                        return ("Error: 无法获取工作表信息，请检查表格权限或提供包含sheet参数的完整URL",)
                
                api_url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values"
                print(f"[飞书写入] 使用飞书表格API v2，spreadsheet_token: {spreadsheet_token}, sheet_name: {sheet_name}")
            
            # 构建请求体 - 使用工作表名称
            write_data = {
                "valueRange": {
                    "range": f"{sheet_name}!{cell_range}",
                    "values": [[data]]
                }
            }
            
            print(f"[飞书写入] 写入数据到单元格 {cell_range} (行{row}, 列{column}): {data}")
            
            response = requests.put(api_url, headers=headers, json=write_data, timeout=30)
            
            if response.status_code != 200:
                error_msg = f"Error: 飞书API写入失败 (状态码: {response.status_code})"
                print(f"[飞书写入] {error_msg}")
                try:
                    error_detail = response.json()
                    print(f"[飞书写入] 错误详情: {error_detail}")
                except:
                    pass
                return (error_msg,)
            
            result = response.json()
            print(f"[飞书写入] API完整响应: {result}")
            
            # 检查写入结果 - 根据飞书API文档修正响应格式
            if result.get("code") == 0 or result.get("msg") == "success":
                success_msg = f"成功写入数据到 {cell_range}"
                print(f"[飞书写入] {success_msg}")
                return (success_msg,)
            elif "code" not in result and "msg" not in result and "error" not in result:
                # 某些情况下，成功的响应可能没有code字段
                success_msg = f"成功写入数据到 {cell_range}"
                print(f"[飞书写入] {success_msg}")
                return (success_msg,)
            else:
                error_msg = f"Error: 写入失败: code={result.get('code')}, msg={result.get('msg', '未知错误')}, 完整响应: {result}"
                print(f"[飞书写入] {error_msg}")
                return (error_msg,)
                
        except json.JSONDecodeError:
            return ("Error: 飞书配置格式错误",)
        except Exception as e:
            error_msg = f"Error: 写入飞书数据失败: {str(e)}"
            print(f"[飞书写入] {error_msg}")
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
            
            print(f"[飞书写入] 正在获取访问令牌，app_id: {app_id[:10]}...")
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code != 200:
                error_msg = f"Error: 获取访问令牌失败 (状态码: {response.status_code}), 响应: {response.text}"
                print(f"[飞书写入] {error_msg}")
                return error_msg
            
            result = response.json()
            print(f"[飞书写入] Token API响应: {result}")
            
            if result.get("code") == 0:
                token = result.get("tenant_access_token")
                print(f"[飞书写入] 访问令牌获取成功")
                return token
            else:
                error_msg = f"Error: 获取访问令牌失败: code={result.get('code')}, msg={result.get('msg', '未知错误')}"
                print(f"[飞书写入] {error_msg}")
                return error_msg
                
        except Exception as e:
            error_msg = f"Error: 获取访问令牌异常: {str(e)}"
            print(f"[飞书写入] {error_msg}")
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
                print(f"[飞书写入] 从URL中提取到sheet参数: {sheet_param}")
                return sheet_param
            else:
                # 当URL中没有sheet参数时，通过API获取第一个工作表名称
                print(f"[飞书写入] URL中没有sheet参数，尝试通过API获取工作表列表")
                return None  # 返回None表示需要通过API获取
        except Exception as e:
            print(f"[飞书写入] 解析URL时发生错误: {str(e)}")
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
            
            print(f"[飞书写入] 正在获取工作表列表...")
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                error_msg = f"Error: 获取工作表列表失败 (状态码: {response.status_code})"
                print(f"[飞书写入] {error_msg}")
                return None
            
            result = response.json()
            
            if result.get("code") == 0 and "data" in result:
                sheets = result["data"].get("sheets", [])
                if sheets:
                    # 使用第一个工作表的sheetId作为sheet名称（符合飞书API要求）
                    first_sheet = sheets[0]
                    sheet_id = first_sheet.get("sheetId", "")
                    print(f"[飞书写入] 使用第一个工作表的sheetId: {sheet_id}")
                    return sheet_id
                else:
                    print(f"[飞书写入] 未找到任何工作表")
                    return None
            else:
                error_msg = f"Error: 获取工作表列表失败: code={result.get('code')}, msg={result.get('msg', '未知错误')}"
                print(f"[飞书写入] {error_msg}")
                return None
                
        except Exception as e:
            error_msg = f"Error: 获取工作表列表异常: {str(e)}"
            print(f"[飞书写入] {error_msg}")
            return None