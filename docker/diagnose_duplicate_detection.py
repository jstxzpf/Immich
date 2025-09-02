#!/usr/bin/env python3
"""
诊断Immich重复检测问题的脚本
分析为什么相似照片未被检测为重复
"""

import subprocess
import json
from datetime import datetime

def query_database(sql):
    """执行数据库查询"""
    try:
        result = subprocess.run([
            'docker', 'exec', 'immich_postgres', 
            'psql', '-U', 'postgres', '-d', 'immich', 
            '-c', sql, '-t', '--csv'
        ], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"数据库查询失败: {e}")
        return None

def check_duplicate_detection_prerequisites():
    """检查重复检测的前置条件"""
    print("🔍 检查重复检测前置条件...")
    
    # 1. 检查智能搜索是否启用
    print("\n1. 检查智能搜索配置:")
    sql = """
    SELECT key, value 
    FROM system_metadata 
    WHERE key LIKE '%machineLearning%' 
       OR key LIKE '%clip%' 
       OR key LIKE '%duplicateDetection%'
    ORDER BY key;
    """
    
    result = query_database(sql)
    if result:
        print("系统配置:")
        for line in result.split('\n'):
            if line.strip():
                parts = line.split(',', 1)
                if len(parts) >= 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    print(f"  {key}: {value}")
    
    # 2. 检查有多少图片已生成嵌入向量
    print("\n2. 检查图片嵌入向量生成情况:")
    sql = """
    SELECT 
        COUNT(*) as total_images,
        COUNT(ss.embedding) as images_with_embedding,
        ROUND(COUNT(ss.embedding)::numeric / COUNT(*) * 100, 2) as embedding_percentage
    FROM asset a
    LEFT JOIN smart_search ss ON a.id = ss."assetId"
    WHERE a.type = 'IMAGE' AND a."deletedAt" IS NULL;
    """
    
    result = query_database(sql)
    if result:
        parts = result.split(',')
        if len(parts) >= 3:
            total = parts[0].strip()
            with_embedding = parts[1].strip()
            percentage = parts[2].strip()
            print(f"  总图片数: {total}")
            print(f"  已生成嵌入向量: {with_embedding}")
            print(f"  嵌入向量覆盖率: {percentage}%")
            
            if float(percentage) < 100:
                print("  ⚠️  部分图片缺少嵌入向量，需要运行智能搜索作业")

def check_specific_photos():
    """检查特定照片的情况"""
    print("\n3. 检查特定照片情况:")
    
    # 查找用户提到的照片
    photo_patterns = ['f4081644432_1.jpg', 'f4081637024_1.jpg']
    
    for pattern in photo_patterns:
        print(f"\n检查照片: {pattern}")
        sql = f"""
        SELECT 
            a.id,
            a."originalFileName",
            a."duplicateId",
            CASE WHEN ss.embedding IS NOT NULL THEN 'YES' ELSE 'NO' END as has_embedding,
            a."stackId",
            a.visibility,
            a."deletedAt"
        FROM asset a
        LEFT JOIN smart_search ss ON a.id = ss."assetId"
        WHERE a."originalFileName" LIKE '%{pattern.replace('_1.jpg', '%')}%'
           OR a."originalFileName" = '{pattern}'
        ORDER BY a."originalFileName";
        """
        
        result = query_database(sql)
        if result:
            print("  找到匹配的照片:")
            print("  ID | 文件名 | 重复ID | 有嵌入 | 堆叠ID | 可见性 | 删除时间")
            print("  " + "-" * 80)
            for line in result.split('\n'):
                if line.strip():
                    parts = line.split(',')
                    if len(parts) >= 6:
                        print(f"  {' | '.join(parts)}")
        else:
            print(f"  未找到匹配 {pattern} 的照片")

def check_duplicate_detection_jobs():
    """检查重复检测作业状态"""
    print("\n4. 检查重复检测作业状态:")
    
    sql = """
    SELECT 
        "assetId",
        "duplicatesDetectedAt"
    FROM asset_job_status 
    WHERE "duplicatesDetectedAt" IS NOT NULL
    ORDER BY "duplicatesDetectedAt" DESC
    LIMIT 10;
    """
    
    result = query_database(sql)
    if result and result.strip():
        print("  最近的重复检测记录:")
        print("  资产ID | 检测时间")
        print("  " + "-" * 50)
        for line in result.split('\n'):
            if line.strip():
                parts = line.split(',')
                if len(parts) >= 2:
                    print(f"  {parts[0]} | {parts[1]}")
    else:
        print("  ⚠️  没有找到重复检测作业记录")
        print("  可能需要手动运行重复检测作业")

