"""
连接分析器 - 跨章节连接分析
功能：分析电路应用节点之间的跨章节连接关系
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

class ConnectionAnalyzer:
    """连接分析器 - 跨章节连接分析"""
    
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
        self.cross_connections = []
        self.failed_pairs = []
        
        # 进度跟踪
        self.progress_tracker = None
        
        print("🔗 [连接分析器] 初始化完成")
        print(f"📡 使用模型: {self.model}")
        print(f"🚀 最大并发数: {workers}")
        print(f"🔄 最大重试次数: {self.max_retries}")
    
    def analyze_connections(self) -> List[Dict[str, Any]]:
        """分析跨章节连接"""
        print("\n" + "="*60)
        print("🔗 开始跨章节连接分析")
        print("="*60)
        
        # 1. 加载子逻辑图谱数据
        sub_logic_data = self._load_sub_logic_data()
        if not sub_logic_data:
            print("❌ 无法加载子逻辑数据")
            return []
        
        # 2. 提取电路应用节点
        circuit_apps = self._extract_circuit_applications(sub_logic_data)
        if not circuit_apps:
            print("❌ 未找到电路应用节点")
            return []
        
        # 3. 生成节点对
        node_pairs = self._generate_node_pairs(circuit_apps)
        if not node_pairs:
            print("❌ 无法生成节点对")
            return []
        
        # 4. 并发分析连接
        connections = self._analyze_concurrent(node_pairs)
        
        # 5. 验证和优化
        validated_connections = self._validate_connections(connections)
        
        # 6. 保存结果
        self._save_connections(validated_connections)
        
        print(f"✅ 跨章节连接分析完成，发现 {len(validated_connections)} 个连接")
        return validated_connections
    
    def _load_sub_logic_data(self) -> List[Dict]:
        """加载子逻辑图谱数据"""
        print("📂 加载子逻辑图谱数据...")
        
        try:
            summary_file = file_manager.get_path("sub_logic", "sub_logic_summary.json")
            with open(summary_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            sub_logic_kgs = data.get('sub_logic_kgs', [])
            print(f"✅ 成功加载 {len(sub_logic_kgs)} 个子逻辑图谱")
            
            return sub_logic_kgs
            
        except Exception as e:
            print(f"❌ 加载失败: {e}")
            return []
    
    def _extract_circuit_applications(self, sub_logic_data: List[Dict]) -> List[Dict]:
        """提取所有电路应用节点"""
        print("🔍 提取电路应用节点...")
        
        circuit_apps = []
        
        for kg in sub_logic_data:
            section_num = kg.get('section_num', '')
            title = kg.get('title', '')
            
            for node in kg.get('nodes', []):
                if node.get('node_type') == 'circuit_application':
                    app_node = {
                        'id': node.get('id', ''),
                        'label': node.get('label', ''),
                        'summary': node.get('summary', ''),
                        'keywords': node.get('keywords', []),
                        'applications': node.get('applications', []),
                        'section_num': section_num,
                        'section_title': title,
                        'difficulty': node.get('difficulty', 3)
                    }
                    circuit_apps.append(app_node)
        
        print(f"📊 提取到 {len(circuit_apps)} 个电路应用节点")
        
        # 显示部分节点
        if circuit_apps:
            print("\n📋 电路应用节点示例:")
            for i, app in enumerate(circuit_apps[:10]):
                print(f"  {i+1:2d}. [{app['section_num']}] {app['label']}")
            if len(circuit_apps) > 10:
                print(f"  ... 还有 {len(circuit_apps) - 10} 个节点")
        
        return circuit_apps
    
    def _generate_node_pairs(self, circuit_apps: List[Dict]) -> List[Tuple[Dict, Dict]]:
        """生成需要分析的节点对"""
        print("🔗 生成节点对...")
        
        node_pairs = []
        
        # 只分析不同章节的节点对
        for i, app1 in enumerate(circuit_apps):
            for j, app2 in enumerate(circuit_apps[i+1:], i+1):
                if app1['section_num'] != app2['section_num']:  # 不同章节
                    node_pairs.append((app1, app2))
        
        print(f"📊 生成 {len(node_pairs)} 个节点对")
        
        # 如果节点对太多，进行采样
        if len(node_pairs) > 1000:
            import random
            node_pairs = random.sample(node_pairs, 1000)
            print(f"⚠️ 节点对过多，随机采样 {len(node_pairs)} 个")
        
        return node_pairs
    
    def _analyze_concurrent(self, node_pairs: List[Tuple[Dict, Dict]]) -> List[Dict]:
        """并发分析节点对连接"""
        print(f"\n🚀 开始并发分析 {len(node_pairs)} 个节点对...")
        
        # 初始化进度跟踪
        self.progress_tracker = ProgressTracker(len(node_pairs), "跨章节连接分析")
        
        results = []
        
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            # 提交所有任务
            future_to_pair = {
                executor.submit(self.analyze_single_pair, pair): pair
                for pair in node_pairs
            }
            
            # 收集结果
            for future in as_completed(future_to_pair):
                pair = future_to_pair[future]
                try:
                    connection = future.result()
                    
                    if connection:
                        results.append(connection)
                    
                    # 更新进度
                    self.progress_tracker.update()
                    
                except Exception as e:
                    print(f"❌ 分析节点对时发生错误: {e}")
                    with self.results_lock:
                        self.failed_pairs.append(f"{pair[0]['id']}-{pair[1]['id']}")
                    self.progress_tracker.update()
        
        # 进度完成
        
        print(f"\n📊 并发分析完成:")
        print(f"   - 发现连接: {len(results)} 个")
        print(f"   - 失败分析: {len(self.failed_pairs)} 个")
        
        return results
    
    def analyze_single_pair(self, pair: Tuple[Dict, Dict]) -> Dict:
        """分析单个节点对的连接"""
        app1, app2 = pair
        
        # 重试机制
        for attempt in range(self.max_retries):
            try:
                connection = self._call_deepseek_for_connection_analysis(app1, app2)
                
                if connection and connection.get('has_connection', False):
                    return connection
                else:
                    return None  # 无连接
                    
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(0.5)  # 重试前等待0.5秒
        
        return None
    
    @retry_on_failure(max_retries=3, delay=1.0)
    def _call_deepseek_for_connection_analysis(self, app1: Dict, app2: Dict) -> Dict:
        """调用DeepSeek分析两个电路应用节点的连接关系"""
        
        prompt = f"""你是电路设计专家。请分析以下两个电路应用节点是否存在技术连接关系。

