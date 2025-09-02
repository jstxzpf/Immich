#!/usr/bin/env python3
"""
检查和修改Immich重复检测配置的脚本
"""

import subprocess
import json

def query_database(sql):
    """执行数据库查询"""
    try:
        result = subprocess.run([
            'docker', 'exec', 'immich_postgres', 
            'psql', '-U', 'postgres', '-d', 'immich', 
            '-c', sql, '-t'
        ], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"数据库查询失败: {e}")
        return None

def get_current_config():
    """获取当前的机器学习配置"""
    print("🔍 检查当前重复检测配置...")
    
    sql = """
    SELECT value 
    FROM system_metadata 
    WHERE key = 'system-config';
    """
    
    result = query_database(sql)
    if result:
        try:
            config = json.loads(result)
            ml_config = config.get('machineLearning', {})
            duplicate_config = ml_config.get('duplicateDetection', {})
            
            print(f"机器学习配置:")
            print(f"  启用状态: {ml_config.get('enabled', 'unknown')}")
            print(f"  CLIP启用: {ml_config.get('clip', {}).get('enabled', 'unknown')}")
            print(f"  重复检测启用: {duplicate_config.get('enabled', 'unknown')}")
            print(f"  当前maxDistance: {duplicate_config.get('maxDistance', 'unknown')}")
            
            return config, duplicate_config
        except json.JSONDecodeError as e:
            print(f"配置解析失败: {e}")
            return None, None
    else:
        print("未找到系统配置")
        return None, None

def update_max_distance(new_distance):
    """更新maxDistance配置"""
    print(f"\n🔧 更新maxDistance为: {new_distance}")
    
    # 首先获取当前配置
    config, _ = get_current_config()
    if not config:
        print("无法获取当前配置，更新失败")
        return False
    
    # 更新配置
    if 'machineLearning' not in config:
        config['machineLearning'] = {}
    if 'duplicateDetection' not in config['machineLearning']:
        config['machineLearning']['duplicateDetection'] = {}
    
    config['machineLearning']['duplicateDetection']['maxDistance'] = new_distance
    
    # 确保重复检测是启用的
    config['machineLearning']['duplicateDetection']['enabled'] = True
    
    # 更新数据库
    config_json = json.dumps(config).replace("'", "''")
    sql = f"""
    UPDATE system_metadata 
    SET value = '{config_json}' 
    WHERE key = 'system-config';
    """
    
    result = query_database(sql)
    if result is not None:
        print("✅ 配置更新成功")
        return True
    else:
        print("❌ 配置更新失败")
        return False

def show_web_interface_steps():
    """显示Web界面设置步骤"""
    print("\n" + "="*60)
    print("🌐 Web界面设置步骤")
    print("="*60)
    
    print("\n1. 访问管理界面:")
    print("   URL: http://10.132.60.111:2283")
    print("   账号: jszpf@qq.com")
    
    print("\n2. 进入设置:")
    print("   点击右上角头像 → 管理 → 设置")
    
    print("\n3. 机器学习设置:")
    print("   点击 '机器学习' 选项卡")
    
    print("\n4. 重复检测配置:")
    print("   找到 '重复检测' 部分")
    print("   确保 '启用重复检测' 开关打开")
    print("   调整 '最大距离' 参数:")
    print("     - 当前建议值: 0.05")
    print("     - 严格检测: 0.01-0.03")
    print("     - 宽松检测: 0.05-0.1")
    
    print("\n5. 保存并运行:")
    print("   点击 '保存' 按钮")
    print("   然后到 '作业' 页面运行 '重复检测' 作业")

def trigger_duplicate_detection():
    """提供触发重复检测的说明"""
    print("\n" + "="*60)
    print("🚀 触发重复检测作业")
    print("="*60)
    
    print("\n在Web界面中:")
    print("1. 进入 '管理' → '作业'")
    print("2. 找到 '重复检测' 作业")
    print("3. 点击 '运行所有' 按钮")
    print("4. 等待作业完成（可能需要几分钟到几小时）")
    
    print("\n作业完成后:")
    print("1. 进入 '探索' → '重复项'")
    print("2. 查看检测到的重复照片")
    print("3. 根据需要删除或保留重复项")

def main():
    """主函数"""
    print("🔧 Immich重复检测配置管理")
    print("=" * 50)
    
    # 检查当前配置
    config, duplicate_config = get_current_config()
    
    if duplicate_config:
        current_distance = duplicate_config.get('maxDistance', 0.01)
        enabled = duplicate_config.get('enabled', False)
        
        print(f"\n当前状态:")
        print(f"  重复检测启用: {enabled}")
        print(f"  最大距离阈值: {current_distance}")
        
        if not enabled:
            print("\n⚠️  重复检测未启用！")
            print("需要在Web界面中启用重复检测功能")
        
        if current_distance > 0.1:
            print(f"\n⚠️  当前阈值 {current_distance} 可能过大")
            print("建议设置为 0.01-0.1 之间")
        elif current_distance < 0.001:
            print(f"\n⚠️  当前阈值 {current_distance} 可能过小")
            print("可能检测不到相似但不完全相同的照片")
    
    # 显示设置步骤
    show_web_interface_steps()
    
    # 显示作业触发说明
    trigger_duplicate_detection()
    
    print(f"\n💡 基于之前的诊断结果:")
    print(f"   f4081644432_1.jpg 和 f4081637024_1.jpg 的距离为 0.009")
    print(f"   这意味着阈值设置为 0.01 或更大都应该能检测到它们")
    print(f"   关键是要运行重复检测作业！")

if __name__ == "__main__":
    main()
