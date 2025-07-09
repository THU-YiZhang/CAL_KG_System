"""
子逻辑图谱生成器 - 并行版本
功能：基于章节内容构建三元组知识图谱，提取基础概念-核心技术-电路应用的层次结构
"""

import os
import json
import re
import time
from typing import List, Dict, Any, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from openai import OpenAI

from .utils import config_manager, file_manager, logger, retry_on_failure, ProgressTracker

class SubLogicGenerator:
    """子逻辑图谱生成器 - 并行版本"""
    
    def __init__(self, workers: int = 8):
        """初始化"""
        self.client = OpenAI(
            api_key="sk-pBUBTdSpfx0ppYf30rzzmbr60WiffKq52EQzx45r9rntGjli",
            base_url="https://www.dmxapi.cn/v1",
        )
        self.model = "DMXAPI-DeepSeek-V3"
        self.workers = workers
        self.max_retries = 3
        
        # 线程安全的结果存储
        self.results_lock = threading.Lock()
        self.sub_domain_kgs = []
        self.failed_sections = []
        
        # 进度跟踪
        self.progress_tracker = None
        
        print("🔬 [子逻辑生成器] 初始化完成")
        print(f"📡 使用模型: {self.model}")
        print(f"🚀 最大并发数: {workers}")
        print(f"🔄 最大重试次数: {self.max_retries}")
    
    def generate_sub_logic(self) -> List[Dict[str, Any]]:
        """生成子逻辑知识图谱"""
        print("\n" + "="*60)
        print("🔬 开始子逻辑图谱生成")
        print("="*60)
        
        # 1. 加载章节数据
        sections_data = self._load_sections_data()
        if not sections_data:
            print("❌ 无法加载章节数据")
            return []
        
        # 2. 并发提取子逻辑图谱
        sub_logic_kgs = self._extract_concurrent(sections_data['sections'])
        
        # 3. 验证和优化
        validated_kgs = self._validate_sub_logic_kgs(sub_logic_kgs)
        
        # 4. 保存结果
        self._save_sub_logic_kgs(validated_kgs)
        
        print(f"✅ 子逻辑图谱生成完成，共生成 {len(validated_kgs)} 个图谱")
        return validated_kgs
    
    def _load_sections_data(self) -> Dict[str, Any]:
        """加载章节数据"""
        print("📂 加载章节数据...")
        
        try:
            sections_file = file_manager.get_path("sections", "document_sections.json")
            with open(sections_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            sections = data.get('sections', [])
            print(f"✅ 成功加载 {len(sections)} 个章节")
            
            # 过滤掉内容太短的章节
            filtered_sections = []
            for section in sections:
                if len(section.get('content', '')) > 200:  # 至少200字符
                    filtered_sections.append(section)
                else:
                    print(f"⚠️ 跳过内容过短的章节: {section['section_num']}")
            
            print(f"📋 过滤后有效章节: {len(filtered_sections)} 个")
            data['sections'] = filtered_sections
            return data
            
        except Exception as e:
            print(f"❌ 加载失败: {e}")
            return {}
    
    def _extract_concurrent(self, sections: List[Dict]) -> List[Dict]:
        """并发提取子逻辑图谱"""
        print(f"\n🚀 开始并发处理 {len(sections)} 个章节...")
        
        # 初始化进度跟踪
        self.progress_tracker = ProgressTracker(len(sections), "子逻辑图谱提取")
        
        results = []
        
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            # 提交所有任务
            future_to_section = {
                executor.submit(self.process_single_section, section): section
                for section in sections
            }
            
            # 收集结果
            for future in as_completed(future_to_section):
                section = future_to_section[future]
                try:
                    section_data, analysis_data, success = future.result()
                    
                    if success and analysis_data:
                        # 构建知识图谱格式
                        kg_data = self._build_kg_from_analysis(analysis_data, section_data['section_num'], section_data['title'])
                        if kg_data:
                            kg_data['section_num'] = section_data['section_num']
                            kg_data['title'] = section_data['title']
                            kg_data['extraction_timestamp'] = datetime.now().isoformat()
                            results.append(kg_data)
                    else:
                        with self.results_lock:
                            self.failed_sections.append(section_data['section_num'])
                    
                    # 更新进度
                    self.progress_tracker.update()
                    
                except Exception as e:
                    print(f"❌ 处理章节 {section['section_num']} 时发生错误: {e}")
                    with self.results_lock:
                        self.failed_sections.append(section['section_num'])
                    self.progress_tracker.update()
        
        # 进度完成
        
        print(f"\n📊 并发处理完成:")
        print(f"   - 成功章节: {len(results)} 个")
        print(f"   - 失败章节: {len(self.failed_sections)} 个")
        if self.failed_sections:
            print(f"   - 失败列表: {', '.join(self.failed_sections)}")
        
        return results
    
    def process_single_section(self, section: Dict) -> Tuple[Dict, Dict, bool]:
        """处理单个章节（用于并行执行）"""
        section_num = section['section_num']
        title = section['title']
        
        print(f"🔍 [线程-{threading.current_thread().name}] 开始处理章节: {section_num}")
        
        # 重试机制
        for attempt in range(self.max_retries):
            try:
                # 分析章节
                analysis_data = self._call_deepseek_with_cot_triplet_extraction(section)
                
                if analysis_data:
                    print(f"✅ [线程-{threading.current_thread().name}] 章节 {section_num} 分析成功")
                    return section, analysis_data, True
                else:
                    print(f"⚠️ [线程-{threading.current_thread().name}] 章节 {section_num} 分析失败，尝试 {attempt + 1}/{self.max_retries}")
                    
            except Exception as e:
                print(f"❌ [线程-{threading.current_thread().name}] 章节 {section_num} 处理错误 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(1)  # 重试前等待1秒
        
        print(f"❌ [线程-{threading.current_thread().name}] 章节 {section_num} 最终失败")
        return section, {}, False
    
    def _call_deepseek_with_cot_triplet_extraction(self, section: Dict) -> Dict:
        """使用CoT方法调用DeepSeek进行三元组知识提取"""
        
        # 安全的章节号处理
        section_num_safe = re.sub(r'[^\w]', '_', str(section['section_num']))
        
        # 限制内容长度，避免token过多
        content = section['content']
        if len(content) > 16000:
            content = content[:16000] + "..."
        
        cot_prompt = f"""你是一位资深的电路设计专家和知识工程师。请使用逐步思考的方法从以下电路技术章节中提取三元组知识图谱。

## 章节信息
- **章节号**: {section['section_num']}
- **标题**: {section['title']}
- **内容**: {content}

## 分析任务
请按照以下步骤进行分析：

### 第一步：内容理解
仔细阅读章节内容，理解主要技术主题和知识结构。

### 第二步：知识分层提取
按照以下三个层次提取知识节点：

**1. 基础概念层 (Basic Concepts)**
- 提取：基本定义、原理、定律、公式、参数等
- 特征：理论性强，是其他知识的基础
- 要求：每个概念都要有明确的定义和解释

**2. 核心技术层 (Core Technologies)**
- 提取：实现方法、设计技巧、分析方法、算法等
- 特征：方法性强，连接理论与应用
- 要求：每个技术都要有具体的实现步骤

**3. 电路应用层 (Circuit Applications)**
- 提取：具体电路、设计实例、应用场景等
- 特征：实践性强，面向具体应用
- 要求：每个应用都要有具体的电路结构

### 第三步：关系识别
识别以下类型的知识关系：

**层间关系**：
- enables: 基础概念使能核心技术
- supports: 基础概念支撑核心技术
- implements: 核心技术实现电路应用
- applies_to: 核心技术应用于电路应用

**层内关系**：
- depends_on: 依赖关系
- relates_to: 相关关系
- complements: 互补关系
- extends: 扩展关系

### 第四步：构建知识图谱
基于上述分析，构建结构化的知识图谱。

请严格按照以下JSON格式返回：

```json
{{
  "section_analysis": {{
    "section_num": "{section['section_num']}",
    "title": "{section['title']}",
    "content_summary": "章节内容的简要概述",
    "knowledge_density": "高",
    "complexity_level": 3,
    "key_themes": ["主要技术主题1", "主要技术主题2"]
  }},
  "basic_concepts": [
    {{
      "id": "bc_{section_num_safe}_1",
      "label": "概念名称",
      "summary": "概念的详细描述，包括定义、原理、特点等",
      "difficulty": 2,
      "keywords": ["关键词1", "关键词2"],
      "formulas": ["相关公式"],
      "applications": ["应用场景"],
      "properties": {{
        "category": "定义",
        "mathematical_level": "基础",
        "prerequisite_knowledge": ["前置知识"]
      }}
    }}
  ],
  "core_technologies": [
    {{
      "id": "ct_{section_num_safe}_1",
      "label": "技术名称",
      "summary": "技术的详细描述，包括方法、步骤、优势等",
      "difficulty": 3,
      "keywords": ["技术关键词1", "技术关键词2"],
      "formulas": ["相关算法公式"],
      "applications": ["技术应用"],
      "properties": {{
        "category": "分析方法",
        "implementation_complexity": "中等",
        "required_tools": ["工具1"]
      }}
    }}
  ],
  "circuit_applications": [
    {{
      "id": "ca_{section_num_safe}_1",
      "label": "应用名称",
      "summary": "应用的详细描述，包括电路结构、功能、特点等",
      "difficulty": 4,
      "keywords": ["应用关键词1", "应用关键词2"],
      "formulas": ["设计公式"],
      "applications": ["具体应用场景"],
      "properties": {{
        "category": "电路拓扑",
        "performance_metrics": ["性能指标"],
        "design_constraints": ["设计约束"]
      }}
    }}
  ],
  "relationships": [
    {{
      "source_id": "bc_{section_num_safe}_1",
      "target_id": "ct_{section_num_safe}_1",
      "relationship": "enables",
      "description": "详细描述这种关系",
      "weight": 0.8,
      "evidence": "支撑这种关系的文本证据",
      "bidirectional": false
    }}
  ]
}}
```

要求：
1. 基础概念、核心技术、电路应用个数不限制
2. 每个节点的summary要详细且准确
3. 关系要真实存在，不能杜撰
4. 所有字段都要填写，不能为空
5. JSON格式要严格正确

开始分析："""
        
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "你是顶级的电路设计专家和知识工程师。你擅长从技术文档中提取结构化的三元组知识图谱，能够准确识别知识的层次结构和相互关系。请严格按照要求进行深入分析，确保提取的知识准确、完整、有用。"},
                    {"role": "user", "content": cot_prompt}
                ],
                model=self.model,
                temperature=0.1,
                max_tokens=8000
            )
            
            result_content = response.choices[0].message.content.strip()
            
            # 解析JSON结果 - 使用更完善的清理方法
            json_str = self._clean_json_response(result_content)
            kg_data = json.loads(json_str)
            
            return kg_data
            
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            print(f"原始响应: {result_content[:500]}...")
            # 降级到规则提取
            return self._rule_based_extraction(section['section_num'], section['title'], section['content'])
            
        except Exception as e:
            print(f"AI提取失败: {e}")
            # 降级到规则提取
            return self._rule_based_extraction(section['section_num'], section['title'], section['content'])
    
    def _clean_json_response(self, content: str) -> str:
        """清理JSON响应 - 参考您的成功代码"""
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

    def _build_kg_from_analysis(self, analysis_data: Dict[str, Any], section_num: str, title: str) -> Dict[str, Any]:
        """从分析数据构建知识图谱格式"""
        try:
            nodes = []
            edges = []

            # 处理基础概念
            for concept in analysis_data.get('basic_concepts', []):
                node = {
                    'id': concept.get('id', ''),
                    'label': concept.get('label', ''),
                    'node_type': 'basic_concept',
                    'summary': concept.get('summary', ''),
                    'difficulty': concept.get('difficulty', 2),
                    'keywords': concept.get('keywords', []),
                    'formulas': concept.get('formulas', []),
                    'applications': concept.get('applications', []),
                    'related_sections': [],
                    'prerequisites': concept.get('properties', {}).get('prerequisite_knowledge', []),
                    'derived_concepts': [],
                    'practical_examples': [],
                    'technical_details': concept.get('summary', '')[:200]
                }
                nodes.append(node)

            # 处理核心技术
            for tech in analysis_data.get('core_technologies', []):
                node = {
                    'id': tech.get('id', ''),
                    'label': tech.get('label', ''),
                    'node_type': 'core_technology',
                    'summary': tech.get('summary', ''),
                    'difficulty': tech.get('difficulty', 3),
                    'keywords': tech.get('keywords', []),
                    'formulas': tech.get('formulas', []),
                    'applications': tech.get('applications', []),
                    'related_sections': [],
                    'prerequisites': [],
                    'derived_concepts': [],
                    'practical_examples': [],
                    'technical_details': tech.get('summary', '')[:200]
                }
                nodes.append(node)

            # 处理电路应用
            for app in analysis_data.get('circuit_applications', []):
                node = {
                    'id': app.get('id', ''),
                    'label': app.get('label', ''),
                    'node_type': 'circuit_application',
                    'summary': app.get('summary', ''),
                    'difficulty': app.get('difficulty', 4),
                    'keywords': app.get('keywords', []),
                    'formulas': app.get('formulas', []),
                    'applications': app.get('applications', []),
                    'related_sections': [],
                    'prerequisites': [],
                    'derived_concepts': [],
                    'practical_examples': [],
                    'technical_details': app.get('summary', '')[:200]
                }
                nodes.append(node)

            # 处理关系
            for rel in analysis_data.get('relationships', []):
                edge = {
                    'source_id': rel.get('source_id', ''),
                    'target_id': rel.get('target_id', ''),
                    'relationship': rel.get('relationship', 'relates_to'),
                    'description': rel.get('description', ''),
                    'weight': rel.get('weight', 0.5),
                    'evidence': rel.get('evidence', ''),
                    'bidirectional': rel.get('bidirectional', False)
                }
                edges.append(edge)

            return {
                'nodes': nodes,
                'edges': edges
            }

        except Exception as e:
            print(f"构建知识图谱失败: {e}")
            return {}

    def _rule_based_extraction(self, section_num: str, title: str, content: str) -> Dict[str, Any]:
        """规则提取降级方案"""
        print(f"⚠️ 使用规则提取作为降级方案: {section_num}")

        # 简单的段落分割
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

        # 改进的关键词提取 - 更准确地识别电路应用
        circuit_terms = {
            'basic_concept': ['定义', '原理', '定律', '公式', '概念', '理论', '基础'],
            'core_technology': ['方法', '技术', '算法', '分析', '设计技巧', '实现方法'],
            'circuit_application': ['电路', '放大器', '滤波器', '振荡器', '比较器', '开关', '变换器', '应用', '实例', '设计'],
            'design_method': ['流程', '步骤', '准则', '优化', '设计方法'],
            'analysis_tool': ['仿真', '测试', '工具', '软件', 'SPICE', 'Matlab']
        }

        nodes = []
        node_id = 1

        for i, para in enumerate(paragraphs[:10]):  # 最多处理10个段落
            if len(para) < 50:  # 跳过太短的段落
                continue

            # 确定节点类型 - 改进的分类逻辑
            node_type = 'basic_concept'  # 默认类型
            type_scores = {}

            # 计算每种类型的匹配分数
            for type_name, keywords in circuit_terms.items():
                score = sum(1 for keyword in keywords if keyword in para.lower())
                type_scores[type_name] = score

            # 选择得分最高的类型
            if type_scores:
                node_type = max(type_scores, key=type_scores.get)
                # 如果没有明显匹配，保持默认
                if type_scores[node_type] == 0:
                    node_type = 'basic_concept'

            # 提取标题（段落的第一句）
            sentences = para.split('。')
            label = sentences[0][:50] + "..." if len(sentences[0]) > 50 else sentences[0]

            node = {
                'id': f"{section_num}_{node_type}_{node_id}",
                'label': label,
                'node_type': node_type,
                'summary': para[:300] + "..." if len(para) > 300 else para,
                'difficulty': 3,
                'keywords': [],
                'formulas': [],
                'applications': [],
                'related_sections': [section_num],
                'prerequisites': [],
                'derived_concepts': [],
                'practical_examples': [],
                'technical_details': para[:200]
            }

            nodes.append(node)
            node_id += 1

        return {
            'basic_concepts': [n for n in nodes if n['node_type'] == 'basic_concept'],
            'core_technologies': [n for n in nodes if n['node_type'] == 'core_technology'],
            'circuit_applications': [n for n in nodes if n['node_type'] == 'circuit_application'],
            'relationships': []
        }

    def _validate_sub_logic_kgs(self, sub_logic_kgs: List[Dict]) -> List[Dict]:
        """验证和优化子逻辑图谱"""
        print(f"\n🔍 验证和优化 {len(sub_logic_kgs)} 个子逻辑图谱...")

        validated_kgs = []

        for kg in sub_logic_kgs:
            if self._is_valid_kg(kg):
                validated_kgs.append(kg)
            else:
                print(f"⚠️ 跳过无效的知识图谱: {kg.get('section_num', 'Unknown')}")

        print(f"✅ 验证完成，有效图谱: {len(validated_kgs)} 个")
        return validated_kgs

    def _is_valid_kg(self, kg: Dict) -> bool:
        """检查知识图谱是否有效"""
        if not kg.get('nodes'):
            return False

        # 检查节点数量
        if len(kg['nodes']) < 2:
            return False

        # 检查节点完整性
        for node in kg['nodes']:
            if not node.get('id') or not node.get('label'):
                return False

        return True

    def _save_sub_logic_kgs(self, sub_logic_kgs: List[Dict]):
        """保存子逻辑图谱"""
        print("💾 保存子逻辑图谱...")

        # 保存汇总数据
        summary_data = {
            'title': '子逻辑知识图谱汇总',
            'timestamp': datetime.now().isoformat(),
            'total_kgs': len(sub_logic_kgs),
            'total_nodes': sum(len(kg.get('nodes', [])) for kg in sub_logic_kgs),
            'total_edges': sum(len(kg.get('edges', [])) for kg in sub_logic_kgs),
            'sub_logic_kgs': sub_logic_kgs
        }

        file_manager.save_json(summary_data, "sub_logic", "sub_logic_summary.json")

        # 保存每个图谱的单独文件
        for kg in sub_logic_kgs:
            section_num = kg.get('section_num', 'unknown')
            filename = f"sub_logic_{section_num.replace('.', '_')}.json"
            file_manager.save_json(kg, "sub_logic", filename)

        print(f"✅ 子逻辑图谱保存完成")
        print(f"   - 总图谱数: {len(sub_logic_kgs)}")
        print(f"   - 总节点数: {sum(len(kg.get('nodes', [])) for kg in sub_logic_kgs)}")
        print(f"   - 总边数: {sum(len(kg.get('edges', [])) for kg in sub_logic_kgs)}")

def main():
    """测试函数"""
    generator = SubLogicGenerator(workers=8)

    # 生成子逻辑图谱
    result = generator.generate_sub_logic()

    if result:
        print(f"生成成功: {len(result)} 个子逻辑图谱")
    else:
        print("生成失败")

if __name__ == "__main__":
    main()
