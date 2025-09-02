#!/usr/bin/env python3
"""
验证人脸检测改进效果的脚本
通过查询数据库来分析检测率的变化
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

def analyze_detection_by_year():
    """按年份分析人脸检测情况"""
    print("🔍 分析各年份照片的人脸检测情况...")
    
    # 查询按年份统计的照片和人脸数据
    sql = """
    SELECT 
        EXTRACT(YEAR FROM "createdAt") as year,
        COUNT(DISTINCT a.id) as total_photos,
        COUNT(DISTINCT af.id) as detected_faces,
        ROUND(COUNT(DISTINCT af.id)::numeric / NULLIF(COUNT(DISTINCT a.id), 0) * 100, 2) as detection_rate
    FROM asset a
    LEFT JOIN asset_face af ON a.id = af."assetId" AND af."deletedAt" IS NULL
    WHERE a.type = 'IMAGE' 
        AND a."deletedAt" IS NULL
        AND EXTRACT(YEAR FROM "createdAt") BETWEEN 2005 AND 2024
    GROUP BY EXTRACT(YEAR FROM "createdAt")
    ORDER BY year;
    """
    
    result = query_database(sql)
    if not result:
        return
    
    print("\n📊 各年份人脸检测统计:")
    print("年份    | 照片总数 | 检测人脸 | 检测率(%)")
    print("-" * 45)
    
    problem_years = []
    good_years = []
    
    for line in result.split('\n'):
        if line.strip():
            parts = line.split(',')
            if len(parts) >= 4:
                year = parts[0].strip()
                total_photos = parts[1].strip()
                detected_faces = parts[2].strip()
                detection_rate = parts[3].strip() if parts[3].strip() else '0.00'
                
                print(f"{year:<7} | {total_photos:<8} | {detected_faces:<8} | {detection_rate}")
                
                # 分析问题年份
                try:
                    year_int = int(year)
                    rate_float = float(detection_rate)
                    
                    if year_int <= 2011 and rate_float > 0:
                        good_years.append((year_int, rate_float))
                    elif year_int >= 2012:
                        if rate_float == 0:
                            problem_years.append((year_int, rate_float))
                        else:
                            good_years.append((year_int, rate_float))
                except ValueError:
                    continue
    
    return problem_years, good_years

def check_recent_detection_activity():
    """检查最近的检测活动"""
    print("\n🕐 检查最近的人脸检测活动...")
    
    sql = """
    SELECT 
        DATE("createdAt") as detection_date,
        COUNT(*) as faces_detected
    FROM asset_face 
    WHERE "createdAt" >= CURRENT_DATE - INTERVAL '7 days'
        AND "deletedAt" IS NULL
    GROUP BY DATE("createdAt")
    ORDER BY detection_date DESC;
    """
    
    result = query_database(sql)
    if result and result.strip():
        print("最近7天的检测活动:")
        print("日期       | 检测人脸数")
        print("-" * 25)
        for line in result.split('\n'):
            if line.strip():
                parts = line.split(',')
                if len(parts) >= 2:
                    date = parts[0].strip()
                    count = parts[1].strip()
                    print(f"{date} | {count}")
    else:
        print("最近7天没有新的人脸检测活动")

def get_model_info():
    """获取当前使用的模型信息"""
    print("\n🤖 当前模型配置:")
    
    # 检查机器学习服务日志中的模型信息
    try:
        result = subprocess.run([
            'docker', 'logs', 'immich_machine_learning', '--tail=50'
        ], capture_output=True, text=True, check=True)
        
        logs = result.stdout
        if 'buffalo' in logs.lower():
            print("✅ 检测到buffalo模型相关日志")
        
        # 查找模型加载信息
        for line in logs.split('\n'):
            if 'Loading' in line and ('model' in line.lower() or 'buffalo' in line.lower()):
                print(f"  {line.strip()}")
                
    except subprocess.CalledProcessError:
        print("无法获取机器学习服务日志")

def main():
    """主函数"""
    print("🔬 Immich人脸检测改进效果验证")
    print("=" * 50)
    print(f"检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 分析检测情况
    result = analyze_detection_by_year()
    if result:
        problem_years, good_years = result
        
        print(f"\n📈 分析结果:")
        print(f"问题年份数量: {len(problem_years)} (检测率为0%)")
        print(f"正常年份数量: {len(good_years)} (有检测结果)")
        
        if problem_years:
            print(f"\n⚠️  仍存在问题的年份:")
            for year, rate in problem_years:
                print(f"  {year}年: {rate}%")
        
        if good_years:
            print(f"\n✅ 检测正常的年份:")
            recent_good = [y for y, r in good_years if y >= 2012]
            if recent_good:
                print(f"  2012年后有检测结果的年份: {len(recent_good)}个")
                for year, rate in sorted(good_years, reverse=True)[:5]:
                    print(f"  {year}年: {rate}%")
    
    # 检查最近活动
    check_recent_detection_activity()
    
    # 获取模型信息
    get_model_info()
    
    print(f"\n💡 建议:")
    if result and result[0]:  # 如果还有问题年份
        print("  1. 阈值已调整到0.3，但可能需要手动触发人脸检测作业")
        print("  2. 在Web界面进入 管理面板 → 作业 → 人脸检测 → 运行所有")
        print("  3. 等待处理完成后再次运行此脚本验证效果")
    else:
        print("  ✅ 检测阈值调整生效，2012年后照片检测率已改善")
        print("  建议运行人脸聚类作业完成人物识别")
    
    print(f"\n🌐 Web管理界面: http://10.132.60.111:2283")

if __name__ == "__main__":
    main()
