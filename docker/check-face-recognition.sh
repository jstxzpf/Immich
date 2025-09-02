#!/bin/bash

#
# Immich人脸识别进度监控脚本
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

echo -e "${BLUE}=== Immich人脸识别进度监控 ===${NC}"
echo ""

# 查询数据库统计
get_database_stats() {
    echo -e "${BLUE}📊 数据库统计信息${NC}"
    
    # 资产统计
    docker exec immich_postgres psql -U postgres -d immich -c "
    SELECT 
        '总资产数量' as metric,
        COUNT(*) as count
    FROM asset
    UNION ALL
    SELECT 
        '图片数量' as metric,
        COUNT(*) as count
    FROM asset WHERE type = 'IMAGE'
    UNION ALL
    SELECT 
        '视频数量' as metric,
        COUNT(*) as count
    FROM asset WHERE type = 'VIDEO';
    " -t
    
    echo ""
    
    # 人脸统计
    echo -e "${BLUE}👤 人脸识别统计${NC}"
    docker exec immich_postgres psql -U postgres -d immich -c "
    SELECT 
        '检测到的人脸总数' as metric,
        COUNT(*) as count
    FROM asset_face
    UNION ALL
    SELECT 
        '已分配给人物的人脸' as metric,
        COUNT(*) as count
    FROM asset_face WHERE \"personId\" IS NOT NULL
    UNION ALL
    SELECT 
        '未分配的人脸' as metric,
        COUNT(*) as count
    FROM asset_face WHERE \"personId\" IS NULL
    UNION ALL
    SELECT 
        '识别的人物数量' as metric,
        COUNT(DISTINCT \"personId\") as count
    FROM asset_face WHERE \"personId\" IS NOT NULL;
    " -t
    
    echo ""
    
    # 人物统计
    echo -e "${BLUE}🏷️  人物标签统计${NC}"
    docker exec immich_postgres psql -U postgres -d immich -c "
    SELECT 
        '创建的人物档案' as metric,
        COUNT(*) as count
    FROM person
    UNION ALL
    SELECT 
        '已命名的人物' as metric,
        COUNT(*) as count
    FROM person WHERE name IS NOT NULL AND name != ''
    UNION ALL
    SELECT 
        '未命名的人物' as metric,
        COUNT(*) as count
    FROM person WHERE name IS NULL OR name = '';
    " -t
}

# 查看作业状态
check_job_status() {
    echo -e "${BLUE}⚙️  机器学习服务状态${NC}"
    
    # 检查容器状态
    if docker compose -f "$COMPOSE_FILE" ps immich-machine-learning | grep -q "Up"; then
        echo -e "${GREEN}✅ 机器学习服务运行正常${NC}"
    else
        echo -e "${RED}❌ 机器学习服务未运行${NC}"
        return 1
    fi
    
    # 检查最近的日志
    echo -e "${YELLOW}最近的机器学习服务日志:${NC}"
    docker compose -f "$COMPOSE_FILE" logs immich-machine-learning --tail=5 | sed 's/^/  /'
    
    echo ""
}

# 显示处理进度
show_progress() {
    echo -e "${BLUE}📈 处理进度分析${NC}"
    
    # 获取统计数据
    local total_images=$(docker exec immich_postgres psql -U postgres -d immich -c "SELECT COUNT(*) FROM asset WHERE type = 'IMAGE';" -t | tr -d ' ')
    local total_faces=$(docker exec immich_postgres psql -U postgres -d immich -c "SELECT COUNT(*) FROM asset_face;" -t | tr -d ' ')
    local assigned_faces=$(docker exec immich_postgres psql -U postgres -d immich -c "SELECT COUNT(*) FROM asset_face WHERE \"personId\" IS NOT NULL;" -t | tr -d ' ')
    
    echo "  总图片数量: $total_images"
    echo "  检测到的人脸: $total_faces"
    
    if [ "$total_images" -gt 0 ] && [ "$total_faces" -gt 0 ]; then
        local progress=$(echo "scale=2; $total_faces * 100 / $total_images" | bc -l 2>/dev/null || echo "0")
        echo "  平均每张图片人脸数: $(echo "scale=2; $total_faces / $total_images" | bc -l 2>/dev/null || echo "0")"
        
        if [ "$total_faces" -gt 0 ]; then
            local assignment_rate=$(echo "scale=2; $assigned_faces * 100 / $total_faces" | bc -l 2>/dev/null || echo "0")
            echo "  人脸分配率: ${assignment_rate}%"
        fi
    fi
    
    echo ""
}

# 显示使用建议
show_recommendations() {
    local total_faces=$(docker exec immich_postgres psql -U postgres -d immich -c "SELECT COUNT(*) FROM asset_face WHERE \"deletedAt\" IS NULL;" -t | tr -d ' ')
    local total_persons=$(docker exec immich_postgres psql -U postgres -d immich -c "SELECT COUNT(*) FROM person;" -t | tr -d ' ')

    echo -e "${BLUE}💡 使用建议${NC}"

    if [ "$total_faces" -eq 0 ]; then
        echo -e "${YELLOW}🔄 还没有检测到人脸，建议:${NC}"
        echo "  1. 在Web界面进入管理面板 → 作业"
        echo "  2. 找到'人脸检测'作业并点击'运行所有'"
        echo "  3. 等待处理完成（可能需要几小时）"
    elif [ "$total_persons" -eq 0 ]; then
        echo -e "${YELLOW}🔄 人脸检测完成，但需要启动人脸聚类:${NC}"
        echo "  1. 在Web界面进入管理面板 → 作业"
        echo "  2. 找到'人脸聚类'作业并点击'运行所有'"
        echo "  3. 或者运行: python3 trigger-face-clustering.py"
        echo "  4. 聚类完成后，'探索 → 人物'页面才会显示内容"
    elif [ "$total_faces" -lt 1000 ]; then
        echo -e "${YELLOW}🚀 人脸检测进行中，建议:${NC}"
        echo "  1. 耐心等待检测完成"
        echo "  2. 可以定期运行此脚本查看进度"
        echo "  3. 检测完成后需要启动人脸聚类作业"
    else
        echo -e "${GREEN}🎉 人脸检测已有结果，建议:${NC}"
        echo "  1. 访问Web界面的'探索 → 人物'页面"
        echo "  2. 为识别的人脸添加姓名标签"
        echo "  3. 使用搜索功能按人名查找照片"
    fi

    echo ""
    echo -e "${BLUE}🌐 Web界面访问:${NC}"
    echo "  URL: http://10.132.60.111:2283"
    echo "  管理员: jszpf@qq.com"
}

# 主函数
main() {
    get_database_stats
    check_job_status
    show_progress
    show_recommendations
    
    echo -e "${GREEN}监控完成！${NC}"
    echo -e "${YELLOW}提示: 可以定期运行此脚本查看最新进度${NC}"
}

# 运行主函数
main "$@"
