import os
import json
import time
import re
import requests
import numpy as np
import torch
import tempfile
import torchaudio
import comfy.utils
import io
import base64

# 创建音频对象的辅助函数
def create_audio_object(url, max_duration_seconds=20):
    """创建ComfyUI可用的音频对象
    
    Args:
        url: 音频URL，如果为空则创建空音频
        max_duration_seconds: 最大音频长度（秒）
    """
    if not url:
        # 创建一个空的音频对象，确保维度正确
        # ComfyUI期望的格式是 [batch, channels, samples] - 必须是3D
        sample_rate = 16000
        waveform = torch.zeros((1, 1, int(sample_rate * max_duration_seconds)), dtype=torch.float32)  # [batch=1, 单声道, max_duration秒]
        return {
            "waveform": waveform,
            "sample_rate": sample_rate
        }
    
    try:
        # 下载音频文件
        print(f"[Suno生成器] 开始下载音频: {url}")
        
        # 使用会话管理和适当的超时设置
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Connection': 'close'  # 明确关闭连接以避免连接重置错误
        })
        
        try:
            response = session.get(url, stream=True, timeout=(10, 30))  # 连接超时10秒，读取超时30秒
            response.raise_for_status()
        except (requests.exceptions.ConnectionError, ConnectionResetError) as e:
            print(f"[Suno生成器] 网络连接错误，尝试重试: {e}")
            # 重试一次
            try:
                response = session.get(url, stream=True, timeout=(10, 30))
                response.raise_for_status()
            except Exception as retry_e:
                print(f"[Suno生成器] 重试失败: {retry_e}")
                raise retry_e
        finally:
            session.close()  # 确保会话被正确关闭
        
        # 保存为临时文件
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            temp_path = temp_file.name
            
        print(f"[Suno生成器] 音频已保存到临时文件: {temp_path}")
        
        # 使用torchaudio加载音频
        try:
            # 加载音频文件
            waveform, sample_rate = torchaudio.load(temp_path)
            print(f"[Suno生成器] 音频加载成功，原始形状: {waveform.shape}, 采样率: {sample_rate}")
            
            # 关键修复：确保波形始终是2D张量 [channels, samples]，然后转换为3D
            if len(waveform.shape) == 1:
                # 1D -> 2D: 添加通道维度
                waveform = waveform.unsqueeze(0)
                print(f"[Suno生成器] 1D转2D: {waveform.shape}")
            elif len(waveform.shape) == 0:
                # 0D -> 2D: 创建单个样本
                waveform = waveform.unsqueeze(0).unsqueeze(0)
                print(f"[Suno生成器] 0D转2D: {waveform.shape}")
            elif len(waveform.shape) > 2:
                # 多维 -> 2D: 只保留前两个维度
                waveform = waveform[:2] if waveform.shape[0] <= 2 else waveform[:2]
                print(f"[Suno生成器] 多维转2D: {waveform.shape}")
            
            # 确保第一个维度是通道数（1或2）
            if waveform.shape[0] > 2:
                waveform = waveform[:2]  # 只保留前两个通道
                print(f"[Suno生成器] 限制通道数: {waveform.shape}")
            
            # 如果是立体声，转换为单声道以避免复杂性
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
                print(f"[Suno生成器] 转为单声道: {waveform.shape}")
            
            # 关键修复：转换为3D张量 [batch, channels, samples]
            waveform = waveform.unsqueeze(0)  # 添加batch维度
            print(f"[Suno生成器] 转换为3D张量 [batch, channels, samples]: {waveform.shape}")
            
            # 确保数据类型为float32
            waveform = waveform.float()
            
            # 确保张量是连续的
            if not waveform.is_contiguous():
                waveform = waveform.contiguous()
                print(f"[Suno生成器] 强制连续化")
            
            # 根据max_duration参数计算最大采样点数（0表示不限制长度）
            if max_duration_seconds > 0:
                max_length = int(sample_rate * max_duration_seconds)  # 将秒转换为采样点数
                if waveform.shape[2] > max_length:  # 现在是3D，样本在第2维
                    waveform = waveform[:, :, :max_length]
                    print(f"[Suno生成器] 音频太长，已裁剪到 {max_length} 采样点 ({max_duration_seconds}秒)")
            else:
                print(f"[Suno生成器] 保持完整音频长度: {waveform.shape[2]} 采样点 ({waveform.shape[2]/sample_rate:.2f}秒)")
            
            # 最终验证：确保是3D张量
            assert len(waveform.shape) == 3, f"波形必须是3D张量，当前形状: {waveform.shape}"
            assert waveform.shape[0] >= 1, f"batch数必须>=1，当前: {waveform.shape[0]}"
            assert waveform.shape[1] >= 1, f"通道数必须>=1，当前: {waveform.shape[1]}"
            assert waveform.shape[2] >= 1, f"样本数必须>=1，当前: {waveform.shape[2]}"
            
            # 创建音频对象 - 只包含必需的字段
            audio_obj = {
                "waveform": waveform,
                "sample_rate": sample_rate
            }
            
            print(f"[Suno生成器] 音频对象创建成功，最终波形形状: {waveform.shape}")
            return audio_obj
            
        except Exception as e:
            print(f"!!! [Suno生成器] 使用torchaudio加载音频失败: {e}")
            # 创建一个安全的空音频对象
            waveform = torch.zeros((1, 1, 16000), dtype=torch.float32)  # 确保3D [batch, channels, samples]
            sample_rate = 16000
            return {
                "waveform": waveform,
                "sample_rate": sample_rate
            }
        
    except Exception as e:
        print(f"!!! [Suno生成器] 加载音频文件时出错: {e}")
        # 返回安全的空音频对象
        waveform = torch.zeros((1, 1, 16000), dtype=torch.float32)  # 确保3D [batch, channels, samples]
        sample_rate = 16000
        return {
            "waveform": waveform,
            "sample_rate": sample_rate
        }
    finally:
        # 尝试删除临时文件
        try:
            if 'temp_path' in locals():
                os.unlink(temp_path)
        except:
            pass