def check_existing_duplicates():
    """检查现有的重复检测结果"""
    print("\n5. 检查现有重复检测结果:")
    
    sql = """
    SELECT 
        "duplicateId",
        COUNT(*) as duplicate_count,
        STRING_AGG("originalFileName", ', ') as filenames
    FROM asset 
    WHERE "duplicateId" IS NOT NULL 
      AND "deletedAt" IS NULL
    GROUP BY "duplicateId"
    ORDER BY duplicate_count DESC
    LIMIT 10;
    """
    
    result = query_database(sql)
    if result and result.strip():
        print("  现有重复组:")
        print("  重复ID | 数量 | 文件名")
        print("  " + "-" * 80)
        for line in result.split('\n'):
            if line.strip():
                parts = line.split(',', 2)
                if len(parts) >= 3:
                    print(f"  {parts[0]} | {parts[1]} | {parts[2][:60]}...")
    else:
        print("  📭 当前没有检测到任何重复照片")

def analyze_embedding_similarity():
    """分析嵌入向量相似度"""
    print("\n6. 分析嵌入向量相似度:")
    
    # 查找可能相似的照片对
    sql = """
    WITH photo_pairs AS (
        SELECT 
            a1.id as id1,
            a1."originalFileName" as file1,
            a2.id as id2,
            a2."originalFileName" as file2,
            ss1.embedding <=> ss2.embedding as distance
        FROM asset a1
        JOIN smart_search ss1 ON a1.id = ss1."assetId"
        JOIN asset a2 ON a1.id < a2.id
        JOIN smart_search ss2 ON a2.id = ss2."assetId"
        WHERE a1.type = 'IMAGE' 
          AND a2.type = 'IMAGE'
          AND a1."deletedAt" IS NULL 
          AND a2."deletedAt" IS NULL
          AND a1."ownerId" = a2."ownerId"
          AND (a1."originalFileName" LIKE '%f4081644432%' OR a1."originalFileName" LIKE '%f4081637024%'
               OR a2."originalFileName" LIKE '%f4081644432%' OR a2."originalFileName" LIKE '%f4081637024%')
    )
    SELECT * FROM photo_pairs
    WHERE distance <= 0.2
    ORDER BY distance ASC
    LIMIT 5;
    """
    
    result = query_database(sql)
    if result and result.strip():
        print("  相似照片对分析:")
        print("  文件1 | 文件2 | 距离")
        print("  " + "-" * 80)
        for line in result.split('\n'):
            if line.strip():
                parts = line.split(',')
                if len(parts) >= 5:
                    file1 = parts[1].strip()
                    file2 = parts[3].strip()
                    distance = parts[4].strip()
                    print(f"  {file1} | {file2} | {distance}")
    else:
        print("  未找到指定照片的相似度数据")
        print("  可能原因：照片不存在或缺少嵌入向量")

def provide_recommendations():
    """提供修复建议"""
    print("\n" + "="*60)
    print("💡 诊断建议")
    print("="*60)
    
    print("\n可能的问题和解决方案:")
    
    print("\n1. 📊 嵌入向量缺失")
    print("   - 如果嵌入向量覆盖率 < 100%，需要运行智能搜索作业")
    print("   - 在Web界面: 管理面板 → 作业 → 智能搜索 → 运行所有")
    
    print("\n2. 🔄 重复检测作业未运行")
    print("   - 如果没有重复检测记录，需要手动触发")
    print("   - 在Web界面: 管理面板 → 作业 → 重复检测 → 运行所有")
    
    print("\n3. ⚙️  配置问题")
    print("   - 确认重复检测已启用")
    print("   - 确认maxDistance设置正确（当前应为0.1）")
    
    print("\n4. 📁 照片状态问题")
    print("   - 检查照片是否被堆叠（stackId不为空）")
    print("   - 检查照片可见性设置")
    print("   - 确认照片未被删除")
    
    print("\n5. 🎯 距离阈值问题")
    print("   - 即使maxDistance=0.1，某些相似照片的距离可能仍然较大")
    print("   - 可以尝试临时设置更大的值（如0.2）进行测试")

def main():
    """主函数"""
    print("🔬 Immich重复检测问题诊断")
    print("=" * 50)
    print(f"诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    check_duplicate_detection_prerequisites()
    check_specific_photos()
    check_duplicate_detection_jobs()
    check_existing_duplicates()
    analyze_embedding_similarity()
    provide_recommendations()
    
    print(f"\n🌐 Web管理界面: http://10.132.60.111:2283")
    print("建议按照上述建议逐步排查和修复问题")

if __name__ == "__main__":
    main()
