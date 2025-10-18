import json
import time
import requests

# -------------------------------------------------------------------
# 飞书读取表格数据差节点
# -------------------------------------------------------------------
class FeishuReadDiffNode:
    @classmethod
    def IS_CHANGED(s, **kwargs): 
        return time.time()
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "feishu_config": ("STRING", {"forceInput": True}),
                "selection": (["行", "列"], {"default": "行"}),
                "indexes_str": ("STRING", {"default": "1,2", "multiline": False}),
                "force_refresh": ("BOOLEAN", {"default": False}),
            }
        }
    
    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("difference",)
    FUNCTION = "read_diff"
    CATEGORY = "AFA/飞书表格"
    
    def read_diff(self, feishu_config, selection, indexes_str, force_refresh):
        """
        读取飞书表格中指定行或列的数据差值 - 统计整列/行的数据数量并计算绝对差值
        
        Args:
            feishu_config: 飞书配置字符串（JSON格式）
            selection: 选择模式（"行" 或 "列"）
            indexes_str: 索引字符串，用逗号分隔（如 "1,2" 表示第1行/列和第2行/列）
            force_refresh: 是否强制刷新
            
        Returns:
            数据差值（整数）
        """
        try:
            # 解析配置
            if feishu_config.startswith("Error:"):
                return (0,)
                
            config = json.loads(feishu_config)
            app_id = config.get("app_id")
            app_secret = config.get("app_secret")
            sheet_url = config.get("sheet_url")
            sheet_id = config.get("sheet_id")
            
            if not all([app_id, app_secret]) or not (sheet_url or sheet_id):
                print("[飞书数据差] Error: 飞书配置信息不完整")
                return (0,)
            
            # 解析索引字符串
            try:
                indexes = [int(x.strip()) for x in indexes_str.split(",")]
                if len(indexes) != 2:
                    print("[飞书数据差] Error: 需要提供两个索引值")
                    return (0,)
                index1, index2 = indexes
            except ValueError:
                print("[飞书数据差] Error: 索引格式错误")
                return (0,)
            
            # 获取访问令牌
            access_token = self._get_access_token(app_id, app_secret)
            if not access_token or (isinstance(access_token, str) and access_token.startswith("Error:")):
                print(f"[飞书数据差] 获取访问令牌失败: {access_token}")
                return (0,)
            
            # 从URL中提取spreadsheet_token
            spreadsheet_token = self._extract_spreadsheet_token(sheet_url, sheet_id)
            
            print(f"[飞书数据差] 使用表格标识: {spreadsheet_token}")
            print(f"[飞书数据差] 选择模式: {selection}, 索引1: {index1}, 索引2: {index2}")
            
            # 统计两个位置的数据数量
            count1 = self._count_data_in_range(access_token, spreadsheet_token, selection, index1)
            count2 = self._count_data_in_range(access_token, spreadsheet_token, selection, index2)
            
            if selection == "列":
                print(f"[飞书数据差] 第{index1}列数据数量: {count1}")
                print(f"[飞书数据差] 第{index2}列数据数量: {count2}")
            else:
                print(f"[飞书数据差] 第{index1}行数据数量: {count1}")
                print(f"[飞书数据差] 第{index2}行数据数量: {count2}")
            
            # 计算绝对差值（确保结果永远是正数）
            diff = abs(count1 - count2)
            print(f"[飞书数据差] 计算结果: |{count1} - {count2}| = {diff}")
            return (diff,)
                
        except json.JSONDecodeError:
            print("[飞书数据差] Error: 飞书配置格式错误")
            return (0,)
        except Exception as e:
            print(f"[飞书数据差] Error: 读取数据差失败: {str(e)}")
            return (0,)
    
    def _count_data_in_range(self, access_token, spreadsheet_token, selection, index):
        """统计指定列或行中有数据的单元格数量"""
        try:
            # 获取工作表名称
            sheet_name = self._get_sheet_list(access_token, spreadsheet_token)
            if sheet_name is None:
                print(f"[飞书数据差] 无法获取工作表信息")
                return 0
            
            # 构建API请求
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # 根据选择模式构建范围
            if selection == "列":
                # 读取整列数据 (A:A, B:B, 等等)
                column_letter = self._number_to_column_letter(index)
                range_param = f"{sheet_name}!{column_letter}:{column_letter}"
                print(f"[飞书数据差] 统计第{index}列({column_letter}列)的数据数量")
            else:  # 行
                # 读取整行数据 (1:1, 2:2, 等等)
                range_param = f"{sheet_name}!{index}:{index}"
                print(f"[飞书数据差] 统计第{index}行的数据数量")
            
            # 构建API URL
            api_url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/{range_param}"
            print(f"[飞书数据差] API URL: {api_url}")
            
            response = requests.get(api_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                print(f"[飞书数据差] 读取范围 {range_param} 失败 (状态码: {response.status_code})")
                return 0
            
            result = response.json()
            print(f"[飞书数据差] API响应: {result}")
            
            # 解析响应数据并统计非空单元格
            count = 0
            if "data" in result:
                data = result["data"]
                # 检查不同的响应格式
                if "valueRange" in data and "values" in data["valueRange"]:
                    values = data["valueRange"]["values"]
                elif "values" in data:
                    values = data["values"]
                elif "valueRanges" in data and len(data["valueRanges"]) > 0:
                    values = data["valueRanges"][0].get("values", [])
                else:
                    values = []
                
                # 统计非空单元格数量
                for row_data in values:
                    for cell_value in row_data:
                        if cell_value is not None and str(cell_value).strip() != "":
                            count += 1
                
                print(f"[飞书数据差] 统计到 {count} 个非空单元格")
                return count
            else:
                print(f"[飞书数据差] API响应格式异常")
                return 0
            
        except Exception as e:
            print(f"[飞书数据差] 统计数据异常: {str(e)}")
            return 0
    
    def _number_to_column_letter(self, column_number):
        """将列号转换为字母 (1->A, 2->B, 26->Z, 27->AA)"""
        column_letter = ""
        while column_number > 0:
            column_number -= 1
            column_letter = chr(65 + column_number % 26) + column_letter
            column_number //= 26
        return column_letter
    
    def _read_cell_value(self, access_token, sheet_id, row, column):
        """读取指定单元格的值"""
        try:
            # 将行列号转换为A1格式
            cell_range = self._convert_to_a1_notation(row, column)
            
            # 构建API请求
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # 从sheet_id中提取spreadsheet_token（实际上sheet_id就是spreadsheet_token）
            spreadsheet_token = sheet_id
            
            # 获取工作表名称（默认使用第一个工作表）
            sheet_name = self._get_sheet_list(access_token, spreadsheet_token)
            if sheet_name is None:
                print(f"[飞书数据差] 无法获取工作表信息")
                return ""
            
            # 构建正确的v2 API URL格式：range参数在URL路径中
            range_param = f"{sheet_name}!{cell_range}"
            api_url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/{range_param}"
            
            print(f"[飞书数据差] 读取单元格 {cell_range} (行{row}, 列{column})")
            print(f"[飞书数据差] API URL: {api_url}")
            
            response = requests.get(api_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                print(f"[飞书数据差] 读取单元格 {cell_range} 失败 (状态码: {response.status_code})")
                return ""
            
            result = response.json()
            print(f"[飞书数据差] API完整响应: {result}")
            
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
                    print(f"[飞书数据差] 成功读取数据: {cell_value}")
                    return cell_value
                else:
                    print(f"[飞书数据差] 单元格为空")
                    return ""
            else:
                print(f"[飞书数据差] API响应格式异常，实际响应: {result}")
                return ""
            
        except Exception as e:
            print(f"[飞书数据差] 读取单元格异常: {str(e)}")
            return ""
    
    def _get_access_token(self, app_id, app_secret):
        """获取飞书访问令牌"""
        try:
            url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            headers = {"Content-Type": "application/json"}
            data = {
                "app_id": app_id,
                "app_secret": app_secret
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code != 200:
                return f"Error: 获取访问令牌失败 (状态码: {response.status_code})"
            
            result = response.json()
            
            if result.get("code") == 0:
                return result.get("tenant_access_token")
            else:
                return f"Error: 获取访问令牌失败: {result.get('msg', '未知错误')}"
                
        except Exception as e:
            return f"Error: 获取访问令牌异常: {str(e)}"
    
    def _extract_spreadsheet_token(self, sheet_url, sheet_id):
        """从飞书表格URL或ID中提取spreadsheet_token"""
        try:
            # 优先使用sheet_url
            if sheet_url and sheet_url.strip():
                # 飞书表格URL格式: https://bytedance.larkoffice.com/sheets/{spreadsheet_token}?sheet={sheet_id}
                if "/sheets/" in sheet_url:
                    parts = sheet_url.split("/sheets/")
                    if len(parts) > 1:
                        token_part = parts[1].split("?")[0]  # 去掉查询参数
                        return token_part
            
            # 如果URL无效，使用sheet_id
            if sheet_id and sheet_id.strip():
                return sheet_id
            
            return None
        except Exception as e:
            print(f"[飞书数据差] 提取spreadsheet_token失败: {str(e)}")
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
            
            print(f"[飞书数据差] 正在获取工作表列表...")
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                print(f"[飞书数据差] 获取工作表列表失败 (状态码: {response.status_code})")
                return None
            
            result = response.json()
            
            if result.get("code") == 0 and "data" in result:
                sheets = result["data"].get("sheets", [])
                if sheets:
                    # 使用第一个工作表的sheetId作为sheet名称（符合飞书API要求）
                    first_sheet = sheets[0]
                    sheet_id = first_sheet.get("sheetId", "")
                    print(f"[飞书数据差] 使用第一个工作表的sheetId: {sheet_id}")
                    return sheet_id
                else:
                    print(f"[飞书数据差] 未找到任何工作表")
                    return None
            else:
                print(f"[飞书数据差] 获取工作表列表失败: code={result.get('code')}, msg={result.get('msg', '未知错误')}")
                return None
                
        except Exception as e:
            print(f"[飞书数据差] 获取工作表列表异常: {str(e)}")
            return None
    
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