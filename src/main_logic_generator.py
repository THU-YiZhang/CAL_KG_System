"""
主逻辑知识图谱生成器
功能：基于章节数据构建章节间关系的主逻辑知识图谱
"""

import os
import json
import re
from typing import List, Dict, Any
from datetime import datetime
from openai import OpenAI

from .utils import config_manager, file_manager, logger, retry_on_failure

class MainLogicGenerator:
    """主逻辑知识图谱生成器"""
    
    def __init__(self, workers: int = 8):
        """初始化"""
        self.client = OpenAI(
            api_key="sk-pBUBTdSpfx0ppYf30rzzmbr60WiffKq52EQzx45r9rntGjli",
            base_url="https://www.dmxapi.cn/v1",
        )
        self.model = "DMXAPI-DeepSeek-V3"
        self.workers = workers
        
        print("🧠 [主逻辑生成器] 初始化完成")
        print(f"📡 使用模型: {self.model}")
        print(f"🚀 并发数: {workers}")
    
    def generate_main_logic(self) -> Dict[str, Any]:
        """生成主逻辑知识图谱"""
        print("\n" + "="*60)
        print("🧠 开始主逻辑图谱生成")
        print("="*60)
        
        # 1. 加载章节数据
        sections_data = self._load_sections_data()
        if not sections_data:
            print("❌ 无法加载章节数据")
            return {}
        
        # 2. 使用CoT方法分析章节关系
        analysis_result = self._analyze_sections_with_cot(sections_data['sections'])
        if not analysis_result:
            print("❌ 章节分析失败")
            return {}
        
        # 3. 构建主逻辑知识图谱
        main_logic_kg = self._build_main_logic_kg(analysis_result)
        
        # 4. 保存结果
        self._save_main_logic_kg(main_logic_kg)
        
        print(f"✅ 主逻辑图谱生成完成")
        return main_logic_kg
    
    def _load_sections_data(self) -> Dict[str, Any]:
        """加载章节数据"""
        print("📂 加载章节数据...")
        
        try:
            sections_file = file_manager.get_path("sections", "document_sections.json")
            with open(sections_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            sections = data.get('sections', [])
            print(f"✅ 成功加载 {len(sections)} 个章节")
            
            return data
            
        except Exception as e:
            print(f"❌ 加载失败: {e}")
            return {}
    
    def _analyze_sections_with_cot(self, sections: List[Dict]) -> Dict:
        """使用CoT方法分析章节"""
        print(f"\n🤔 使用CoT方法分析章节关系...")
        
        # 准备章节摘要
        section_summaries = []
        for section in sections:
            content_preview = section['content'][:800] + "..." if len(section['content']) > 800 else section['content']
            section_summaries.append({
                'section_num': section['section_num'],
                'title': section['title'],
                'content_preview': content_preview,
                'content_length': len(section['content']),
                'word_count': len(section['content'].split())
            })
        
        # 使用CoT进行分析
        analysis_result = self._call_deepseek_with_cot_analysis(section_summaries)
        
        return analysis_result
    
    @retry_on_failure(max_retries=3, delay=2.0)
    def _call_deepseek_with_cot_analysis(self, section_summaries: List[Dict]) -> Dict:
        """使用CoT方法调用DeepSeek进行章节分析"""
        
        cot_prompt = f"""你是一位资深的电路设计教育专家和知识图谱构建专家。请使用逐步思考的方法分析以下电路技术章节，构建主逻辑知识图谱。

## 第一步：章节内容理解
请逐一分析每个章节的核心内容：

章节信息：
{json.dumps(section_summaries, ensure_ascii=False, indent=2)}

### 思考过程：
1. 每个章节的主要技术主题是什么？
2. 每个章节的难度层级如何？
3. 每个章节的学习目标是什么？
4. 每个章节需要哪些前置知识？

## 第二步：知识层次分析
请将章节按照电路学习的逻辑层次进行分类：

### 思考框架：
- **基础理论层**：基本概念、原理、数学基础
- **器件技术层**：具体器件、特性、模型
- **电路设计层**：电路拓扑、设计方法、分析技巧
- **系统应用层**：完整系统、实际应用、工程实践
- **高级优化层**：性能优化、先进技术、创新方法

## 第三步：依赖关系识别
请分析章节间的逻辑依赖关系：

### 关系类型定义：
- **depends_on**：必须先学习A才能理解B
- **builds_on**：B是A的进阶和扩展
- **applies_to**：A的技术在B中得到应用
- **complements**：A和B相互补充
- **parallel_to**：A和B可以并行学习
- **cross_references**：A和B在某些概念上有交集

## 第四步：学习路径规划
基于依赖关系，设计最优的学习路径。

## 第五步：知识图谱构建
基于以上分析，构建结构化的主逻辑知识图谱。

请严格按照以下JSON格式返回：

```json
{{
  "analysis_summary": {{
    "total_sections": {len(section_summaries)},
    "analysis_timestamp": "{datetime.now().isoformat()}",
    "complexity_distribution": {{
      "basic": 0,
      "intermediate": 0,
      "advanced": 0
    }},
    "main_themes": ["主题1", "主题2", "主题3"]
  }},
  "knowledge_hierarchy": {{
    "基础理论层": ["章节号1", "章节号2"],
    "器件技术层": ["章节号3", "章节号4"],
    "电路设计层": ["章节号5", "章节号6"],
    "系统应用层": ["章节号7", "章节号8"],
    "高级优化层": ["章节号9", "章节号10"]
  }},
  "main_knowledge_points": [
    {{
      "id": "main_1",
      "section_num": "章节号",
      "label": "章节标题",
      "summary": "章节核心内容概述",
      "difficulty": 3,
      "knowledge_layer": "电路设计层",
      "key_concepts": ["概念1", "概念2"],
      "prerequisites": ["前置章节1", "前置章节2"],
      "learning_objectives": ["目标1", "目标2"]
    }}
  ],
  "section_relationships": [
    {{
      "source_id": "main_1",
      "target_id": "main_2",
      "relationship": "depends_on",
      "description": "详细描述依赖关系",
      "weight": 0.8,
      "reasoning": "推理过程"
    }}
  ],
  "learning_paths": [
    {{
      "path_name": "基础到应用路径",
      "description": "从基础理论到实际应用的学习路径",
      "sections_sequence": ["1.1", "1.2", "2.1", "3.1"],
      "estimated_duration": "4周",
      "difficulty_progression": "递增"
    }}
  ]
}}
```

要求：
1. 每个章节都要分析到
2. 关系要基于实际的技术逻辑
3. 学习路径要合理可行
4. JSON格式要严格正确

开始分析："""
        
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "你是一位资深的电路设计教育专家和知识图谱构建专家。请仔细分析章节间的逻辑关系，构建合理的学习路径。"},
                    {"role": "user", "content": cot_prompt}
                ],
                model=self.model,
                temperature=0.1,
                max_tokens=8000
            )
            
            result_content = response.choices[0].message.content.strip()
            
            # 解析JSON结果
            json_str = self._clean_json_response(result_content)
            analysis_data = json.loads(json_str)
            
            return analysis_data
            
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            print(f"原始响应: {result_content[:500]}...")
            return {}
            
        except Exception as e:
            print(f"AI分析失败: {e}")
            return {}
    
    def _clean_json_response(self, content: str) -> str:
        """清理JSON响应"""
        # 移除markdown代码块标记
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*$', '', content)
        
        # 移除多余的空白字符
        content = content.strip()
        
        # 尝试找到JSON对象的开始和结束
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            content = content[start_idx:end_idx+1]
        
        return content
    
    def _build_main_logic_kg(self, analysis_result: Dict) -> Dict[str, Any]:
        """构建主逻辑知识图谱"""
        print("🔨 构建主逻辑知识图谱...")
        
        main_logic_kg = {
            'title': '主逻辑知识图谱',
            'timestamp': datetime.now().isoformat(),
            'nodes': analysis_result.get('main_knowledge_points', []),
            'edges': analysis_result.get('section_relationships', []),
            'knowledge_hierarchy': analysis_result.get('knowledge_hierarchy', {}),
            'learning_paths': analysis_result.get('learning_paths', []),
            'metadata': {
                'generator': 'MainLogicGenerator',
                'analysis_summary': analysis_result.get('analysis_summary', {}),
                'total_nodes': len(analysis_result.get('main_knowledge_points', [])),
                'total_edges': len(analysis_result.get('section_relationships', []))
            }
        }
        
        print(f"✅ 主逻辑知识图谱构建完成")
        print(f"   - 节点数: {len(main_logic_kg['nodes'])}")
        print(f"   - 边数: {len(main_logic_kg['edges'])}")
        print(f"   - 学习路径: {len(main_logic_kg['learning_paths'])}")
        
        return main_logic_kg
    
    def _save_main_logic_kg(self, main_logic_kg: Dict[str, Any]):
        """保存主逻辑知识图谱"""
        print("💾 保存主逻辑知识图谱...")
        
        # 保存完整的主逻辑图谱
        file_manager.save_json(main_logic_kg, "main_logic", "main_logic_kg.json")
        
        # 保存节点和边的单独文件
        file_manager.save_json(main_logic_kg['nodes'], "main_logic", "main_logic_nodes.json")
        file_manager.save_json(main_logic_kg['edges'], "main_logic", "main_logic_edges.json")
        
        # 保存学习路径
        file_manager.save_json(main_logic_kg['learning_paths'], "main_logic", "learning_paths.json")
        
        print(f"✅ 主逻辑知识图谱保存完成")

def main():
    """测试函数"""
    generator = MainLogicGenerator(workers=8)
    
    # 生成主逻辑图谱
    result = generator.generate_main_logic()
    
    if result:
        print(f"生成成功: {len(result.get('nodes', []))} 个节点")
    else:
        print("生成失败")

if __name__ == "__main__":
    main()
