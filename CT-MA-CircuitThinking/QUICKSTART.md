# 🚀 CT-MA-CircuitThinking 快速开始指南

欢迎使用CT-MA-CircuitThinking系统！本指南将帮助您快速设置和运行系统。

## 📋 前置条件

### 1. 环境要求
- Python 3.9+
- 16GB+ 内存推荐
- 5GB+ 可用磁盘空间
- 稳定的网络连接（用于API调用）

### 2. API密钥
您需要以下API密钥：
- **DeepSeek API Key**: 用于LLM推理
- **OpenAI API Key**: 用于文本嵌入

## 🔧 安装步骤

### 步骤 1: 激活虚拟环境
```bash
conda activate graphcot
```

### 步骤 2: 安装依赖
```bash
cd CAL_KG_System/CT-MA-CircuitThinking
pip install -r requirements.txt
```

### 步骤 3: 配置系统
```bash
# 复制配置模板
cp config/system_config.yaml.example config/system_config.yaml

# 设置环境变量
export DEEPSEEK_API_KEY="your_deepseek_api_key"
export OPENAI_API_KEY="your_openai_api_key"

# Windows用户使用:
# set DEEPSEEK_API_KEY=your_deepseek_api_key
# set OPENAI_API_KEY=your_openai_api_key
```

### 步骤 4: 导入知识图谱
```bash
python scripts/import_kg.py
```

### 步骤 5: 设置环境
```bash
python scripts/setup_environment.py
```

## 🎯 运行系统

### 完整流水线运行
```bash
python main.py --mode full --batch_size 5
```

### 分步执行
```bash
# 1. 提取子图谱
python main.py --mode extract_subgraphs

# 2. 生成CoT数据
python main.py --mode generate_cot

# 3. 批量生成（推荐）
python scripts/batch_generate.py --max-subgraphs 10 --batch-size 3
```

## 📊 查看结果

### 生成的数据位置
- **CoT数据集**: `data/output/cot_datasets/`
- **分析报告**: `data/output/reports/`
- **子图谱**: `data/output/subgraphs/`

### 使用Jupyter分析
```bash
jupyter notebook notebooks/analysis.ipynb
```

## 🔍 示例输出

生成的CoT数据格式如下：

```json
{
  "data_id": "cot_circuit_001",
  "source_application": "电流镜负载的差动对运算放大器",
  "logic": "<logic>\n【目标应用】: 电流镜负载的差动对运算放大器\n【关键瓶颈】: 在单级放大器中同时实现高电压增益和高共模抑制比...\n</logic>",
  "think": "<think>\n推理开始。目标是理解如何构建一个高增益、高CMRR的差动对运放...\n</think>",
  "answer": "<answer>\n为在单级差动对放大器中同时实现高增益和高CMRR，核心策略是采用电流镜作为有源负载...\n</answer>"
}
```

## ⚙️ 配置选项

### 主要配置参数

| 参数 | 描述 | 默认值 |
|------|------|--------|
| `processing.batch_size` | 批处理大小 | 10 |
| `models.llm.temperature` | LLM温度 | 0.3 |
| `quality.min_think_length` | 思考部分最小长度 | 500 |
| `subgraph.max_nodes` | 子图最大节点数 | 20 |

### 修改配置
编辑 `config/system_config.yaml` 文件来调整参数。

## 🐛 故障排除

### 常见问题

**1. API密钥错误**
```
错误: LLM API key not configured
解决: 检查环境变量设置，确保API密钥正确
```

**2. 知识图谱未找到**
```
错误: Knowledge graph not found
解决: 运行 python scripts/import_kg.py
```

**3. 内存不足**
```
错误: Out of memory
解决: 减少batch_size参数，如设置为3或5
```

**4. 网络连接问题**
```
错误: API call failed
解决: 检查网络连接，确认API服务可用
```

### 调试模式
```bash
python main.py --debug --batch_size 1
```

## 📈 性能优化

### 提高生成速度
1. **增加批处理大小**: 适当增加 `batch_size`
2. **并行处理**: 设置 `processing.enable_parallel=true`
3. **减少验证**: 临时禁用某些质量检查

### 提高质量
1. **增加知识库**: 在 `data/knowledge_base/` 添加更多文档
2. **调整温度**: 降低 `models.llm.temperature`
3. **增加检索数量**: 提高 `rag.retrieval.top_k`

## 📚 进阶使用

### 自定义Agent提示词
编辑 `config/agent_prompts.yaml` 来自定义Agent行为。

### 添加新的检索策略
在 `src/rag/retriever.py` 中实现新的检索方法。

### 扩展质量评估
在 `src/cot/quality_checker.py` 中添加新的质量维度。

## 🤝 获取帮助

如果遇到问题：

1. **查看日志**: 检查 `logs/` 目录下的日志文件
2. **运行测试**: `python -m pytest tests/`
3. **查看文档**: 阅读 `README.md` 获取详细信息

## 🎉 下一步

成功运行系统后，您可以：

1. **分析生成的数据**: 使用Jupyter notebook进行深入分析
2. **调优参数**: 根据结果调整配置参数
3. **扩展知识库**: 添加更多电路设计文档
4. **自定义流程**: 修改Agent逻辑以适应特定需求

祝您使用愉快！🚀
