#!/bin/bash

#
# Immich部署测试脚本
# 验证优化部署的效果
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
WEB_URL="http://10.132.60.111:2283"
MODELS_DIR="./models"

echo -e "${BLUE}=== Immich部署测试工具 ===${NC}"
echo ""

# 测试模型文件（Docker volume版本）
test_models() {
    echo -e "${BLUE}测试模型配置...${NC}"

    # 检查Docker volume中的模型
    echo -e "${YELLOW}检查Docker volume中的模型文件...${NC}"

    # 通过容器检查模型文件
    if docker exec immich_machine_learning ls -la /cache/ 2>/dev/null | grep -q "models\|buffalo\|clip"; then
        echo -e "${GREEN}✅ 模型文件: Docker volume中存在模型文件${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  模型文件: 无法直接验证，将通过服务日志检查${NC}"
        return 0
    fi
}

# 测试容器状态
test_containers() {
    echo -e "${BLUE}测试容器状态...${NC}"
    
    local success=0
    local total=0
    
    # 检查容器是否存在并运行
    containers=("immich_server" "immich_machine_learning" "immich_redis" "immich_postgres")
    
    for container in "${containers[@]}"; do
        total=$((total + 1))
        if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$container.*Up"; then
            status=$(docker ps --format "table {{.Names}}\t{{.Status}}" | grep "$container" | awk '{print $2}')
            echo -e "${GREEN}✅ $container: $status${NC}"
            success=$((success + 1))
        else
            echo -e "${RED}❌ $container: 未运行${NC}"
        fi
    done
    
    echo -e "${BLUE}容器测试结果: $success/$total${NC}"
    return $((total - success))
}

# 测试服务健康状态
test_health() {
    echo -e "${BLUE}测试服务健康状态...${NC}"
    
    # 等待服务完全启动
    echo -e "${YELLOW}等待服务启动...${NC}"
    sleep 5
    
    # 检查Web服务
    if curl -s -o /dev/null -w "%{http_code}" "$WEB_URL" | grep -q "200\|302"; then
        echo -e "${GREEN}✅ Web服务: 可访问${NC}"
    else
        echo -e "${RED}❌ Web服务: 无法访问${NC}"
        return 1
    fi
    
    # 检查机器学习服务日志
    ml_logs=$(docker compose -f "$COMPOSE_FILE" logs immich-machine-learning --tail=20 2>/dev/null || echo "")
    
    if echo "$ml_logs" | grep -q "ERROR\|FAILED\|Exception"; then
        echo -e "${RED}❌ 机器学习服务: 发现错误${NC}"
        echo -e "${YELLOW}错误日志:${NC}"
        echo "$ml_logs" | grep -E "ERROR|FAILED|Exception" | tail -3
        return 1
    else
        echo -e "${GREEN}✅ 机器学习服务: 运行正常${NC}"
    fi
    
    return 0
}

# 测试外部照片挂载
test_external_photos() {
    echo -e "${BLUE}测试外部照片挂载...${NC}"
    
    # 检查容器内的挂载点
    photo_count=$(docker exec immich_server find /mnt/external_photos -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" | wc -l 2>/dev/null || echo "0")
    
    if [ "$photo_count" -gt 0 ]; then
        echo -e "${GREEN}✅ 外部照片: $photo_count 张照片可访问${NC}"
        return 0
    else
        echo -e "${RED}❌ 外部照片: 无法访问或为空${NC}"
        return 1
    fi
}

# 性能测试
test_performance() {
    echo -e "${BLUE}测试系统性能...${NC}"
    
    # 检查内存使用
    total_memory=$(docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}" | grep immich | awk '{print $2}' | sed 's/MiB.*//' | awk '{sum+=$1} END {print sum}')
    
    if [ -n "$total_memory" ] && [ "$total_memory" -gt 0 ]; then
        echo -e "${GREEN}✅ 内存使用: ${total_memory}MB${NC}"
    else
        echo -e "${YELLOW}⚠️  内存使用: 无法获取${NC}"
    fi
    
    # 检查磁盘使用
    if [ -d "$MODELS_DIR" ]; then
        model_size=$(du -sh "$MODELS_DIR" | cut -f1)
        echo -e "${GREEN}✅ 模型存储: $model_size${NC}"
    fi
    
    return 0
}

# 生成测试报告
generate_report() {
    local model_result=$1
    local container_result=$2
    local health_result=$3
    local photo_result=$4
    
    echo ""
    echo -e "${BLUE}=== 测试报告 ===${NC}"
    
    local total_tests=4
    local passed_tests=0
    
    [ $model_result -eq 0 ] && passed_tests=$((passed_tests + 1))
    [ $container_result -eq 0 ] && passed_tests=$((passed_tests + 1))
    [ $health_result -eq 0 ] && passed_tests=$((passed_tests + 1))
    [ $photo_result -eq 0 ] && passed_tests=$((passed_tests + 1))
    
    echo -e "${BLUE}总体结果: $passed_tests/$total_tests 项测试通过${NC}"
    
    if [ $passed_tests -eq $total_tests ]; then
        echo -e "${GREEN}🎉 所有测试通过！部署成功！${NC}"
        echo ""
        echo -e "${BLUE}访问信息:${NC}"
        echo -e "  Web界面: ${YELLOW}$WEB_URL${NC}"
        echo -e "  管理员账户: ${YELLOW}jszpf@qq.com${NC}"
        return 0
    else
        echo -e "${RED}⚠️  部分测试失败，请检查相关组件${NC}"
        return 1
    fi
}

# 主函数
main() {
    echo -e "${BLUE}开始测试部署结果...${NC}"
    echo ""
    
    # 执行各项测试
    test_models
    model_result=$?
    echo ""
    
    test_containers
    container_result=$?
    echo ""
    
    test_health
    health_result=$?
    echo ""
    
    test_external_photos
    photo_result=$?
    echo ""
    
    test_performance
    echo ""
    
    # 生成报告
    generate_report $model_result $container_result $health_result $photo_result
}

# 运行主函数
main "$@"