## 节点1
- **ID**: {app1['id']}
- **名称**: {app1['label']}
- **章节**: {app1['section_num']} - {app1['section_title']}
- **描述**: {app1['summary']}
- **关键词**: {', '.join(app1['keywords'])}
- **应用**: {', '.join(app1['applications'])}

## 节点2
- **ID**: {app2['id']}
- **名称**: {app2['label']}
- **章节**: {app2['section_num']} - {app2['section_title']}
- **描述**: {app2['summary']}
- **关键词**: {', '.join(app2['keywords'])}
- **应用**: {', '.join(app2['applications'])}

## 分析要求
请判断这两个电路应用是否存在以下类型的连接关系：

1. **技术依赖**: 一个应用依赖另一个应用的技术
2. **功能组合**: 两个应用可以组合形成更复杂的系统
3. **性能互补**: 两个应用在性能上相互补充
4. **设计相似**: 两个应用采用相似的设计方法
5. **应用场景重叠**: 两个应用在某些场景下可以互换或组合使用

## 输出格式
请严格按照以下JSON格式返回：

```json
{{
  "has_connection": true/false,
  "connection_type": "技术依赖/功能组合/性能互补/设计相似/应用场景重叠",
  "connection_strength": 0.8,
  "description": "详细描述连接关系",
  "technical_evidence": "支撑连接关系的技术证据",
  "application_scenarios": ["应用场景1", "应用场景2"],
  "benefits": "连接带来的技术或应用优势"
}}
```

要求：
1. 只有确实存在技术连接时才返回has_connection: true
2. connection_strength范围0-1，表示连接强度
3. 必须提供具体的技术证据
4. 如果没有连接，返回has_connection: false即可

开始分析："""
        
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "你是专业的电路设计专家。请仔细分析两个电路应用节点之间的技术连接关系，只有确实存在技术关联时才认为有连接。"},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                temperature=0.1,
                max_tokens=2000
            )
            
            result_content = response.choices[0].message.content.strip()
            
            # 解析JSON结果
            json_str = self._clean_json_response(result_content)
            connection_data = json.loads(json_str)
            
            # 添加节点信息
            if connection_data.get('has_connection', False):
                connection_data.update({
                    'source_id': app1['id'],
                    'target_id': app2['id'],
                    'source_section': app1['section_num'],
                    'target_section': app2['section_num'],
                    'source_label': app1['label'],
                    'target_label': app2['label'],
                    'analysis_timestamp': datetime.now().isoformat()
                })
            
            return connection_data
            
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            return {}
            
        except Exception as e:
            print(f"连接分析失败: {e}")
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
    
    def _validate_connections(self, connections: List[Dict]) -> List[Dict]:
        """验证和优化连接"""
        print(f"\n🔍 验证和优化 {len(connections)} 个连接...")
        
        validated_connections = []
        
        for conn in connections:
            if self._is_valid_connection(conn):
                validated_connections.append(conn)
        
        print(f"✅ 验证完成，有效连接: {len(validated_connections)} 个")
        return validated_connections
    
    def _is_valid_connection(self, connection: Dict) -> bool:
        """检查连接是否有效"""
        if not connection.get('has_connection', False):
            return False
        
        if not connection.get('source_id') or not connection.get('target_id'):
            return False
        
        if connection.get('connection_strength', 0) < 0.3:  # 连接强度阈值
            return False
        
        return True
    
    def _save_connections(self, connections: List[Dict]):
        """保存连接分析结果"""
        print("💾 保存连接分析结果...")
        
        # 保存汇总数据
        summary_data = {
            'title': '跨章节连接分析结果',
            'timestamp': datetime.now().isoformat(),
            'total_connections': len(connections),
            'connection_types': self._analyze_connection_types(connections),
            'connections': connections
        }
        
        file_manager.save_json(summary_data, "connections", "cross_section_connections.json")
        
        print(f"✅ 连接分析结果保存完成")
        print(f"   - 总连接数: {len(connections)}")
        
        # 显示连接类型统计
        conn_types = summary_data['connection_types']
        if conn_types:
            print("📊 连接类型分布:")
            for conn_type, count in conn_types.items():
                print(f"   - {conn_type}: {count} 个")
    
    def _analyze_connection_types(self, connections: List[Dict]) -> Dict[str, int]:
        """分析连接类型分布"""
        type_counts = {}
        
        for conn in connections:
            conn_type = conn.get('connection_type', 'unknown')
            type_counts[conn_type] = type_counts.get(conn_type, 0) + 1
        
        return type_counts

def main():
    """测试函数"""
    analyzer = ConnectionAnalyzer(workers=8)
    
    # 分析连接
    result = analyzer.analyze_connections()
    
    if result:
        print(f"分析成功: {len(result)} 个连接")
    else:
        print("分析失败")

if __name__ == "__main__":
    main()
