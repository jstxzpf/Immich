# Immich优化部署指南

## 概述

本指南提供了一种优化的Immich部署方式，采用**先下载模型再复制到容器**的策略，解决了以下问题：

- ✅ HuggingFace模型下载加速（使用中国镜像站）
- ✅ 避免容器启动时的模型下载延迟
- ✅ 提高部署的可靠性和可重复性
- ✅ 支持离线部署

## 技术要点

### 1. 模型预下载策略
- 使用HuggingFace中国镜像站 (`https://hf-mirror.com`) 加速下载
- 预下载关键模型：`buffalo_l` 和 `ViT-B-32`
- 使用本地目录挂载替代Docker volume

### 2. 容器配置优化
- 设置 `TRANSFORMERS_OFFLINE=1` 禁用自动下载
- 设置 `HF_HUB_OFFLINE=1` 强制使用本地模型
- 使用中国镜像源加速容器镜像下载

## 部署步骤

### 步骤1：下载模型

选择以下任一方式下载模型：

#### 方式A：使用Python脚本（推荐）
```bash
cd /home/zpf/mycode/Immich/docker
python3 download_models.py
```

#### 方式B：使用Shell脚本
```bash
cd /home/zpf/mycode/Immich/docker
./prepare-models.sh
```

### 步骤2：验证模型下载
```bash
ls -la models/
# 应该看到：
# buffalo_l/
# ViT-B-32/
```

### 步骤3：停止现有服务（如果运行中）
```bash
docker-compose down
```

### 步骤4：启动优化版本
```bash
docker-compose -f docker-compose.optimized.yml up -d
```

### 步骤5：验证服务状态
```bash
docker-compose -f docker-compose.optimized.yml ps
docker-compose -f docker-compose.optimized.yml logs immich-machine-learning
```

## 文件结构

```
docker/
├── docker-compose.optimized.yml    # 优化的部署配置
├── prepare-models.sh               # Shell版本模型下载脚本
├── download_models.py              # Python版本模型下载脚本
├── models/                         # 预下载的模型目录
│   ├── buffalo_l/                  # 人脸识别模型
│   └── ViT-B-32/                   # 图像特征提取模型
└── DEPLOYMENT_GUIDE.md            # 本指南
```

## 关键配置变更

### docker-compose.optimized.yml 主要变更：
1. **模型存储**：从Docker volume改为本地目录挂载
   ```yaml
   volumes:
     - ./models:/cache  # 替代 model-cache:/cache
   ```

2. **环境变量**：添加离线模式配置
   ```yaml
   environment:
     - HF_ENDPOINT=https://hf-mirror.com
     - TRANSFORMERS_OFFLINE=1
     - HF_HUB_OFFLINE=1
   ```

3. **镜像源**：使用中国镜像加速
   ```yaml
   image: ghcr.m.daocloud.io/immich-app/immich-machine-learning:${IMMICH_VERSION:-release}
   ```

## 故障排除

### 模型下载失败
```bash
# 检查网络连接
curl -I https://hf-mirror.com

# 手动安装依赖
pip3 install huggingface_hub

# 清理并重新下载
rm -rf models/
python3 download_models.py
```

### 容器启动失败
```bash
# 查看日志
docker-compose -f docker-compose.optimized.yml logs immich-machine-learning

# 检查模型目录权限
ls -la models/
sudo chown -R 1000:1000 models/
```

### 模型加载错误
```bash
# 验证模型文件完整性
find models/ -name "*.bin" -o -name "*.safetensors" | head -5

# 重新下载特定模型
rm -rf models/buffalo_l/
python3 -c "
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
from huggingface_hub import snapshot_download
snapshot_download('buffalo_l', cache_dir='./models/buffalo_l')
"
```

## 性能优化建议

1. **存储优化**：将模型目录放在SSD上
2. **网络优化**：使用国内镜像源
3. **资源分配**：为机器学习容器分配足够内存
4. **监控**：定期检查容器日志和资源使用情况

## 回滚方案

如需回滚到原始配置：
```bash
docker-compose -f docker-compose.optimized.yml down
docker-compose -f docker-compose.yml up -d
```

## 联系信息

- 服务器IP: 10.132.60.111
- Web界面: http://10.132.60.111:2283
- 管理员账户: jszpf@qq.com
- 照片目录: /data/cleanjpg (23,624张照片)
