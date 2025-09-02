#!/bin/bash

#
# Immich模型预下载脚本
# 使用HuggingFace中国镜像站加速下载
#

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
MODELS_DIR="./models"
HF_ENDPOINT="https://hf-mirror.com"

# 需要下载的模型列表
declare -A MODELS=(
    ["buffalo_l"]="buffalo_l"
    ["ViT-B-32"]="openai/clip-vit-base-patch32"
)

echo -e "${BLUE}=== Immich模型预下载工具 ===${NC}"
echo -e "${YELLOW}使用HuggingFace中国镜像站: ${HF_ENDPOINT}${NC}"
echo ""

# 检查依赖
check_dependencies() {
    echo -e "${BLUE}检查依赖...${NC}"
    
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}错误: 未找到python3${NC}"
        exit 1
    fi
    
    if ! python3 -c "import huggingface_hub" &> /dev/null; then
        echo -e "${YELLOW}安装huggingface_hub...${NC}"
        pip3 install huggingface_hub
    fi
    
    echo -e "${GREEN}依赖检查完成${NC}"
}

# 创建模型目录
prepare_directories() {
    echo -e "${BLUE}准备目录结构...${NC}"
    
    # 清理旧的模型目录
    if [ -d "$MODELS_DIR" ]; then
        echo -e "${YELLOW}清理旧的模型目录...${NC}"
        rm -rf "$MODELS_DIR"
    fi
    
    # 创建新的模型目录
    mkdir -p "$MODELS_DIR"
    
    echo -e "${GREEN}目录准备完成${NC}"
}

# 下载单个模型
download_model() {
    local model_name=$1
    local model_repo=$2
    
    echo -e "${BLUE}下载模型: ${model_name} (${model_repo})${NC}"
    
    # 设置环境变量
    export HF_ENDPOINT="$HF_ENDPOINT"
    
    # 使用Python脚本下载模型
    python3 << EOF
import os
from huggingface_hub import snapshot_download
import shutil

try:
    # 下载模型到临时目录
    cache_dir = snapshot_download(
        repo_id="$model_repo",
        cache_dir="$MODELS_DIR/temp",
        local_files_only=False
    )
    
    # 复制到目标目录
    target_dir = "$MODELS_DIR/$model_name"
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    
    shutil.copytree(cache_dir, target_dir)
    print(f"✅ 模型 $model_name 下载完成")
    
except Exception as e:
    print(f"❌ 模型 $model_name 下载失败: {e}")
    exit(1)
EOF
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ ${model_name} 下载成功${NC}"
    else
        echo -e "${RED}❌ ${model_name} 下载失败${NC}"
        exit 1
    fi
}

# 验证模型文件
verify_models() {
    echo -e "${BLUE}验证模型文件...${NC}"
    
    for model_name in "${!MODELS[@]}"; do
        model_dir="$MODELS_DIR/$model_name"
        if [ -d "$model_dir" ]; then
            size=$(du -sh "$model_dir" | cut -f1)
            echo -e "${GREEN}✅ ${model_name}: ${size}${NC}"
        else
            echo -e "${RED}❌ ${model_name}: 未找到${NC}"
        fi
    done
}

# 清理临时文件
cleanup() {
    echo -e "${BLUE}清理临时文件...${NC}"
    
    if [ -d "$MODELS_DIR/temp" ]; then
        rm -rf "$MODELS_DIR/temp"
    fi
    
    echo -e "${GREEN}清理完成${NC}"
}

# 主函数
main() {
    echo -e "${BLUE}开始下载Immich所需模型...${NC}"
    echo ""
    
    check_dependencies
    prepare_directories
    
    # 下载所有模型
    for model_name in "${!MODELS[@]}"; do
        model_repo="${MODELS[$model_name]}"
        download_model "$model_name" "$model_repo"
        echo ""
    done
    
    cleanup
    verify_models
    
    echo ""
    echo -e "${GREEN}=== 模型下载完成 ===${NC}"
    echo -e "${YELLOW}现在可以运行: docker-compose -f docker-compose.optimized.yml up -d${NC}"
}

# 运行主函数
main "$@"