class SunoGeneratorNode:
    """Suno文生歌高级生成器"""
    @classmethod
    def IS_CHANGED(s, **kwargs): return time.time()
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "API密钥": ("API_KEY",),
                "基础URL": ("BASE_URL",),
                "模型名称": ("MODEL_NAME",),
                "任务类型": (["普通生成", "续写扩展", "翻唱生成"], 
                            {"default": "普通生成", "tooltip": "选择生成模式：普通生成新歌曲/续写扩展现有歌曲/翻唱生成"}),
                "纯音乐模式": ("BOOLEAN", {"default": False, "tooltip": "生成纯音乐（无人声）"}),
                "最大时长": ("INT", {"default": 0, "min": 0, "max": 600, "step": 5, "tooltip": "最大音频长度（秒），设置为0表示不限制长度"}),
                "自定义模式": ("BOOLEAN", {"default": True, "tooltip": "启用自定义模式，支持完整歌词和风格控制"}),
            },
            "optional": {
                "歌曲标题": ("STRING", {"default": "", "placeholder": "歌曲标题（最多80字符）"}),
                "歌词内容": ("STRING", {"multiline": True, "default": "", "placeholder": "歌词内容（自定义模式下V4.5+支持5000字符，V4及以下支持3000字符）"}),
                "风格标签": ("STRING", {"default": "", "placeholder": "音乐风格标签，如：pop, rock, jazz等（V4.5+支持1000字符，V4及以下支持200字符）"}),
                "歌曲描述": ("STRING", {"multiline": True, "default": "", "placeholder": "非自定义模式下的歌曲描述（最多500字符）"}),
                "生成类型": ("STRING", {"default": "TEXT", "placeholder": "生成类型，默认为TEXT"}),
                "声音性别": (["自动", "女声", "男声"], {"default": "自动", "tooltip": "选择人声性别"}),
                "参考音频": ("AUDIO", {"tooltip": "用于续写扩展的参考音频（续写模式时使用）"}),
                "参考音频URL": ("STRING", {"default": "", "placeholder": "参考音频URL（备用输入方式）"}),
                "排除风格": ("STRING", {"default": "", "placeholder": "要避免的音乐风格"}),
                "风格权重": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.1, "tooltip": "风格影响强度"}),
                "创意程度": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.1, "tooltip": "音乐创意和随机性程度"}),
                # 续写功能参数
                "前任务ID": ("STRING", {"default": "", "placeholder": "续写的前任务ID（续写模式时填写）"}),
                "续写起点": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 300.0, "step": 0.1, "tooltip": "从第几秒开始继续创作"}),
                "续写歌曲ID": ("STRING", {"default": "", "placeholder": "需要继续创作的歌曲ID"}),
                "续写提示词": ("STRING", {"default": "", "placeholder": "继续创作的对齐提示词"}),
                # 翻唱生成功能参数
                "翻唱音频ID": ("STRING", {"default": "", "placeholder": "要翻唱的原曲ID或上传的音频clip ID"}),
                "填充开始时间": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 300.0, "step": 0.1, "tooltip": "音频填充开始时间（秒）"}),
                "填充结束时间": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 300.0, "step": 0.1, "tooltip": "音频填充结束时间（秒）"}),
                # 通用参数
                "随机种子": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "随机种子，相同种子产生相似结果"}),
                "超时时间": ("INT", {"default": 300, "min": 30, "max": 600, "tooltip": "请求超时时间（秒）"}),
                "最大尝试次数": ("INT", {"default": 120, "min": 1, "max": 200, "tooltip": "最大轮询尝试次数"}),
                "重试间隔": ("FLOAT", {"default": 5.0, "min": 1.0, "max": 60.0, "step": 0.5, "tooltip": "重试间隔时间（秒）"}),
            }
        }
    
    RETURN_TYPES = ("AUDIO", "AUDIO", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("音频1", "音频2", "音频链接1", "音频链接2", "提示词", "任务ID", "响应信息", "片段ID", "歌曲标题")
    FUNCTION = "generate_music"
    CATEGORY = "AFA/音乐"

    def generate_music(self, **kwargs):
        # 参数映射：中文参数名 -> 英文内部变量名
        param_mapping = {
            "API密钥": "api_key",
            "基础URL": "base_url", 
            "模型名称": "model_name",
            "任务类型": "task_type",
            "纯音乐模式": "make_instrumental",
            "最大时长": "max_duration",
            "自定义模式": "custom_mode",
            "歌曲标题": "title",
            "歌词内容": "lyrics",
            "风格标签": "style_tags",
            "歌曲描述": "description_prompt",
            "生成类型": "generation_type",
            "声音性别": "vocal_gender",
            "参考音频": "reference_audio",
            "参考音频URL": "reference_audio_url",
            "排除风格": "negative_tags",
            "风格权重": "style_weight",
            "创意程度": "weirdness_constraint",
            "前任务ID": "task_id",
            "续写起点": "continue_at",
            "续写歌曲ID": "continue_clip_id",
            "续写提示词": "continued_aligned_prompt",
            "翻唱音频ID": "cover_clip_id",
            "填充开始时间": "infill_start_s",
            "填充结束时间": "infill_end_s",
            "随机种子": "seed",
            "超时时间": "timeout",
            "最大尝试次数": "max_attempts",
            "重试间隔": "retry_delay"
        }
        
        # 任务类型映射
        task_type_mapping = {
            "普通生成": "generate",
            "续写扩展": "extend", 
            "翻唱生成": "cover"
        }
        
        # 声音性别映射
        vocal_gender_mapping = {
            "自动": "auto",
            "女声": "female",
            "男声": "male"
        }
        
        # 提取并转换参数
        params = {}
        for chinese_name, english_name in param_mapping.items():
            if chinese_name in kwargs:
                params[english_name] = kwargs[chinese_name]
        
        # 设置默认值
        api_key = params.get("api_key", "")
        base_url = params.get("base_url", "")
        model_name = params.get("model_name", "")
        task_type = task_type_mapping.get(params.get("task_type", "普通生成"), "generate")
        make_instrumental = params.get("make_instrumental", False)
        max_duration = params.get("max_duration", 0)
        custom_mode = params.get("custom_mode", True)
        title = params.get("title", "")
        lyrics = params.get("lyrics", "")
        style_tags = params.get("style_tags", "")
        description_prompt = params.get("description_prompt", "")
        generation_type = params.get("generation_type", "TEXT")
        vocal_gender = vocal_gender_mapping.get(params.get("vocal_gender", "自动"), "auto")
        reference_audio = params.get("reference_audio", None)
        reference_audio_url = params.get("reference_audio_url", "")
        negative_tags = params.get("negative_tags", "")
        style_weight = params.get("style_weight", 0.5)
        weirdness_constraint = params.get("weirdness_constraint", 0.5)
        task_id = params.get("task_id", "")
        continue_at = params.get("continue_at", 0.0)
        continue_clip_id = params.get("continue_clip_id", "")
        continued_aligned_prompt = params.get("continued_aligned_prompt", "")
        cover_clip_id = params.get("cover_clip_id", "")
        infill_start_s = params.get("infill_start_s", 0.0)
        infill_end_s = params.get("infill_end_s", 0.0)
        seed = params.get("seed", 0)
        timeout = params.get("timeout", 300)
        max_attempts = params.get("max_attempts", 120)
        retry_delay = params.get("retry_delay", 5.0)
        
        # 处理音频输入
        if reference_audio is not None and task_type == "extend":
            try:
                # 如果有音频输入，将其保存为临时文件并获取URL
                # 这里需要实现音频上传到 Suno 的逻辑
                print(">>> [Suno生成器] 检测到音频输入，正在处理...")
                # TODO: 实现音频上传功能
                # reference_audio_url = self.upload_audio_to_suno(reference_audio, api_key, base_url)
            except Exception as e:
                print(f"!!! [Suno生成器] 音频处理失败: {str(e)}")
                reference_audio_url = ""
        """生成音乐"""
        if not api_key:
            error_message = "API密钥不能为空"
            print(f"!!! [Suno生成器] {error_message}")
            empty_audio = create_audio_object("", max_duration_seconds=max_duration)
            return (empty_audio, empty_audio, "", "", "", "", json.dumps({"error": error_message}, ensure_ascii=False), "", "")
        
        # 验证任务类型特定的必需参数
        if task_type == "extend" and not task_id:
            error_message = "续写扩展模式下前任务ID不能为空"
            print(f"!!! [Suno生成器] {error_message}")
            empty_audio = create_audio_object("", max_duration_seconds=max_duration)
            return (empty_audio, empty_audio, "", "", "", "", json.dumps({"error": error_message}, ensure_ascii=False), "", "")
        
        if task_type == "cover" and not cover_clip_id:
            error_message = "翻唱生成模式下翻唱音频ID不能为空"
            print(f"!!! [Suno生成器] {error_message}")
            empty_audio = create_audio_object("", max_duration_seconds=max_duration)
            return (empty_audio, empty_audio, "", "", "", "", json.dumps({"error": error_message}, ensure_ascii=False), "", "")
        
        # 直接使用选择器传入的模型名称
        mv = model_name
        
        try:
            # 检查是否使用参考音频扩展功能
            use_reference_audio = bool(reference_audio_url.strip())
            
            # 根据模型版本确定字符限制
            is_v45_plus = any(v in mv.lower() for v in ['v4.5', 'v4_5', 'v5', 'chirp-v4-5', 'chirp-v5'])
            max_lyrics_chars = 5000 if is_v45_plus else 3000
            max_style_chars = 1000 if is_v45_plus else 200
            
            # 字符长度验证和截断
            if title and len(title) > 80:
                print(f"[Suno生成器] 警告：标题超过80字符，将被截断")
                title = title[:80]
            
            if lyrics and len(lyrics) > max_lyrics_chars:
                print(f"[Suno生成器] 警告：歌词超过{max_lyrics_chars}字符，将被截断")
                lyrics = lyrics[:max_lyrics_chars]
            
            if style_tags and len(style_tags) > max_style_chars:
                print(f"[Suno生成器] 警告：风格标签超过{max_style_chars}字符，将被截断")
                style_tags = style_tags[:max_style_chars]
            
            if description_prompt and len(description_prompt) > 500:
                print(f"[Suno生成器] 警告：描述提示超过500字符，将被截断")
                description_prompt = description_prompt[:500]
            
            # 根据任务类型构建API请求payload
            if task_type == "generate":
                # 普通生成
                endpoint = "/suno/generate"
                payload = {
                    "generation_type": generation_type,
                    "mv": mv,
                }
                
                if custom_mode:
                    # 自定义模式
                    if title:
                        payload["title"] = title
                    if style_tags:
                        payload["tags"] = style_tags
                    if not make_instrumental and lyrics:
                        payload["prompt"] = lyrics
                    if negative_tags:
                        payload["negative_tags"] = negative_tags
                else:
                    # 非自定义模式
                    if description_prompt:
                        payload["gpt_description_prompt"] = description_prompt
                
                payload["make_instrumental"] = make_instrumental
                
            elif task_type == "extend":
                # 续写功能
                endpoint = "/suno/generate"
                payload = {
                    "task_id": task_id,
                    "title": title,
                    "tags": style_tags,
                    "generation_type": generation_type,
                    "prompt": lyrics,
                    "negative_tags": negative_tags,
                    "mv": mv,
                    "continue_at": continue_at,
                    "continue_clip_id": continue_clip_id,
                    "task": "extend"
                }
                
                if continued_aligned_prompt:
                    payload["continued_aligned_prompt"] = continued_aligned_prompt
                    
            elif task_type == "cover":
                # 上传生成功能
                endpoint = "/suno/generate"
                payload = {
                    "prompt": lyrics,
                    "generation_type": generation_type,
                    "tags": style_tags,
                    "negative_tags": negative_tags,
                    "mv": mv,  # 直接使用选择器传入的模型名称
                    "title": title,
                    "continue_clip_id": continue_clip_id if continue_clip_id else None,
                    "continue_at": continue_at if continue_at > 0 else None,
                    "continued_aligned_prompt": continued_aligned_prompt if continued_aligned_prompt else None,
                    "infill_start_s": infill_start_s if infill_start_s > 0 else None,
                    "infill_end_s": infill_end_s if infill_end_s > 0 else None,
                    "task": "cover",
                    "cover_clip_id": cover_clip_id,
                    "task_id": task_id
                }
                
            # 处理参考音频扩展（可以与其他模式结合）
            if reference_audio_url.strip():
                endpoint = "/suno/upload-extend"
                payload = {
                    "uploadUrl": reference_audio_url,
                    "defaultParamFlag": False,
                    "instrumental": make_instrumental,
                    "model": mv,
                    "prompt": lyrics,
                    "style": style_tags
                }
            
            # 添加通用可选参数（仅在支持的任务类型中）
            if not reference_audio_url.strip():  # 非参考音频模式才添加这些参数
                if vocal_gender != "auto" and task_type in ["generate", "extend", "cover"]:
                    gender_map = {"female": "f", "male": "m"}
                    if vocal_gender in gender_map:
                        payload["vocal_gender"] = gender_map[vocal_gender]
                
                if style_weight != 0.5 and task_type == "generate":
                    payload["style_weight"] = style_weight
                    
                if weirdness_constraint != 0.5 and task_type == "generate":
                    payload["weirdness_constraint"] = weirdness_constraint

                if seed > 0:
                    payload["seed"] = seed
            
            pbar = comfy.utils.ProgressBar(100)
            pbar.update_absolute(10)
            
            headers = {
                "Authorization": f"Bearer {api_key}", 
                "Content-Type": "application/json",
                "Connection": "close"  # 明确关闭连接以避免连接重置错误
            }
            
            # 发送生成请求 - 根据功能使用对应端点
            api_url = f"{base_url}{endpoint}"
            print(f"[Suno生成器] 请求URL: {api_url}")
            print(f"[Suno生成器] 请求参数: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            
            # 使用会话管理和错误重试
            session = requests.Session()
            session.headers.update(headers)
            
            try:
                response = session.post(
                    api_url,
                    json=payload,
                    timeout=timeout
                )
            except (requests.exceptions.ConnectionError, ConnectionResetError) as e:
                print(f"[Suno生成器] API请求连接错误，尝试重试: {e}")
                # 重试一次
                try:
                    response = session.post(
                        api_url,
                        json=payload,
                        timeout=timeout
                    )
                except Exception as retry_e:
                    print(f"[Suno生成器] API请求重试失败: {retry_e}")
                    session.close()
                    empty_audio = create_audio_object("")
                    return (empty_audio, empty_audio, "", "", "", "", json.dumps({"error": f"连接错误: {retry_e}"}, ensure_ascii=False), "", "")
            finally:
                session.close()  # 确保会话被正确关闭
            
            pbar.update_absolute(20)
            
            if response.status_code != 200:
                error_message = f"API错误: {response.status_code} - {response.text}"
                print(f"!!! [Suno生成器] {error_message}")
                empty_audio = create_audio_object("")
                return (empty_audio, empty_audio, "", "", "", "", json.dumps({"error": error_message}, ensure_ascii=False), "", "")
                
            result = response.json()
            print(f"[Suno生成器] API响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            # 根据API文档，/suno/generate 应该返回包含clips的响应
            # 可能的响应格式：
            # 1. {"id": "xxx", "clips": [...]}  - 标准格式
            # 2. {"code": "success", "data": {"clips": [...]}} - t8封装格式
            
            clips = []
            task_id = ""
            
            # 检查是否是t8平台的封装格式
            if result.get("code") == "success" and "data" in result:
                data = result["data"]
                if isinstance(data, dict):
                    clips = data.get("clips", [])
                    task_id = data.get("id", "")
                elif isinstance(data, list):
                    clips = data
            else:
                # 标准格式
                clips = result.get("clips", [])
                task_id = result.get("id", "")
            
            print(f"[Suno生成器] 解析结果 - task_id: {task_id}, clips数量: {len(clips)}")
            
            # 获取clip IDs用于后续查询
            clip_ids = [clip.get("id", "") for clip in clips if clip.get("id")]
            
            if not clip_ids:
                error_message = "响应中没有clip IDs"
                print(f"!!! [Suno生成器] {error_message}")
                print(f"[Suno生成器] 完整响应: {json.dumps(result, ensure_ascii=False)}")
                empty_audio = create_audio_object("")
                return (empty_audio, empty_audio, "", "", "", "", json.dumps({"error": error_message, "response": result}, ensure_ascii=False), "", "")
            
            print(f"[Suno生成器] 找到 {len(clip_ids)} 个clip IDs: {clip_ids}")
                
            pbar.update_absolute(30)
            attempts = 0
            final_clips = []
            generated_prompt = ""
            extracted_tags = ""
            generated_title = ""
            
            # 轮询检查生成状态
            while attempts < max_attempts and len(final_clips) < 2:
                time.sleep(retry_delay)
                attempts += 1
                
                try:
                    # 根据API文档，使用feed API查询clips状态
                    # 使用会话管理和错误重试
                    query_session = requests.Session()
                    query_headers = headers.copy()
                    query_headers["Connection"] = "close"  # 明确关闭连接
                    query_session.headers.update(query_headers)
                    
                    try:
                        clip_response = query_session.get(
                            f"{base_url}/suno/feed/{','.join(clip_ids)}",
                            timeout=timeout
                        )
                    except (requests.exceptions.ConnectionError, ConnectionResetError) as e:
                        print(f"[Suno生成器] 状态查询连接错误 (尝试 {attempts}): {e}")
                        query_session.close()
                        continue  # 跳过这次查询，等待下次重试
                    finally:
                        query_session.close()  # 确保会话被正确关闭
                    
                    if clip_response.status_code != 200:
                        continue
                        
                    clips_data = clip_response.json()
                    
                    progress = min(80, 30 + (attempts * 50 // max_attempts))
                    pbar.update_absolute(progress)
                    
                    # 根据API文档，/suno/feed 返回clips数组
                    current_clips = []
                    
                    if isinstance(clips_data, list):
                        # 标准格式：直接返回clips数组
                        current_clips = clips_data
                        print(f"[Suno生成器] 轮询 {attempts}: 收到 {len(current_clips)} 个clips")
                    elif isinstance(clips_data, dict):
                        # t8封装格式
                        if clips_data.get("code") == "success":
                            data = clips_data.get("data", [])
                            if isinstance(data, list):
                                current_clips = data
                            elif isinstance(data, dict) and "clips" in data:
                                current_clips = data["clips"]
                        print(f"[Suno生成器] 轮询 {attempts}: 解析得到 {len(current_clips)} 个clips")
                    
                    # 找出已完成的clips
                    complete_clips = []
                    for clip in current_clips:
                        if not isinstance(clip, dict):
                            continue
                        
                        clip_status = clip.get("status", "").lower()
                        audio_url = (clip.get("audio_url") or 
                                   clip.get("audioUrl") or 
                                   clip.get("url") or 
                                   clip.get("mp3_url") or 
                                   clip.get("audio"))
                        
                        print(f"[Suno生成器] Clip {clip.get('id', 'unknown')}: status={clip_status}, has_url={bool(audio_url)}")
                        
                        # 检查clip是否完成
                        if clip_status in ["complete", "completed"]:
                            if audio_url:
                                complete_clips.append(clip)
                                print(f"[Suno生成器] ✓ Clip完成: {clip.get('id')}, URL: {audio_url}")
                        elif clip_status == "streaming":
                            if audio_url:
                                print(f"[Suno生成器] ⏳ Clip流式生成中: {clip.get('id')}, URL可用但仍在生成...")
                        elif clip_status in ["error", "failed"]:
                            print(f"!!! [Suno生成器] Clip失败: {clip.get('id')}")
                    
                    for clip in complete_clips:
                        # 如果有clip_ids，检查是否匹配；否则直接添加
                        clip_id = clip.get("id", "")
                        should_add = False
                        
                        if clip_ids:
                            # 有特定的clip_ids要查找
                            should_add = clip_id in clip_ids
                        else:
                            # 没有特定clip_ids，添加所有完成的clips
                            should_add = True
                        
                        if should_add and clip not in final_clips:
                            final_clips.append(clip)
                            if not generated_prompt and "prompt" in clip:
                                generated_prompt = clip["prompt"]
                            if not extracted_tags and "tags" in clip:
                                extracted_tags = clip["tags"]
                            if not generated_title and "title" in clip and clip["title"]:
                                generated_title = clip["title"]
                    
                    if len(final_clips) >= 2:
                        break
                        
                except Exception as e:
                    print(f"!!! [Suno生成器] 检查clip状态时出错: {str(e)}")
            
            if len(final_clips) < 2:
                error_message = f"{max_attempts}次尝试后仅收到{len(final_clips)}个完整clip"
                print(f"!!! [Suno生成器] {error_message}")
                
                if not final_clips:
                    empty_audio = create_audio_object("")
                    return (empty_audio, empty_audio, "", "", "", task_id, json.dumps({"error": error_message}, ensure_ascii=False), "", "")
                else:
                    # 如果只有一个clip，复制它作为第二个
                    print(f"[Suno生成器] 只有1个clip，将复制作为第二个音频")
                    final_clips.append(final_clips[0])
            
            # 使用生成的标题或用户提供的标题
            final_title = generated_title if generated_title else title

            # 为每个clip设置标题
            for clip in final_clips:
                if "title" not in clip or not clip["title"]:
                    clip["title"] = final_title
                    
            audio_urls = []
            clip_id_values = []
            
            # 提取音频URL
            for clip in final_clips[:2]:
                audio_url = ""
                
                # 检查多种可能的音频URL字段
                audio_url = (clip.get("audio_url") or 
                           clip.get("audioUrl") or 
                           clip.get("url") or 
                           clip.get("mp3_url") or 
                           clip.get("audio") or "")
                
                # 如果没有直接的URL字段，尝试在整个clip对象中搜索URL
                if not audio_url:
                    clip_str = str(clip)
                    if "cdn1.suno.ai" in clip_str:
                        match = re.search(r'https://cdn1\.suno\.ai/[^"\']+\.mp3', clip_str)
                        if match:
                            audio_url = match.group(0)
                
                if audio_url:
                    print(f"[Suno生成器] 找到音频URL: {audio_url}")
                    audio_urls.append(audio_url)
                else:
                    print(f"[Suno生成器] 未在clip中找到音频URL: {json.dumps(clip, ensure_ascii=False)}")
                    audio_urls.append("")
                    
                clip_id_value = clip.get("id", "")
                if clip_id_value:
                    clip_id_values.append(clip_id_value)
                else:
                    clip_id_values.append("")
                
            # 确保有两个URL
            while len(audio_urls) < 2:
                audio_urls.append("")
                
            while len(clip_id_values) < 2:
                clip_id_values.append("")
            
            # 创建音频对象
            pbar.update_absolute(90)
            print("[Suno生成器] 下载并处理音频文件...")
            
            # 使用try-except分别处理每个音频，确保即使一个失败也不影响另一个
            audio_objects = []
            for i, url in enumerate(audio_urls[:2]):
                try:
                    audio_obj = create_audio_object(url, max_duration_seconds=max_duration)
                    # 验证音频对象
                    wf = audio_obj["waveform"]
                    assert len(wf.shape) == 3, f"音频{i+1}波形必须是3D，当前: {wf.shape}"
                    print(f"[Suno生成器] 音频{i+1}对象验证通过: {wf.shape}")
                    audio_objects.append(audio_obj)
                except Exception as e:
                    print(f"!!! [Suno生成器] 创建音频对象{i+1}失败: {e}")
                    # 创建安全的空音频对象
                    sample_rate = 16000
                    waveform = torch.zeros((1, 1, int(sample_rate * max_duration)), dtype=torch.float32)  # 3D [batch, channels, samples]
                    audio_objects.append({
                        "waveform": waveform,
                        "sample_rate": sample_rate
                    })
            
            # 确保有两个音频对象
            while len(audio_objects) < 2:
                sample_rate = 16000
                waveform = torch.zeros((1, 1, int(sample_rate * max_duration)), dtype=torch.float32)  # 3D [batch, channels, samples]
                audio_objects.append({
                    "waveform": waveform,
                    "sample_rate": sample_rate
                })
            
            pbar.update_absolute(100)
            
            response_info = {
                "status": "success",
                "task_type": task_type,
                "prompt": generated_prompt,
                "title": final_title, 
                "model": mv,
                "generation_type": generation_type,
                "seed": seed if seed > 0 else "auto",
                "make_instrumental": make_instrumental,
                "custom_mode": custom_mode,
                "vocal_gender": vocal_gender,
                "style_weight": style_weight,
                "weirdness_constraint": weirdness_constraint,
                "clips_generated": len(final_clips),
                "tags": extracted_tags,
                "use_reference_audio": bool(reference_audio_url.strip()),
                "task_id_input": task_id,
                "continue_at": continue_at,
                "continue_clip_id": continue_clip_id,
                "cover_clip_id": cover_clip_id
            }

            return (
                audio_objects[0],
                audio_objects[1],
                audio_urls[0],
                audio_urls[1],
                generated_prompt,
                task_id,
                json.dumps(response_info, ensure_ascii=False),
                clip_id_values[0],
                final_title
            )
                
        except Exception as e:
            error_message = f"生成音乐时出错: {str(e)}"
            print(f"!!! [Suno生成器] {error_message}")
            empty_audio = create_audio_object("", max_duration_seconds=max_duration)
            return (empty_audio, empty_audio, "", "", "", "", json.dumps({"error": error_message}, ensure_ascii=False), "", "")




# 导出节点类
NODE_CLASS_MAPPINGS = {
    "SunoGenerator": SunoGeneratorNode,
}

# 节点显示名称映射
NODE_DISPLAY_NAME_MAPPINGS = {
    "SunoGenerator": "Suno音乐生成器",
}