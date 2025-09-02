#!/usr/bin/env python3
"""
Immich照片技术规格差异分析脚本
用于分析2011年前后照片的技术差异，找出影响人脸检测的关键因素
"""

import os
import sys
import json
import requests
from datetime import datetime
from pathlib import Path
from PIL import Image, ExifTags
from PIL.ExifTags import TAGS
import numpy as np

# 配置
IMMICH_SERVER = "http://10.132.60.111:2283"
SAMPLE_SIZE = 10  # 每个年代采样的照片数量

def get_image_metadata(image_path):
    """获取图片的详细元数据"""
    try:
        with Image.open(image_path) as img:
            # 基本信息
            metadata = {
                'filename': os.path.basename(image_path),
                'format': img.format,
                'mode': img.mode,
                'size': img.size,
                'width': img.width,
                'height': img.height,
                'resolution': img.width * img.height,
                'aspect_ratio': round(img.width / img.height, 2),
                'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info,
            }
            
            # EXIF数据
            exif_data = {}
            if hasattr(img, '_getexif') and img._getexif() is not None:
                exif = img._getexif()
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif_data[tag] = str(value)
            
            metadata['exif'] = exif_data
            
            # 色彩信息
            if img.mode == 'RGB':
                img_array = np.array(img)
                metadata['color_stats'] = {
                    'mean_brightness': float(np.mean(img_array)),
                    'std_brightness': float(np.std(img_array)),
                    'mean_r': float(np.mean(img_array[:,:,0])),
                    'mean_g': float(np.mean(img_array[:,:,1])),
                    'mean_b': float(np.mean(img_array[:,:,2])),
                }
            
            return metadata
            
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None

def analyze_photos_by_year(photo_dir):
    """按年份分析照片"""
    photo_dir = Path(photo_dir)
    if not photo_dir.exists():
        print(f"照片目录不存在: {photo_dir}")
        return None
    
    # 收集照片文件
    photo_files = []
    for ext in ['*.jpg', '*.jpeg', '*.JPG', '*.JPEG']:
        photo_files.extend(photo_dir.rglob(ext))
    
    print(f"找到 {len(photo_files)} 张照片")
    
    # 按年份分组
    photos_by_year = {}
    for photo_path in photo_files:
        try:
            # 尝试从文件名或EXIF获取年份
            year = None
            
            # 方法1: 从EXIF获取
            try:
                with Image.open(photo_path) as img:
                    if hasattr(img, '_getexif') and img._getexif() is not None:
                        exif = img._getexif()
                        for tag_id, value in exif.items():
                            tag = TAGS.get(tag_id, tag_id)
                            if tag == 'DateTime':
                                year = int(str(value)[:4])
                                break
            except:
                pass
            
            # 方法2: 从文件修改时间获取
            if year is None:
                mtime = os.path.getmtime(photo_path)
                year = datetime.fromtimestamp(mtime).year
            
            if year not in photos_by_year:
                photos_by_year[year] = []
            photos_by_year[year].append(photo_path)
            
        except Exception as e:
            print(f"处理照片时出错 {photo_path}: {e}")
            continue
    
    return photos_by_year

def compare_photo_groups(photos_by_year):
    """对比不同年份照片的技术规格"""
    
    # 分为两组：2011年及以前 vs 2012年及以后
    old_photos = []  # 2011年及以前
    new_photos = []  # 2012年及以后
    
    for year, photos in photos_by_year.items():
        if year <= 2011:
            old_photos.extend(photos[:SAMPLE_SIZE])  # 限制采样数量
        elif year >= 2012:
            new_photos.extend(photos[:SAMPLE_SIZE])  # 限制采样数量
    
    print(f"老照片样本: {len(old_photos)} 张 (2011年及以前)")
    print(f"新照片样本: {len(new_photos)} 张 (2012年及以后)")
    
    # 分析两组照片
    old_metadata = []
    new_metadata = []
    
    print("\n分析老照片...")
    for i, photo_path in enumerate(old_photos[:SAMPLE_SIZE]):
        print(f"  处理 {i+1}/{min(len(old_photos), SAMPLE_SIZE)}: {photo_path.name}")
        metadata = get_image_metadata(photo_path)
        if metadata:
            old_metadata.append(metadata)
    
    print("\n分析新照片...")
    for i, photo_path in enumerate(new_photos[:SAMPLE_SIZE]):
        print(f"  处理 {i+1}/{min(len(new_photos), SAMPLE_SIZE)}: {photo_path.name}")
        metadata = get_image_metadata(photo_path)
        if metadata:
            new_metadata.append(metadata)
    
    return old_metadata, new_metadata

