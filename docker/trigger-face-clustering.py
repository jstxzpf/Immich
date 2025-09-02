#!/usr/bin/env python3
"""
Immich人脸聚类作业触发脚本
通过API触发人脸聚类作业
"""

import requests
import json
import sys
import time

# 配置
IMMICH_URL = "http://10.132.60.111:2283"
API_BASE = f"{IMMICH_URL}/api"

def get_api_key():
    """获取API密钥的说明"""
    print("🔑 需要API密钥来访问Immich API")
    print("获取API密钥的步骤：")
    print("1. 访问 http://10.132.60.111:2283")
    print("2. 登录管理员账户")
    print("3. 点击右上角头像 → 账户设置")
    print("4. 选择 'API密钥' 选项卡")
    print("5. 点击 '新建API密钥'")
    print("6. 复制生成的密钥")
    print()
    
    api_key = input("请输入API密钥: ").strip()
    return api_key

def check_server_status():
    """检查服务器状态"""
    try:
        response = requests.get(f"{API_BASE}/server-info/ping", timeout=10)
        if response.status_code == 200:
            print("✅ Immich服务器连接正常")
            return True
        else:
            print(f"❌ 服务器响应异常: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接到Immich服务器: {e}")
        return False

def get_job_status(api_key):
    """获取作业状态"""
    headers = {"X-API-Key": api_key}
    
    try:
        response = requests.get(f"{API_BASE}/jobs", headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ 获取作业状态失败: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return None

def trigger_face_clustering(api_key):
    """触发人脸聚类作业"""
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    # 触发人脸聚类作业
    payload = {
        "command": "start",
        "force": False
    }
    
    try:
        response = requests.put(
            f"{API_BASE}/jobs/face-clustering", 
            headers=headers, 
            json=payload
        )
        
        if response.status_code == 200:
            print("✅ 人脸聚类作业已启动")
            return True
        else:
            print(f"❌ 启动人脸聚类作业失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return False

def show_face_stats():
    """显示人脸统计信息"""
    print("\n📊 当前人脸统计:")
    
    # 通过数据库查询显示统计
    import subprocess
    
    try:
        result = subprocess.run([
            "docker", "exec", "immich_postgres", "psql", "-U", "postgres", "-d", "immich", "-c",
            """
            SELECT 
                COUNT(*) as detected_faces,
                COUNT(DISTINCT "personId") as unique_persons,
                COUNT(CASE WHEN "personId" IS NOT NULL THEN 1 END) as assigned_faces
            FROM asset_face WHERE "deletedAt" IS NULL;
            """
        ], capture_output=True, text=True, cwd="/home/zpf/mycode/Immich/docker")
        
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("❌ 无法获取数据库统计")
    except Exception as e:
        print(f"❌ 查询统计失败: {e}")

def main():
    print("🎯 Immich人脸聚类作业触发器")
    print("=" * 40)
    
    # 检查服务器状态
    if not check_server_status():
        sys.exit(1)
    
    # 显示当前统计
    show_face_stats()
    
    # 获取API密钥
    api_key = get_api_key()
    if not api_key:
        print("❌ 需要API密钥才能继续")
        sys.exit(1)
    
    # 获取作业状态
    print("\n📋 获取当前作业状态...")
    jobs = get_job_status(api_key)
    if jobs:
        # 显示人脸相关作业状态
        face_jobs = ["face-detection", "face-clustering", "facial-recognition"]
        for job_name in face_jobs:
            if job_name in jobs:
                job_info = jobs[job_name]
                active = job_info.get("active", 0)
                waiting = job_info.get("waiting", 0)
                print(f"  {job_name}: 活跃={active}, 等待={waiting}")
    
    # 触发人脸聚类
    print("\n🚀 启动人脸聚类作业...")
    if trigger_face_clustering(api_key):
        print("\n✅ 人脸聚类作业已成功启动！")
        print("\n💡 接下来的步骤:")
        print("1. 等待人脸聚类完成（可能需要几分钟到几小时）")
        print("2. 访问Web界面: http://10.132.60.111:2283")
        print("3. 进入 '探索' → '人物' 查看聚类结果")
        print("4. 为识别的人脸添加姓名标签")
    else:
        print("\n❌ 启动失败，请检查API密钥是否正确")
        sys.exit(1)

if __name__ == "__main__":
    main()
