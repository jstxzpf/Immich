#!/bin/bash

#
# Immich优化部署自动化脚本
# 集成模型下载和容器部署
#

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
COMPOSE_FILE="docker-compose.optimized.yml"
MODELS_DIR="./models"

echo -e "${BLUE}=== Immich优化部署工具 ===${NC}"
echo -e "${YELLOW}自动化模型下载和容器部署${NC}"
echo ""

# 检查当前目录
check_directory() {
    if [ ! -f "docker-compose.yml" ]; then
        echo -e "${RED}错误: 请在docker目录中运行此脚本${NC}"
        exit 1
    fi
}

# 停止现有服务
stop_existing_services() {
    echo -e "${BLUE}停止现有服务...${NC}"
    
    if docker compose ps | grep -q "Up"; then
        echo -e "${YELLOW}发现运行中的服务，正在停止...${NC}"
        docker compose down
    fi

    if docker compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        echo -e "${YELLOW}发现优化版本服务，正在停止...${NC}"
        docker compose -f "$COMPOSE_FILE" down
    fi
    
    echo -e "${GREEN}✅ 服务停止完成${NC}"
}

# 下载模型（暂时跳过，使用现有Docker volume）
download_models() {
    echo -e "${BLUE}检查模型配置...${NC}"

    echo -e "${YELLOW}当前使用Docker volume中的现有模型${NC}"
    echo -e "${YELLOW}如需使用本地模型目录，请手动修改docker-compose.optimized.yml${NC}"

    echo -e "${GREEN}✅ 模型配置检查完成${NC}"
}

# 验证模型文件（跳过本地验证）
verify_models() {
    echo -e "${BLUE}验证模型配置...${NC}"

    echo -e "${YELLOW}使用Docker volume中的模型，跳过本地验证${NC}"
    echo -e "${GREEN}✅ 模型配置验证完成${NC}"

    return 0
}

# 设置权限（跳过本地目录权限设置）
set_permissions() {
    echo -e "${BLUE}检查权限配置...${NC}"

    echo -e "${YELLOW}使用Docker volume，跳过本地权限设置${NC}"
    echo -e "${GREEN}✅ 权限检查完成${NC}"
}

# 启动优化服务
start_optimized_services() {
    echo -e "${BLUE}启动优化版本服务...${NC}"
    
    # 拉取最新镜像
    echo -e "${YELLOW}拉取容器镜像...${NC}"
    docker compose -f "$COMPOSE_FILE" pull

    # 启动服务
    docker compose -f "$COMPOSE_FILE" up -d
    
    echo -e "${GREEN}✅ 服务启动完成${NC}"
}

# 验证服务状态
verify_services() {
    echo -e "${BLUE}验证服务状态...${NC}"
    
    # 等待服务启动
    echo -e "${YELLOW}等待服务启动...${NC}"
    sleep 10
    
    # 检查容器状态
    if ! docker compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        echo -e "${RED}❌ 部分服务未正常启动${NC}"
        echo -e "${YELLOW}查看日志:${NC}"
        docker compose -f "$COMPOSE_FILE" logs --tail=20
        return 1
    fi

    # 检查机器学习服务日志
    echo -e "${YELLOW}检查机器学习服务日志...${NC}"
    ml_logs=$(docker compose -f "$COMPOSE_FILE" logs immich-machine-learning --tail=10)
    
    if echo "$ml_logs" | grep -q "ERROR\|FAILED\|Exception"; then
        echo -e "${RED}❌ 机器学习服务可能存在问题${NC}"
        echo "$ml_logs"
        return 1
    fi
    
    echo -e "${GREEN}✅ 所有服务运行正常${NC}"
    return 0
}

# 显示部署信息
show_deployment_info() {
    echo ""
    echo -e "${GREEN}=== 部署完成 ===${NC}"
    echo -e "${BLUE}服务信息:${NC}"
    echo -e "  Web界面: ${YELLOW}http://10.132.60.111:2283${NC}"
    echo -e "  管理员账户: ${YELLOW}jszpf@qq.com${NC}"
    echo -e "  外部照片: ${YELLOW}/data/cleanjpg (23,624张)${NC}"
    echo ""
    echo -e "${BLUE}常用命令:${NC}"
    echo -e "  查看状态: ${YELLOW}docker compose -f $COMPOSE_FILE ps${NC}"
    echo -e "  查看日志: ${YELLOW}docker compose -f $COMPOSE_FILE logs -f${NC}"
    echo -e "  停止服务: ${YELLOW}docker compose -f $COMPOSE_FILE down${NC}"
    echo ""
}

# 主函数
main() {
    check_directory
    
    echo -e "${BLUE}开始优化部署流程...${NC}"
    echo ""
    
    # 执行部署步骤
    stop_existing_services
    echo ""
    
    download_models
    echo ""
    
    if ! verify_models; then
        echo -e "${RED}模型验证失败，请检查下载过程${NC}"
        exit 1
    fi
    echo ""
    
    set_permissions
    echo ""
    
    start_optimized_services
    echo ""
    
    if verify_services; then
        show_deployment_info
    else
        echo -e "${RED}服务验证失败，请检查日志${NC}"
        echo -e "${YELLOW}运行以下命令查看详细日志:${NC}"
        echo -e "docker compose -f $COMPOSE_FILE logs"
        exit 1
    fi
}

# 处理中断信号
trap 'echo -e "\n${YELLOW}部署被中断${NC}"; exit 1' INT TERM

# 运行主函数
main "$@"
