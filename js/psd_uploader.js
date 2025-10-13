import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// PSD文件上传功能
app.registerExtension({
    name: "AFA.PSDUploader",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "ImportPSD") {
            // 添加文件上传功能到ImportPSDNode
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                
                // 隐藏PSD文件的文字输入框
                setTimeout(() => {
                    const psdWidget = this.widgets.find(w => w.name === "PSD文件");
                    if (psdWidget) {
                        psdWidget.type = "hidden";
                        psdWidget.computeSize = () => [0, 0];
                        psdWidget.draw = () => {};
                    }
                }, 100);
                
                // 创建文件上传控件
                this.addWidget("button", "选择PSD文件", "upload", () => {
                    this.uploadPSDFile();
                });
                
                // 添加文件名显示
                this.addWidget("text", "已选择文件", "", function(v) {}, {
                    readonly: true,
                    serialize: false
                });
                
                return r;
            };
            
            // 添加PSD文件上传方法
            nodeType.prototype.uploadPSDFile = function() {
                const input = document.createElement("input");
                input.type = "file";
                input.accept = ".psd";
                input.style.display = "none";
                document.body.appendChild(input);
                
                input.onchange = async (e) => {
                    const file = e.target.files[0];
                    if (file) {
                        try {
                            // 显示上传进度
                            const statusWidget = this.widgets.find(w => w.name === "已选择文件");
                            if (statusWidget) {
                                statusWidget.value = "正在上传...";
                            }
                            
                            // 创建FormData
                            const formData = new FormData();
                            formData.append("image", file);
                            formData.append("type", "input");
                            formData.append("subfolder", "psd");
                            
                            // 上传文件到ComfyUI
                            const response = await api.fetchApi("/upload/image", {
                                method: "POST",
                                body: formData,
                            });
                            
                            if (response.status === 200) {
                                const result = await response.json();
                                const filename = result.name;
                                
                                // 找到PSD文件的widget并设置值
                                const psdWidget = this.widgets.find(w => w.name === "PSD文件");
                                const statusWidget = this.widgets.find(w => w.name === "已选择文件");
                                
                                if (psdWidget) {
                                    psdWidget.value = filename;
                                }
                                if (statusWidget) {
                                    statusWidget.value = `已选择: ${file.name}`;
                                }
                                
                                // 触发节点更新
                                if (this.onWidgetChanged && psdWidget) {
                                    this.onWidgetChanged("PSD文件", filename, psdWidget.value, psdWidget);
                                }
                                
                                console.log("PSD文件上传成功:", filename);
                            } else {
                                throw new Error(`上传失败: ${response.status}`);
                            }
                        } catch (error) {
                            console.error("PSD文件上传失败:", error);
                            const statusWidget = this.widgets.find(w => w.name === "已选择文件");
                            if (statusWidget) {
                                statusWidget.value = `上传失败: ${error.message}`;
                            }
                        }
                    }
                    document.body.removeChild(input);
                };
                
                input.click();
            };
            
            // 修改输入类型定义
            const getExtraMenuOptions = nodeType.prototype.getExtraMenuOptions;
            nodeType.prototype.getExtraMenuOptions = function(_, options) {
                const r = getExtraMenuOptions ? getExtraMenuOptions.apply(this, arguments) : undefined;
                
                options.push({
                    content: "上传PSD文件",
                    callback: () => {
                        this.uploadPSDFile();
                    }
                });
                
                return r;
            };
        }
    }
});

// 扩展ComfyUI的文件处理以支持PSD文件
const originalHandleFile = app.handleFile;
app.handleFile = function(file) {
    if (file.name.toLowerCase().endsWith('.psd')) {
        // 处理拖拽的PSD文件
        const formData = new FormData();
        formData.append("image", file);
        formData.append("type", "input");
        formData.append("subfolder", "psd");
        
        api.fetchApi("/upload/image", {
            method: "POST",
            body: formData,
        }).then(async (response) => {
            if (response.status === 200) {
                const result = await response.json();
                console.log("PSD文件拖拽上传成功:", result.name);
                
                // 可以在这里添加自动创建ImportPSDNode的逻辑
                // 或者显示通知告诉用户文件已上传
                app.ui.dialog.show(`PSD文件已上传: ${result.name}`);
            } else {
                console.error("PSD文件拖拽上传失败");
                app.ui.dialog.show("PSD文件上传失败");
            }
        }).catch((error) => {
            console.error("PSD文件拖拽上传错误:", error);
            app.ui.dialog.show(`PSD文件上传错误: ${error.message}`);
        });
        
        return true; // 表示我们已处理此文件
    }
    
    // 对于非PSD文件，使用原始处理方法
    return originalHandleFile ? originalHandleFile.call(this, file) : false;
};