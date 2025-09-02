#!/usr/bin/env python3
"""
手动测试人脸检测API脚本
用于验证修改后的检测阈值对2020年照片的效果
"""

import os
import sys
import json
import requests
import time
from pathlib import Path
from PIL import Image
import base64
from io import BytesIO

# 配置
IMMICH_ML_SERVER = "http://10.132.60.111:3003"  # 机器学习服务地址
TEST_PHOTO_DIR = "/data/cleanjpg"

def encode_image_to_base64(image_path):
    """将图片编码为base64"""
    try:
        with Image.open(image_path) as img:
            # 如果图片太大，先缩放
            if img.width > 2048 or img.height > 2048:
                img.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
            
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=95)
            img_bytes = buffer.getvalue()
            
            return base64.b64encode(img_bytes).decode('utf-8')
    except Exception as e:
        print(f"编码图片失败 {image_path}: {e}")
        return None

def test_face_detection_api(image_path, threshold=0.3):
    """测试人脸检测API"""
    print(f"\n🔍 测试照片: {image_path}")
    
    # 检查文件是否存在
    if not os.path.exists(image_path):
        print(f"❌ 文件不存在: {image_path}")
        return None
    
    # 获取图片信息
    try:
        with Image.open(image_path) as img:
            print(f"   📐 尺寸: {img.width} x {img.height}")
            print(f"   🎨 格式: {img.format}")
            print(f"   🌈 模式: {img.mode}")
    except Exception as e:
        print(f"❌ 无法读取图片: {e}")
        return None
    
    # 准备API请求
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # 构建请求数据
        entries = {
            "facial-recognition": {
                "detection": {
                    "modelName": "buffalo_l",
                    "options": {
                        "minScore": threshold
                    }
                }
            }
        }
        
        files = {
            'image': ('test.jpg', image_data, 'image/jpeg'),
            'entries': (None, json.dumps(entries), 'application/json')
        }
        
        print(f"   🚀 发送检测请求 (阈值: {threshold})...")
        
        # 发送请求
        response = requests.post(
            f"{IMMICH_ML_SERVER}/predict",
            files=files,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # 解析结果
            if 'facial-recognition' in result:
                faces = result['facial-recognition']
                face_count = len(faces.get('boxes', []))
                
                print(f"   ✅ 检测成功!")
                print(f"   👤 检测到人脸数量: {face_count}")
                
                if face_count > 0:
                    print(f"   📊 人脸详情:")
                    boxes = faces.get('boxes', [])
                    scores = faces.get('scores', [])
                    
                    for i, (box, score) in enumerate(zip(boxes, scores)):
                        x1, y1, x2, y2 = box
                        print(f"      人脸 {i+1}: 位置({x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}) 置信度:{score:.3f}")
                
                return {
                    'success': True,
                    'face_count': face_count,
                    'faces': faces,
                    'threshold': threshold
                }
            else:
                print(f"   ❌ 响应中没有人脸检测结果")
                return {'success': False, 'error': 'No facial-recognition in response'}
        
        else:
            print(f"   ❌ API请求失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return {'success': False, 'error': f'HTTP {response.status_code}'}
    
    except requests.exceptions.Timeout:
        print(f"   ❌ 请求超时")
        return {'success': False, 'error': 'Timeout'}
    except Exception as e:
        print(f"   ❌ 请求异常: {e}")
        return {'success': False, 'error': str(e)}

def find_test_photos():
    """查找测试用的照片"""
    test_dir = Path(TEST_PHOTO_DIR)
    
    if not test_dir.exists():
        print(f"❌ 测试目录不存在: {test_dir}")
        return []
    
    # 查找2020年的照片
    photos_2020 = []
    photos_2010 = []
    
    for ext in ['*.jpg', '*.jpeg', '*.JPG', '*.JPEG']:
        for photo_path in test_dir.rglob(ext):
            try:
                # 从文件修改时间判断年份
                mtime = os.path.getmtime(photo_path)
                year = time.gmtime(mtime).tm_year
                
                if year == 2020:
                    photos_2020.append(photo_path)
                elif year == 2010:
                    photos_2010.append(photo_path)
                    
            except Exception:
                continue
    
    print(f"找到2020年照片: {len(photos_2020)} 张")
    print(f"找到2010年照片: {len(photos_2010)} 张")
    
    return photos_2020[:3], photos_2010[:3]  # 各取3张作为测试

def test_different_thresholds(image_path):
    """测试不同阈值的效果"""
    thresholds = [0.7, 0.5, 0.3, 0.1]
    results = []
    
    print(f"\n🧪 测试不同阈值对照片的影响: {os.path.basename(image_path)}")
    
    for threshold in thresholds:
        result = test_face_detection_api(image_path, threshold)
        if result:
            results.append(result)
            time.sleep(1)  # 避免请求过快
    
    # 汇总结果
    print(f"\n📈 阈值测试结果汇总:")
    print(f"{'阈值':<8} {'检测到人脸数':<12} {'状态'}")
    print("-" * 30)
    
    for result in results:
        if result['success']:
            status = "✅ 成功"
            face_count = result['face_count']
        else:
            status = "❌ 失败"
            face_count = 0
        
        print(f"{result['threshold']:<8} {face_count:<12} {status}")
    
    return results

def main():
    """主函数"""
    print("🔬 Immich人脸检测API测试")
    print("=" * 50)
    
    # 检查机器学习服务状态
    try:
        response = requests.get(f"{IMMICH_ML_SERVER}/ping", timeout=5)
        if response.status_code == 200:
            print("✅ 机器学习服务运行正常")
        else:
            print("❌ 机器学习服务响应异常")
            return
    except Exception as e:
        print(f"❌ 无法连接到机器学习服务: {e}")
        print(f"请确认服务地址: {IMMICH_ML_SERVER}")
        return
    
    # 查找测试照片
    photos_2020, photos_2010 = find_test_photos()
    
    if not photos_2020 and not photos_2010:
        print("❌ 未找到测试照片")
        return
    
    # 测试结果收集
    all_results = []
    
    # 测试2020年照片（问题照片）
    if photos_2020:
        print(f"\n📅 测试2020年照片 (问题年份)")
        for photo_path in photos_2020[:2]:  # 测试2张
            results = test_different_thresholds(photo_path)
            all_results.extend(results)
    
    # 测试2010年照片（正常年份）
    if photos_2010:
        print(f"\n📅 测试2010年照片 (正常年份)")
        for photo_path in photos_2010[:1]:  # 测试1张作为对比
            results = test_different_thresholds(photo_path)
            all_results.extend(results)
    
    # 生成测试报告
    print(f"\n📊 测试总结:")
    
    success_count = sum(1 for r in all_results if r['success'])
    total_count = len(all_results)
    
    print(f"总测试次数: {total_count}")
    print(f"成功次数: {success_count}")
    print(f"成功率: {success_count/total_count*100:.1f}%")
    
    # 按阈值统计
    threshold_stats = {}
    for result in all_results:
        if result['success']:
            threshold = result['threshold']
            if threshold not in threshold_stats:
                threshold_stats[threshold] = {'total': 0, 'with_faces': 0, 'face_count': 0}
            
            threshold_stats[threshold]['total'] += 1
            if result['face_count'] > 0:
                threshold_stats[threshold]['with_faces'] += 1
                threshold_stats[threshold]['face_count'] += result['face_count']
    
    print(f"\n📈 各阈值检测效果:")
    print(f"{'阈值':<8} {'测试次数':<10} {'检测到人脸':<12} {'检测率':<10} {'平均人脸数'}")
    print("-" * 60)
    
    for threshold in sorted(threshold_stats.keys(), reverse=True):
        stats = threshold_stats[threshold]
        detection_rate = stats['with_faces'] / stats['total'] * 100
        avg_faces = stats['face_count'] / stats['total'] if stats['total'] > 0 else 0
        
        print(f"{threshold:<8} {stats['total']:<10} {stats['with_faces']:<12} {detection_rate:.1f}%{'':<6} {avg_faces:.1f}")
    
    # 保存测试结果
    report = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'server': IMMICH_ML_SERVER,
        'test_results': all_results,
        'threshold_stats': threshold_stats,
        'recommendation': "建议使用阈值0.3，在检测率和准确性之间取得平衡"
    }
    
    with open('face_detection_test_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 详细测试报告已保存到: face_detection_test_report.json")
    
    # 给出建议
    print(f"\n💡 建议:")
    if 0.3 in threshold_stats and threshold_stats[0.3]['with_faces'] > 0:
        print("✅ 阈值调整到0.3后，检测效果有改善")
        print("建议重新运行人脸检测作业，验证整体效果")
    else:
        print("⚠️  仅调整阈值可能不够，需要进一步优化图像预处理参数")

if __name__ == "__main__":
    main()
