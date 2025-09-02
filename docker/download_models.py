#!/usr/bin/env python3
"""
Immich模型下载工具
使用HuggingFace中国镜像站加速下载
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# 配置
MODELS_DIR = Path("./models")
HF_ENDPOINT = "https://hf-mirror.com"

# 需要下载的模型
MODELS = {
    "buffalo_l": "public-data/buffalo_l",
    "ViT-B-32": "openai/clip-vit-base-patch32"
}

def print_colored(text, color=""):
    """打印彩色文本"""
    colors = {
        "red": "\033[0;31m",
        "green": "\033[0;32m", 
        "yellow": "\033[1;33m",
        "blue": "\033[0;34m",
        "reset": "\033[0m"
    }
    
    if color in colors:
        print(f"{colors[color]}{text}{colors['reset']}")
    else:
        print(text)

def check_dependencies():
    """检查依赖"""
    print_colored("检查依赖...", "blue")
    
    try:
        import huggingface_hub
        print_colored("✅ huggingface_hub 已安装", "green")
    except ImportError:
        print_colored("安装 huggingface_hub...", "yellow")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "huggingface_hub"])
        import huggingface_hub

def prepare_directories():
    """准备目录结构"""
    print_colored("准备目录结构...", "blue")
    
    if MODELS_DIR.exists():
        print_colored("清理旧的模型目录...", "yellow")
        shutil.rmtree(MODELS_DIR)
    
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print_colored("✅ 目录准备完成", "green")

def download_model(model_name, model_repo):
    """下载单个模型"""
    print_colored(f"下载模型: {model_name} ({model_repo})", "blue")
    
    # 设置环境变量
    os.environ["HF_ENDPOINT"] = HF_ENDPOINT
    
    try:
        from huggingface_hub import snapshot_download
        
        # 下载模型
        cache_dir = snapshot_download(
            repo_id=model_repo,
            cache_dir=str(MODELS_DIR / "temp"),
            local_files_only=False
        )
        
        # 复制到目标目录
        target_dir = MODELS_DIR / model_name
        if target_dir.exists():
            shutil.rmtree(target_dir)
        
        shutil.copytree(cache_dir, target_dir)
        print_colored(f"✅ {model_name} 下载完成", "green")
        return True
        
    except Exception as e:
        print_colored(f"❌ {model_name} 下载失败: {e}", "red")
        return False

def verify_models():
    """验证模型文件"""
    print_colored("验证模型文件...", "blue")
    
    for model_name in MODELS.keys():
        model_dir = MODELS_DIR / model_name
        if model_dir.exists():
            # 计算目录大小
            total_size = sum(f.stat().st_size for f in model_dir.rglob('*') if f.is_file())
            size_mb = total_size / (1024 * 1024)
            print_colored(f"✅ {model_name}: {size_mb:.1f}MB", "green")
        else:
            print_colored(f"❌ {model_name}: 未找到", "red")

def cleanup():
    """清理临时文件"""
    print_colored("清理临时文件...", "blue")
    
    temp_dir = MODELS_DIR / "temp"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    
    print_colored("✅ 清理完成", "green")

def main():
    """主函数"""
    print_colored("=== Immich模型预下载工具 ===", "blue")
    print_colored(f"使用HuggingFace中国镜像站: {HF_ENDPOINT}", "yellow")
    print()
    
    try:
        check_dependencies()
        prepare_directories()
        
        # 下载所有模型
        success_count = 0
        for model_name, model_repo in MODELS.items():
            if download_model(model_name, model_repo):
                success_count += 1
            print()
        
        cleanup()
        verify_models()
        
        print()
        if success_count == len(MODELS):
            print_colored("=== 所有模型下载完成 ===", "green")
            print_colored("现在可以运行: docker-compose -f docker-compose.optimized.yml up -d", "yellow")
        else:
            print_colored(f"=== 部分模型下载失败 ({success_count}/{len(MODELS)}) ===", "red")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print_colored("\n用户取消下载", "yellow")
        sys.exit(1)
    except Exception as e:
        print_colored(f"下载过程中出现错误: {e}", "red")
        sys.exit(1)

if __name__ == "__main__":
    main()
