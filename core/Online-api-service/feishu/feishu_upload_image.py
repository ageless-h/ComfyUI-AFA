import json
import time
import requests
import base64
import io
from PIL import Image
import numpy as np

# -------------------------------------------------------------------
# 飞书上传图像节点
# -------------------------------------------------------------------
class FeishuUploadImageNode:
    @classmethod
    def IS_CHANGED(s, **kwargs): 
        return time.time()
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "feishu_config": ("STRING", {"forceInput": True}),
                "row": ("INT", {"default": 1, "min": 1, "max": 10000}),
                "column": ("INT", {"default": 1, "min": 1, "max": 1000}),
                "insert_mode": (["单元格内图像", "浮动图片"], {"default": "单元格内图像"}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("upload_result",)
    FUNCTION = "upload_image"
    CATEGORY = "AFA/飞书表格"
    
    def upload_image(self, image, feishu_config, row, column, insert_mode):
        """
        上传图像到飞书表格指定单元格
        
        Args:
            image: 输入图像（ComfyUI格式）
            feishu_config: 飞书配置字符串（JSON格式）
            row: 行号（从1开始）
            column: 列号（从1开始）
            insert_mode: 插入模式（"单元格内图像" 或 "浮动图片"）
            
        Returns:
            上传操作结果字符串
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
            spreadsheet_token = config.get("spreadsheet_token")
            
            if not all([app_id, app_secret, sheet_url, sheet_id, spreadsheet_token]):
                return ("Error: 飞书配置信息不完整",)
            
            # 获取访问令牌
            access_token = self._get_access_token(app_id, app_secret)
            if access_token.startswith("Error:"):
                return (access_token,)
            
            # 转换图像格式
            image_bytes = self._convert_image_to_bytes(image)
            if not image_bytes:
                return ("Error: 图像转换失败",)
            
            # 根据插入模式选择不同的处理方式
            if insert_mode == "单元格内图像":
                # 使用values_image API直接在单元格内插入图像
                result = self._insert_image_in_cell(access_token, spreadsheet_token, sheet_id, row, column, image_bytes)
            else:
                # 使用传统的浮动图片方式
                # 上传图像到飞书
                file_token = self._upload_image_to_feishu(access_token, image_bytes, spreadsheet_token)
                if file_token.startswith("Error:"):
                    return (file_token,)
                
                # 将图像插入为浮动图片
                result = self._insert_image_to_cell(access_token, spreadsheet_token, sheet_id, row, column, file_token)
            
            return (result,)
                
        except json.JSONDecodeError:
            return ("Error: 飞书配置格式错误",)
        except Exception as e:
            error_msg = f"Error: 上传图像失败: {str(e)}"
            print(f"[飞书上传图像] {error_msg}")
            return (error_msg,)
    
    def _convert_image_to_bytes(self, image):
        """将ComfyUI图像转换为字节数据"""
        try:
            # 将tensor转换为PIL图像
            if isinstance(image, np.ndarray):
                # 如果是numpy数组
                if image.ndim == 4:
                    image = image[0]  # 取第一张图像
                if image.dtype != np.uint8:
                    image = (image * 255).astype(np.uint8)
                pil_image = Image.fromarray(image)
            else:
                # 如果是tensor
                image_np = image.cpu().numpy()
                if image_np.ndim == 4:
                    image_np = image_np[0]  # 取第一张图像
                if image_np.dtype != np.uint8:
                    image_np = (image_np * 255).astype(np.uint8)
                pil_image = Image.fromarray(image_np)
            
            # 转换为字节数据
            img_buffer = io.BytesIO()
            pil_image.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            return img_buffer.getvalue()
            
        except Exception as e:
            print(f"[飞书上传图像] 图像转换失败: {str(e)}")
            return None
    
    def _upload_image_to_feishu(self, access_token, image_bytes, spreadsheet_token):
        """上传图像到飞书并获取文件token - 使用Drive媒体API"""
        try:
            url = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all"
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            
            file_size = len(image_bytes)
            
            files = {
                "file": ("image.png", image_bytes, "image/png")
            }
            
            data = {
                "file_name": "image.png",
                "parent_type": "sheet_image",  # 表格图像类型
                "parent_node": spreadsheet_token,  # 表格token
                "size": str(file_size)
            }
            
            print(f"[飞书上传图像] 正在上传图像到飞书...")
            
            response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
            
            if response.status_code != 200:
                error_msg = f"Error: 上传图像到飞书失败 (状态码: {response.status_code})"
                print(f"[飞书上传图像] {error_msg}")
                return error_msg
            
            result = response.json()
            
            if result.get("code") == 0:
                file_token = result.get("data", {}).get("file_token")
                if file_token:
                    print(f"[飞书上传图像] 图像上传成功，文件token: {file_token}")
                    return file_token
                else:
                    return "Error: 未获取到文件token"
            else:
                return f"Error: 上传失败: {result.get('msg', '未知错误')}"
                
        except Exception as e:
            return f"Error: 上传图像异常: {str(e)}"
    
    def _insert_image_in_cell(self, access_token, spreadsheet_token, sheet_id, row, column, image_bytes):
        """使用values_image API直接在单元格内插入图像"""
        try:
            # 将行列号转换为A1格式
            cell_range = self._convert_to_a1_notation(row, column)
            
            # 构建API请求
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # 将图像转换为整数数组（飞书API要求的格式）
            image_array = list(image_bytes)
            
            # 构建请求数据
            write_data = {
                "range": f"{sheet_id}!{cell_range}:{cell_range}",
                "image": image_array,
                "name": f"cell_image_{row}_{column}.png"
            }
            
            # 使用values_image API
            api_url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values_image"
            
            print(f"[飞书上传图像] 使用values_image API插入图像到单元格 {sheet_id}!{cell_range} (行{row}, 列{column})")
            
            response = requests.post(api_url, headers=headers, json=write_data, timeout=30)
            
            if response.status_code != 200:
                error_msg = f"Error: 插入单元格内图像失败 (状态码: {response.status_code})"
                print(f"[飞书上传图像] {error_msg}")
                try:
                    error_detail = response.json()
                    print(f"[飞书上传图像] 错误详情: {error_detail}")
                except:
                    pass
                return error_msg
            
            result = response.json()
            
            # 检查插入结果
            if result.get("code") == 0:
                success_msg = f"成功插入图像到单元格 {sheet_id}!{cell_range} (行{row}, 列{column})"
                print(f"[飞书上传图像] {success_msg}")
                return success_msg
            else:
                error_msg = f"Error: 插入单元格内图像失败: {result.get('msg', '未知错误')}"
                print(f"[飞书上传图像] {error_msg}")
                return error_msg
                
        except Exception as e:
            return f"Error: 插入单元格内图像异常: {str(e)}"

    def _insert_image_to_cell(self, access_token, spreadsheet_token, sheet_id, row, column, file_token):
        """将图像作为浮动图片插入到表格"""
        try:
            # 将行列号转换为A1格式
            cell_range = self._convert_to_a1_notation(row, column)
            
            # 构建API请求
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # 使用浮动图片API插入图像
            # 根据飞书官方文档，range格式应该是 "sheet_id!A1:A1"
            write_data = {
                "float_image_token": file_token,
                "range": f"{sheet_id}!{cell_range}:{cell_range}",  # 单元格范围格式：A1:A1
                "width": 300,  # 图片宽度，可以根据需要调整
                "height": 200  # 图片高度，可以根据需要调整
            }
            
            # 飞书浮动图片API端点
            api_url = f"https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/{spreadsheet_token}/sheets/{sheet_id}/float_images"
            
            print(f"[飞书上传图像] 插入浮动图像到单元格 {sheet_id}!{cell_range} (行{row}, 列{column})")
            
            response = requests.post(api_url, headers=headers, json=write_data, timeout=30)
            
            if response.status_code != 200:
                error_msg = f"Error: 插入浮动图像到表格失败 (状态码: {response.status_code})"
                print(f"[飞书上传图像] {error_msg}")
                try:
                    error_detail = response.json()
                    print(f"[飞书上传图像] 错误详情: {error_detail}")
                except:
                    pass
                return error_msg
            
            result = response.json()
            
            # 检查插入结果
            if result.get("code") == 0:
                success_msg = f"成功上传浮动图像到 {sheet_id}!{cell_range}"
                print(f"[飞书上传图像] {success_msg}")
                return success_msg
            else:
                error_msg = f"Error: 插入浮动图像失败: {result.get('msg', '未知错误')}"
                print(f"[飞书上传图像] {error_msg}")
                return error_msg
                
        except Exception as e:
            return f"Error: 插入浮动图像异常: {str(e)}"
    
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
    
    def _convert_to_a1_notation(self, row, column):
        """将行列号转换为A1格式"""
        # 将列号转换为字母
        column_letter = ""
        while column > 0:
            column -= 1
            column_letter = chr(65 + column % 26) + column_letter
            column //= 26
        
        cell_ref = f"{column_letter}{row}"
        return cell_ref  # 返回A1格式