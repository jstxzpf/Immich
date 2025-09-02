#!/usr/bin/env python3
"""
Immich 自动扫描和人脸检测脚本
用于自动化扫描外部照片库并启动人脸检测任务
"""

import requests
import json
import time
import sys
import os

# Immich API 配置
IMMICH_URL = "http://localhost:2283"
API_BASE = f"{IMMICH_URL}/api"

class ImmichAPI:
    def __init__(self, base_url, api_key=None):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"X-API-Key": api_key})
    
    def ping(self):
        """测试API连接"""
        try:
            response = self.session.get(f"{self.base_url}/server/ping")
            return response.status_code == 200
        except Exception as e:
            print(f"API连接失败: {e}")
            return False
    
    def get_libraries(self):
        """获取所有外部库"""
        try:
            response = self.session.get(f"{self.base_url}/libraries")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"获取库列表失败: {e}")
            return []
    
    def create_library(self, name, import_paths, exclusion_pattern="", inclusion_pattern=""):
        """创建外部库"""
        data = {
            "name": name,
            "importPaths": import_paths,
            "exclusionPattern": exclusion_pattern,
            "inclusionPattern": inclusion_pattern
        }
        try:
            response = self.session.post(f"{self.base_url}/libraries", json=data)
            if response.status_code == 201:
                return response.json()
            else:
                print(f"创建库失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"创建库异常: {e}")
            return None
    
    def scan_library(self, library_id, scan_all=True):
        """扫描库"""
        data = {"refreshAllFiles": scan_all}
        try:
            response = self.session.post(f"{self.base_url}/libraries/{library_id}/scan", json=data)
            return response.status_code == 204
        except Exception as e:
            print(f"扫描库失败: {e}")
            return False
    
    def get_jobs(self):
        """获取作业状态"""
        try:
            response = self.session.get(f"{self.base_url}/jobs")
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            print(f"获取作业状态失败: {e}")
            return {}
    
    def run_job(self, job_name, force=False):
        """运行作业"""
        data = {"force": force}
        try:
            response = self.session.post(f"{self.base_url}/jobs/{job_name}", json=data)
            return response.status_code == 204
        except Exception as e:
            print(f"运行作业失败: {e}")
            return False

def main():
    print("🚀 开始Immich自动扫描和人脸检测流程...")
    
    # 初始化API客户端
    api = ImmichAPI(API_BASE)
    
    # 测试连接
    print("📡 测试API连接...")
    if not api.ping():
        print("❌ 无法连接到Immich API")
        sys.exit(1)
    print("✅ API连接成功")
    
    # 检查现有库
    print("📚 检查现有外部库...")
    libraries = api.get_libraries()
    
    cleanjpg_library = None
    for lib in libraries:
        if "cleanjpg" in lib.get("name", "").lower():
            cleanjpg_library = lib
            break
    
    # 创建或使用现有库
    if not cleanjpg_library:
        print("📁 创建新的外部库...")
        cleanjpg_library = api.create_library(
            name="cleanjpg照片库",
            import_paths=["/mnt/external_photos/jpg"],
            inclusion_pattern="**/*.{jpg,jpeg,png,tiff,webp,dng,nef,cr2,arw}"
        )
        if not cleanjpg_library:
            print("❌ 创建库失败")
            sys.exit(1)
        print(f"✅ 库创建成功: {cleanjpg_library['name']}")
    else:
        print(f"✅ 使用现有库: {cleanjpg_library['name']}")
    
    # 扫描库
    print("🔍 开始扫描照片库...")
    library_id = cleanjpg_library["id"]
    if api.scan_library(library_id, scan_all=True):
        print("✅ 库扫描已启动")
    else:
        print("❌ 库扫描启动失败")
        sys.exit(1)
    
    # 等待扫描完成（简单的等待，实际应该检查作业状态）
    print("⏳ 等待扫描完成...")
    time.sleep(30)  # 给扫描一些时间开始
    
    # 启动人脸检测
    print("👤 启动人脸检测作业...")
    if api.run_job("faceDetection", force=False):
        print("✅ 人脸检测作业已启动")
    else:
        print("❌ 人脸检测作业启动失败")
    
    # 启动人脸识别
    print("🧠 启动人脸识别作业...")
    if api.run_job("facialRecognition", force=False):
        print("✅ 人脸识别作业已启动")
    else:
        print("❌ 人脸识别作业启动失败")
    
    print("🎉 自动化流程完成！")
    print("💡 请通过Web界面 (http://localhost:2283) 监控处理进度")

if __name__ == "__main__":
    main()