def generate_comparison_report(old_metadata, new_metadata):
    """生成对比报告"""
    
    def calculate_stats(metadata_list, field):
        """计算统计数据"""
        values = []
        for item in metadata_list:
            if field in item and item[field] is not None:
                values.append(item[field])
        
        if not values:
            return None
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'median': sorted(values)[len(values)//2]
        }
    
    print("\n" + "="*60)
    print("照片技术规格对比报告")
    print("="*60)
    
    # 分辨率对比
    print("\n📐 分辨率对比:")
    old_res = calculate_stats(old_metadata, 'resolution')
    new_res = calculate_stats(new_metadata, 'resolution')
    
    if old_res and new_res:
        print(f"  老照片平均分辨率: {old_res['avg']:,.0f} 像素")
        print(f"  新照片平均分辨率: {new_res['avg']:,.0f} 像素")
        print(f"  分辨率提升: {(new_res['avg']/old_res['avg']-1)*100:.1f}%")
    
    # 尺寸对比
    print("\n📏 尺寸对比:")
    old_width = calculate_stats(old_metadata, 'width')
    new_width = calculate_stats(new_metadata, 'width')
    old_height = calculate_stats(old_metadata, 'height')
    new_height = calculate_stats(new_metadata, 'height')
    
    if all([old_width, new_width, old_height, new_height]):
        print(f"  老照片平均尺寸: {old_width['avg']:.0f} x {old_height['avg']:.0f}")
        print(f"  新照片平均尺寸: {new_width['avg']:.0f} x {new_height['avg']:.0f}")
    
    # 格式对比
    print("\n🎨 格式对比:")
    old_formats = {}
    new_formats = {}
    
    for item in old_metadata:
        fmt = item.get('format', 'Unknown')
        old_formats[fmt] = old_formats.get(fmt, 0) + 1
    
    for item in new_metadata:
        fmt = item.get('format', 'Unknown')
        new_formats[fmt] = new_formats.get(fmt, 0) + 1
    
    print(f"  老照片格式分布: {old_formats}")
    print(f"  新照片格式分布: {new_formats}")
    
    # 色彩模式对比
    print("\n🌈 色彩模式对比:")
    old_modes = {}
    new_modes = {}
    
    for item in old_metadata:
        mode = item.get('mode', 'Unknown')
        old_modes[mode] = old_modes.get(mode, 0) + 1
    
    for item in new_metadata:
        mode = item.get('mode', 'Unknown')
        new_modes[mode] = new_modes.get(mode, 0) + 1
    
    print(f"  老照片色彩模式: {old_modes}")
    print(f"  新照片色彩模式: {new_modes}")
    
    # EXIF数据对比
    print("\n📋 EXIF数据对比:")
    old_exif_keys = set()
    new_exif_keys = set()
    
    for item in old_metadata:
        old_exif_keys.update(item.get('exif', {}).keys())
    
    for item in new_metadata:
        new_exif_keys.update(item.get('exif', {}).keys())
    
    print(f"  老照片EXIF字段数: {len(old_exif_keys)}")
    print(f"  新照片EXIF字段数: {len(new_exif_keys)}")
    print(f"  新增EXIF字段: {new_exif_keys - old_exif_keys}")
    
    # 关键发现
    print("\n🔍 关键发现:")
    if new_res and old_res and new_res['avg'] > old_res['avg'] * 1.5:
        print("  ⚠️  新照片分辨率显著提高，可能需要调整检测参数")
    
    if 'JPEG' in new_formats and 'JPEG' in old_formats:
        print("  ✅ 新老照片都使用JPEG格式，格式兼容性良好")
    
    print("\n💡 建议:")
    print("  1. 已将检测阈值从0.7降低到0.3，应该能提高检测率")
    print("  2. 如果问题仍然存在，考虑针对高分辨率照片优化预处理")
    print("  3. 可能需要调整RetinaFace的input_size参数")

def main():
    """主函数"""
    print("Immich照片技术规格差异分析")
    print("="*40)
    
    # 照片目录
    photo_dir = "/data/cleanjpg"
    
    if not os.path.exists(photo_dir):
        print(f"错误: 照片目录不存在 {photo_dir}")
        print("请确认照片目录路径是否正确")
        return
    
    # 分析照片
    print(f"分析照片目录: {photo_dir}")
    photos_by_year = analyze_photos_by_year(photo_dir)
    
    if not photos_by_year:
        print("未找到照片文件")
        return
    
    print(f"\n按年份分布:")
    for year in sorted(photos_by_year.keys()):
        print(f"  {year}年: {len(photos_by_year[year])} 张")
    
    # 对比分析
    old_metadata, new_metadata = compare_photo_groups(photos_by_year)
    
    if not old_metadata or not new_metadata:
        print("警告: 缺少足够的样本数据进行对比")
        return
    
    # 生成报告
    generate_comparison_report(old_metadata, new_metadata)
    
    # 保存详细数据
    report_data = {
        'timestamp': datetime.now().isoformat(),
        'old_photos_metadata': old_metadata,
        'new_photos_metadata': new_metadata,
        'summary': {
            'old_photos_count': len(old_metadata),
            'new_photos_count': len(new_metadata),
            'detection_threshold_changed': True,
            'old_threshold': 0.7,
            'new_threshold': 0.3
        }
    }
    
    with open('photo_analysis_report.json', 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 详细报告已保存到: photo_analysis_report.json")

if __name__ == "__main__":
    main()
