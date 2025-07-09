"""
可视化模块
负责生成知识图谱的交互式和静态可视化
"""

import json
import os
from typing import Dict, Any, List, Tuple
from datetime import datetime
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import plotly.graph_objects as go
import plotly.offline as pyo
from pyvis.network import Network

from .utils import file_manager, logger

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

class Visualizer:
    """可视化器"""
    
    def __init__(self):
        # 层次化节点颜色配置
        self.node_colors = {
            'main_logic': '#FF6B6B',           # 红色 - 主逻辑（顶层）
            'basic_concept': '#4ECDC4',        # 青色 - 基础概念（理论层）
            'core_technology': '#45B7D1',      # 蓝色 - 核心技术（方法层）
            'circuit_application': '#96CEB4',  # 绿色 - 电路应用（应用层）
            'design_method': '#FFEAA7',       # 黄色 - 设计方法
            'analysis_tool': '#DDA0DD',       # 紫色 - 分析工具
            'unknown': '#BDC3C7'              # 灰色 - 未知类型
        }

        # 层次化边颜色配置
        self.edge_colors = {
            'main_logic': '#FF6B6B',           # 红色 - 主逻辑连接
            'contains_application': '#FF8C42', # 橙色 - 包含应用
            'enables': '#4ECDC4',              # 青色 - 使能关系
            'implements': '#45B7D1',           # 蓝色 - 实现关系
            'supports': '#96CEB4',             # 绿色 - 支撑关系
            'relates_to_application': '#9B59B6', # 紫色 - 应用关联
            'inter_section': '#E74C3C',        # 红色 - 跨章节连接
            'intra_section': '#3498DB',        # 蓝色 - 章节内连接
            'hierarchical': '#2ECC71',         # 绿色 - 层次连接
            'application_network': '#F39C12',  # 橙色 - 应用网络
            'relates_to': '#95A5A6'            # 灰色 - 一般关联
        }

        # 节点大小配置
        self.node_sizes = {
            'main_logic': 50,           # 主逻辑节点最大
            'circuit_application': 40,  # 电路应用节点较大
            'core_technology': 30,      # 核心技术节点中等
            'basic_concept': 25,        # 基础概念节点较小
            'default': 20               # 默认大小
        }
        
        logger.info("可视化器初始化完成")
    
    def generate_visualizations(self) -> bool:
        """生成所有可视化"""
        print("\n" + "="*60)
        print("📊 开始生成可视化")
        print("="*60)
        
        try:
            # 1. 构建完整知识图谱
            complete_kg = self._build_complete_knowledge_graph()
            if not complete_kg:
                logger.error("无法构建完整知识图谱")
                return False
            
            # 2. 生成交互式可视化
            self._generate_interactive_visualization(complete_kg)
            
            # 3. 生成静态可视化
            self._generate_static_visualization(complete_kg)
            
            # 4. 生成分析报告
            self._generate_analysis_report(complete_kg)
            
            print("✅ 可视化生成完成")
            return True
            
        except Exception as e:
            logger.error(f"可视化生成失败: {e}")
            return False
    
    def _build_complete_knowledge_graph(self) -> Dict[str, Any]:
        """构建完整的知识图谱 - 加载融合后的统一知识图谱"""
        print("🔄 加载统一知识图谱...")

        try:
            # 加载融合后的统一知识图谱
            unified_kg = file_manager.load_json("final", "unified_knowledge_graph.json")

            if not unified_kg:
                logger.error("无法加载统一知识图谱")
                return {}

            # 获取节点和边
            all_nodes = unified_kg.get('nodes', [])
            all_edges = unified_kg.get('edges', [])

            # 为节点添加可视化属性
            for node in all_nodes:
                node_type = node.get('node_type', 'unknown')
                node['color'] = self.node_colors.get(node_type, self.node_colors['unknown'])
                node['size'] = self.node_sizes.get(node_type, self.node_sizes['default'])
                node['level'] = node.get('level', 1)  # 层次级别

                # 根据节点类型设置形状
                if node_type == 'main_logic':
                    node['shape'] = 'diamond'
                elif node_type == 'circuit_application':
                    node['shape'] = 'box'
                elif node_type == 'core_technology':
                    node['shape'] = 'ellipse'
                else:
                    node['shape'] = 'dot'

            # 为边添加可视化属性
            for edge in all_edges:
                relationship = edge.get('relationship', 'relates_to')
                edge_type = edge.get('edge_type', 'unknown')

                # 设置边的颜色
                if relationship in self.edge_colors:
                    edge['color'] = self.edge_colors[relationship]
                elif edge_type in self.edge_colors:
                    edge['color'] = self.edge_colors[edge_type]
                else:
                    edge['color'] = self.edge_colors['relates_to']

                # 设置边的宽度（基于权重）
                weight = edge.get('weight', 0.5)
                edge['width'] = max(1, int(weight * 5))

                # 设置边的样式
                if edge_type == 'main_to_sub':
                    edge['dashes'] = False
                    edge['width'] = 3
                elif edge_type == 'hierarchical':
                    edge['dashes'] = [5, 5]
                elif edge_type == 'inter_section':
                    edge['dashes'] = [10, 5]
                else:
                    edge['dashes'] = False
            
            # 构建可视化知识图谱
            complete_kg = {
                'title': 'CAL-KG电路领域自适应逻辑知识图谱',
                'timestamp': datetime.now().isoformat(),
                'total_nodes': len(all_nodes),
                'total_edges': len(all_edges),
                'nodes': all_nodes,
                'edges': all_edges,
                'statistics': unified_kg.get('statistics', {}),
                'metadata': {
                    'node_type_distribution': self._count_node_types(all_nodes),
                    'edge_type_distribution': self._count_edge_types(all_edges),
                    'level_distribution': self._count_level_distribution(all_nodes),
                    'visualization_timestamp': datetime.now().isoformat()
                }
            }

            # 保存可视化知识图谱
            file_manager.save_json(complete_kg, "final", "visualization_knowledge_graph.json")

            print(f"✅ 统一知识图谱加载完成")
            print(f"   - 节点数: {len(all_nodes)}")
            print(f"   - 边数: {len(all_edges)}")
            print(f"   - 主逻辑节点: {unified_kg.get('statistics', {}).get('main_logic_nodes', 0)}")
            print(f"   - 基础概念节点: {unified_kg.get('statistics', {}).get('basic_concept_nodes', 0)}")
            print(f"   - 核心技术节点: {unified_kg.get('statistics', {}).get('core_technology_nodes', 0)}")
            print(f"   - 电路应用节点: {unified_kg.get('statistics', {}).get('circuit_application_nodes', 0)}")
            print(f"   - 跨章节连接: {unified_kg.get('statistics', {}).get('cross_section_edges', 0)}")

            return complete_kg
            
        except Exception as e:
            logger.error(f"构建完整知识图谱失败: {e}")
            return {}

    def _create_enhanced_node_tooltip(self, node: Dict) -> str:
        """创建增强的节点提示信息"""
        node_type = node.get('node_type', 'unknown')
        label = node.get('label', '')
        summary = node.get('summary', '')[:200] + "..." if len(node.get('summary', '')) > 200 else node.get('summary', '')
        section_num = node.get('section_num', '')
        keywords = ', '.join(node.get('keywords', [])[:5])  # 显示前5个关键词

        tooltip = f"""
<b>{label}</b><br>
<b>类型:</b> {node_type}<br>
<b>章节:</b> {section_num}<br>
<b>描述:</b> {summary}<br>
<b>关键词:</b> {keywords}<br>
<b>难度:</b> {node.get('difficulty', 'N/A')}<br>
<b>层级:</b> {node.get('level', 'N/A')}
        """.strip()

        return tooltip

    def _create_enhanced_edge_tooltip(self, edge: Dict) -> str:
        """创建增强的边提示信息"""
        relationship = edge.get('relationship', '')
        description = edge.get('description', '')
        weight = edge.get('weight', 0)
        edge_type = edge.get('edge_type', '')
        evidence = edge.get('evidence', '')

        tooltip = f"""
<b>关系:</b> {relationship}<br>
<b>类型:</b> {edge_type}<br>
<b>描述:</b> {description}<br>
<b>权重:</b> {weight:.2f}<br>
<b>证据:</b> {evidence[:100]}{'...' if len(evidence) > 100 else ''}
        """.strip()

        return tooltip

    def _get_edge_label(self, relationship: str) -> str:
        """获取边的简化标签"""
        label_mapping = {
            'contains_application': '包含',
            'enables': '使能',
            'implements': '实现',
            'supports': '支撑',
            'relates_to_application': '关联',
            'depends_on': '依赖',
            'relates_to': '相关'
        }
        return label_mapping.get(relationship, relationship[:6])

    def _count_level_distribution(self, nodes: List[Dict]) -> Dict[str, int]:
        """统计节点层级分布"""
        level_counts = {}
        for node in nodes:
            level = str(node.get('level', 'unknown'))
            level_counts[level] = level_counts.get(level, 0) + 1
        return level_counts
    
    def _generate_interactive_visualization(self, kg_data: Dict[str, Any]):
        """生成交互式可视化 - 支持中文和图例，保持完整数据"""
        print("🌐 生成交互式可视化...")

        try:
            total_nodes = len(kg_data.get('nodes', []))
            total_edges = len(kg_data.get('edges', []))

            print(f"📊 图谱规模: {total_nodes}个节点, {total_edges}个边")
            print("⚡ 使用完整数据，优化渲染性能...")

            # 创建pyvis网络 - 优化配置
            net = Network(
                height="800px",
                width="100%",
                bgcolor="#ffffff",
                font_color="black",
                directed=True,
                select_menu=False,
                filter_menu=False
            )

            # 设置高性能物理引擎和中文字体支持
            net.set_options("""
            var options = {
              "physics": {
                "enabled": true,
                "stabilization": {
                  "iterations": 30,
                  "updateInterval": 50,
                  "onlyDynamicEdges": false,
                  "fit": true
                },
                "barnesHut": {
                  "gravitationalConstant": -1000,
                  "centralGravity": 0.05,
                  "springLength": 300,
                  "springConstant": 0.01,
                  "damping": 0.2,
                  "avoidOverlap": 0.2
                },
                "maxVelocity": 20,
                "minVelocity": 1,
                "timestep": 0.5,
                "adaptiveTimestep": true
              },
              "nodes": {
                "font": {
                  "size": 10,
                  "face": "Microsoft YaHei, SimHei, Arial"
                },
                "borderWidth": 0,
                "borderWidthSelected": 1,
                "chosen": false
              },
              "edges": {
                "font": {
                  "size": 8,
                  "face": "Microsoft YaHei, SimHei, Arial"
                },
                "smooth": {
                  "enabled": false
                },
                "arrows": {
                  "to": {
                    "enabled": true,
                    "scaleFactor": 0.3
                  }
                },
                "chosen": false
              },
              "interaction": {
                "hideEdgesOnDrag": true,
                "hideNodesOnDrag": true,
                "hideEdgesOnZoom": true,
                "zoomView": true,
                "dragView": true
              },
              "layout": {
                "improvedLayout": false,
                "clusterThreshold": 150
              }
            }
            """)
            
            # 添加节点 - 高性能模式
            print(f"📝 添加 {len(kg_data.get('nodes', []))} 个节点...")
            nodes = kg_data.get('nodes', [])

            for i, node in enumerate(nodes):
                if i % 100 == 0:  # 每100个节点显示一次进度
                    print(f"   进度: {i}/{len(nodes)}")

                node_id = node.get('id', '')
                label = node.get('label', '')
                node_type = node.get('node_type', 'unknown')

                # 简化标签
                if len(label) > 15:
                    display_label = label[:15] + '...'
                else:
                    display_label = label

                # 节点颜色和大小
                color = self.node_colors.get(node_type, self.node_colors['unknown'])
                size = self.node_sizes.get(node_type, self.node_sizes['default'])

                # 最小化节点属性
                net.add_node(
                    node_id,
                    label=display_label,
                    color=color,
                    size=size,
                    title=f"{node_type}: {label}"
                )
            
            # 添加边 - 高性能模式
            print(f"🔗 添加 {len(kg_data.get('edges', []))} 个连接...")
            edges = kg_data.get('edges', [])
            edge_count = 0

            for i, edge in enumerate(edges):
                if i % 200 == 0:  # 每200个边显示一次进度
                    print(f"   进度: {i}/{len(edges)}")

                source_id = edge.get('source_id', '')
                target_id = edge.get('target_id', '')
                relationship = edge.get('relationship', 'relates_to')

                if source_id and target_id:
                    # 简化边的颜色选择
                    edge_color = self.edge_colors.get(relationship, '#95A5A6')

                    # 最小化边属性
                    net.add_edge(
                        source_id,
                        target_id,
                        color=edge_color,
                        width=1
                    )
                    edge_count += 1

            print(f"✅ 成功添加 {edge_count} 个连接")
            
            # 生成带图例的HTML文件
            output_path = file_manager.get_path("final", "interactive_graph.html")
            print("💾 保存交互式图谱...")
            self._save_interactive_graph_with_legend(net, output_path, kg_data)

            print(f"✅ 交互式可视化保存到: {output_path}")
            print("💡 提示: 如果加载缓慢，请等待物理引擎稳定化完成")

        except Exception as e:
            logger.error(f"生成交互式可视化失败: {e}")

    def _save_interactive_graph_with_legend(self, net, output_path, kg_data):
        """保存带图例的交互式图谱"""
        # 先生成基础HTML
        net.save_graph(str(output_path))

        # 读取生成的HTML文件
        with open(output_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 生成图例HTML
        legend_html = self._generate_legend_html(kg_data)

        # 在HTML中插入图例和加载提示
        # 找到body标签的位置
        body_start = html_content.find('<body>')
        if body_start != -1:
            # 添加加载提示
            loading_html = """
            <div id="loading-overlay" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                 background: rgba(255,255,255,0.9); z-index: 9999; display: flex;
                 justify-content: center; align-items: center; font-family: Microsoft YaHei;">
                <div style="text-align: center;">
                    <div style="font-size: 24px; margin-bottom: 20px;">🔄 正在加载知识图谱...</div>
                    <div style="font-size: 16px; color: #666;">
                        节点数: """ + str(kg_data.get('total_nodes', 0)) + """<br>
                        连接数: """ + str(kg_data.get('total_edges', 0)) + """<br>
                        请耐心等待物理引擎稳定化...
                    </div>
                </div>
            </div>
            <script>
                // 等待网络稳定后隐藏加载提示
                setTimeout(function() {
                    var overlay = document.getElementById('loading-overlay');
                    if (overlay) {
                        overlay.style.display = 'none';
                    }
                }, 10000); // 10秒后自动隐藏
            </script>
            """

            # 在body开始后插入加载提示和图例
            insert_pos = body_start + len('<body>')
            modified_html = (html_content[:insert_pos] +
                           loading_html +
                           legend_html +
                           html_content[insert_pos:])

            # 添加CSS样式
            css_styles = """
            <style>
                body { font-family: 'Microsoft YaHei', 'SimHei', Arial, sans-serif; }
                .legend-container {
                    position: fixed;
                    top: 10px;
                    right: 10px;
                    width: 300px;
                    background: rgba(255, 255, 255, 0.95);
                    border: 2px solid #ccc;
                    border-radius: 10px;
                    padding: 15px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    z-index: 1000;
                    max-height: 80vh;
                    overflow-y: auto;
                }
                .legend-title {
                    font-size: 18px;
                    font-weight: bold;
                    margin-bottom: 15px;
                    text-align: center;
                    color: #333;
                }
                .legend-section {
                    margin-bottom: 15px;
                }
                .legend-section-title {
                    font-size: 14px;
                    font-weight: bold;
                    margin-bottom: 8px;
                    color: #555;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 3px;
                }
                .legend-item {
                    display: flex;
                    align-items: center;
                    margin-bottom: 5px;
                    font-size: 12px;
                }
                .legend-symbol {
                    width: 20px;
                    height: 20px;
                    margin-right: 8px;
                    border: 1px solid #333;
                    display: inline-block;
                }
                .legend-line {
                    width: 30px;
                    height: 3px;
                    margin-right: 8px;
                    display: inline-block;
                }
                .toggle-legend {
                    position: fixed;
                    top: 10px;
                    right: 320px;
                    background: #007bff;
                    color: white;
                    border: none;
                    padding: 8px 12px;
                    border-radius: 5px;
                    cursor: pointer;
                    z-index: 1001;
                    font-family: 'Microsoft YaHei', 'SimHei', Arial, sans-serif;
                }
                .instructions {
                    font-size: 11px;
                    color: #666;
                    margin-top: 10px;
                    padding-top: 10px;
                    border-top: 1px solid #eee;
                }
            </style>
            """

            # 在head标签中插入CSS
            head_end = modified_html.find('</head>')
            if head_end != -1:
                modified_html = (modified_html[:head_end] +
                               css_styles +
                               modified_html[head_end:])

            # 写回文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(modified_html)

    def _generate_legend_html(self, kg_data):
        """生成图例HTML"""
        # 统计节点和边的数量
        node_stats = {}
        edge_stats = {}

        for node in kg_data.get('nodes', []):
            node_type = node.get('node_type', 'unknown')
            node_stats[node_type] = node_stats.get(node_type, 0) + 1

        for edge in kg_data.get('edges', []):
            relationship = edge.get('relationship', 'unknown')
            edge_type = edge.get('edge_type', 'unknown')
            edge_stats[relationship] = edge_stats.get(relationship, 0) + 1

        # 节点类型中文映射
        node_type_names = {
            'main_logic': '主逻辑',
            'basic_concept': '基础概念',
            'core_technology': '核心技术',
            'circuit_application': '电路应用',
            'design_method': '设计方法',
            'analysis_tool': '分析工具'
        }

        # 边类型中文映射
        edge_type_names = {
            'contains_application': '包含应用',
            'enables': '使能关系',
            'implements': '实现关系',
            'supports': '支撑关系',
            'relates_to_application': '应用关联',
            'inter_section': '跨章节连接',
            'hierarchical': '层次连接',
            'relates_to': '一般关联'
        }

        legend_html = f"""
        <button class="toggle-legend" onclick="toggleLegend()">显示/隐藏图例</button>
        <div id="legend" class="legend-container">
            <div class="legend-title">CAL-KG 知识图谱图例</div>

            <div class="legend-section">
                <div class="legend-section-title">节点类型</div>
        """

        # 添加节点类型图例
        for node_type, color in self.node_colors.items():
            if node_type in node_stats and node_stats[node_type] > 0:
                name = node_type_names.get(node_type, node_type)
                count = node_stats[node_type]
                legend_html += f"""
                <div class="legend-item">
                    <div class="legend-symbol" style="background-color: {color};"></div>
                    <span>{name} ({count}个)</span>
                </div>
                """

        legend_html += """
            </div>

            <div class="legend-section">
                <div class="legend-section-title">连接关系</div>
        """

        # 添加边类型图例
        for edge_type, color in self.edge_colors.items():
            if edge_type in edge_stats and edge_stats[edge_type] > 0:
                name = edge_type_names.get(edge_type, edge_type)
                count = edge_stats[edge_type]
                legend_html += f"""
                <div class="legend-item">
                    <div class="legend-line" style="background-color: {color};"></div>
                    <span>{name} ({count}个)</span>
                </div>
                """

        legend_html += f"""
            </div>

            <div class="instructions">
                <strong>操作说明:</strong><br>
                • 拖拽节点可移动位置<br>
                • 滚轮缩放图谱大小<br>
                • 悬停查看详细信息<br>
                • 点击节点可选中高亮<br>
                • 右键可查看菜单选项<br>
                <br>
                <strong>图谱统计:</strong><br>
                • 总节点数: {kg_data.get('total_nodes', 0)}<br>
                • 总连接数: {kg_data.get('total_edges', 0)}<br>
                • 生成时间: {kg_data.get('timestamp', 'Unknown')[:19]}
            </div>
        </div>

        <script>
            function toggleLegend() {{
                var legend = document.getElementById('legend');
                if (legend.style.display === 'none') {{
                    legend.style.display = 'block';
                }} else {{
                    legend.style.display = 'none';
                }}
            }}
        </script>
        """

        return legend_html

    def _generate_static_visualization(self, kg_data: Dict[str, Any]):
        """生成静态可视化 - 支持中文字体和完整图例"""
        print("🖼️ 生成静态可视化...")

        try:
            # 创建NetworkX图
            G = nx.DiGraph()

            # 添加节点
            for node in kg_data.get('nodes', []):
                node_id = node.get('id', '')
                G.add_node(node_id, **node)

            # 添加边
            for edge in kg_data.get('edges', []):
                source_id = edge.get('source_id', '')
                target_id = edge.get('target_id', '')
                if source_id and target_id and G.has_node(source_id) and G.has_node(target_id):
                    G.add_edge(source_id, target_id, **edge)

            # 如果图太大，只显示核心节点
            if len(G.nodes()) > 150:
                G = self._extract_core_subgraph(G, max_nodes=150)

            # 创建图形和子图布局
            fig = plt.figure(figsize=(24, 16))

            # 主图区域（左侧，占80%宽度）
            ax_main = plt.subplot2grid((1, 5), (0, 0), colspan=4)

            # 图例区域（右侧，占20%宽度）
            ax_legend = plt.subplot2grid((1, 5), (0, 4))

            # 在主图区域绘制知识图谱
            plt.sca(ax_main)

            # 计算布局
            pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

            # 定义节点类型的中文名称和形状
            node_type_info = {
                'main_logic': {'name': '主逻辑', 'shape': 'D', 'size': 800},
                'basic_concept': {'name': '基础概念', 'shape': 'o', 'size': 300},
                'core_technology': {'name': '核心技术', 'shape': 's', 'size': 500},
                'circuit_application': {'name': '电路应用', 'shape': '^', 'size': 600},
                'design_method': {'name': '设计方法', 'shape': 'v', 'size': 400},
                'analysis_tool': {'name': '分析工具', 'shape': 'p', 'size': 400}
            }

            # 绘制不同类型的节点
            for node_type, color in self.node_colors.items():
                nodes = [n for n, d in G.nodes(data=True) if d.get('node_type') == node_type]
                if nodes and node_type in node_type_info:
                    info = node_type_info[node_type]
                    nx.draw_networkx_nodes(
                        G, pos, nodelist=nodes,
                        node_color=color,
                        node_size=info['size'],
                        node_shape=info['shape'],
                        alpha=0.8,
                        edgecolors='black',
                        linewidths=1
                    )

            # 定义边类型的中文名称和样式
            edge_type_info = {
                'contains_application': {'name': '包含应用', 'style': '-', 'width': 3},
                'enables': {'name': '使能关系', 'style': '--', 'width': 2},
                'implements': {'name': '实现关系', 'style': '-', 'width': 2},
                'supports': {'name': '支撑关系', 'style': '-.', 'width': 2},
                'relates_to_application': {'name': '应用关联', 'style': ':', 'width': 1.5},
                'inter_section': {'name': '跨章节连接', 'style': '--', 'width': 1.5},
                'hierarchical': {'name': '层次连接', 'style': '-.', 'width': 1},
                'relates_to': {'name': '一般关联', 'style': '-', 'width': 1}
            }

            # 绘制不同类型的边
            for relationship, color in self.edge_colors.items():
                edges = [(u, v) for u, v, d in G.edges(data=True)
                        if d.get('relationship') == relationship or d.get('edge_type') == relationship]
                if edges and relationship in edge_type_info:
                    info = edge_type_info[relationship]
                    nx.draw_networkx_edges(
                        G, pos, edgelist=edges,
                        edge_color=color,
                        alpha=0.6,
                        arrows=True,
                        arrowsize=15,
                        width=info['width'],
                        style=info['style']
                    )

            # 添加重要节点标签
            important_nodes = self._select_important_nodes(G, max_labels=40)
            labels = {}
            for n in important_nodes:
                label = G.nodes[n].get('label', '')
                if len(label) > 12:
                    label = label[:12] + '...'
                labels[n] = label

            nx.draw_networkx_labels(G, pos, labels, font_size=9, font_family='SimHei')

            # 设置主图标题和属性
            ax_main.set_title('CAL-KG 电路领域自适应逻辑知识图谱',
                             fontsize=20, fontweight='bold', pad=20)
            ax_main.axis('off')

            # 在图例区域绘制完整图例
            self._draw_comprehensive_legend(ax_legend, node_type_info, edge_type_info, G)

            # 调整布局
            plt.tight_layout()

            # 保存静态图谱
            output_path = file_manager.get_path("final", "static_graph.png")
            plt.savefig(output_path, dpi=300, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            plt.close()

            print(f"✅ 静态可视化保存到: {output_path}")

        except Exception as e:
            logger.error(f"生成静态可视化失败: {e}")

    def _draw_comprehensive_legend(self, ax_legend, node_type_info, edge_type_info, G):
        """绘制完整的图例"""
        ax_legend.clear()
        ax_legend.set_xlim(0, 1)
        ax_legend.set_ylim(0, 1)
        ax_legend.axis('off')

        y_pos = 0.95

        # 图例标题
        ax_legend.text(0.5, y_pos, '图例说明', fontsize=16, fontweight='bold',
                      ha='center', va='top')
        y_pos -= 0.08

        # 节点类型图例
        ax_legend.text(0.05, y_pos, '节点类型:', fontsize=14, fontweight='bold',
                      ha='left', va='top')
        y_pos -= 0.05

        # 统计各类型节点数量
        node_counts = {}
        for node_type in node_type_info.keys():
            count = len([n for n, d in G.nodes(data=True) if d.get('node_type') == node_type])
            node_counts[node_type] = count

        for node_type, info in node_type_info.items():
            if node_counts.get(node_type, 0) > 0:
                color = self.node_colors.get(node_type, '#BDC3C7')
                count = node_counts[node_type]

                # 绘制节点示例
                if info['shape'] == 'D':  # 菱形
                    ax_legend.scatter(0.1, y_pos, s=100, c=color, marker='D',
                                    edgecolors='black', linewidths=1)
                elif info['shape'] == 's':  # 方形
                    ax_legend.scatter(0.1, y_pos, s=100, c=color, marker='s',
                                    edgecolors='black', linewidths=1)
                elif info['shape'] == '^':  # 三角形
                    ax_legend.scatter(0.1, y_pos, s=100, c=color, marker='^',
                                    edgecolors='black', linewidths=1)
                else:  # 圆形
                    ax_legend.scatter(0.1, y_pos, s=100, c=color, marker='o',
                                    edgecolors='black', linewidths=1)

                # 添加文字说明
                ax_legend.text(0.2, y_pos, f"{info['name']} ({count}个)",
                             fontsize=11, ha='left', va='center')
                y_pos -= 0.06

        y_pos -= 0.03

        # 边类型图例
        ax_legend.text(0.05, y_pos, '连接关系:', fontsize=14, fontweight='bold',
                      ha='left', va='top')
        y_pos -= 0.05

        # 统计各类型边数量
        edge_counts = {}
        for edge_type in edge_type_info.keys():
            count = len([(u, v) for u, v, d in G.edges(data=True)
                        if d.get('relationship') == edge_type or d.get('edge_type') == edge_type])
            edge_counts[edge_type] = count

        for edge_type, info in edge_type_info.items():
            if edge_counts.get(edge_type, 0) > 0:
                color = self.edge_colors.get(edge_type, '#95A5A6')
                count = edge_counts[edge_type]

                # 绘制线条示例
                ax_legend.plot([0.05, 0.15], [y_pos, y_pos],
                             color=color, linewidth=info['width'],
                             linestyle=info['style'], alpha=0.8)

                # 添加箭头
                ax_legend.annotate('', xy=(0.15, y_pos), xytext=(0.13, y_pos),
                                 arrowprops=dict(arrowstyle='->', color=color, lw=1))

                # 添加文字说明
                ax_legend.text(0.2, y_pos, f"{info['name']} ({count}个)",
                             fontsize=11, ha='left', va='center')
                y_pos -= 0.06

        y_pos -= 0.03

        # 节点大小说明
        ax_legend.text(0.05, y_pos, '节点大小:', fontsize=14, fontweight='bold',
                      ha='left', va='top')
        y_pos -= 0.05

        size_info = [
            ('主逻辑节点', '最大', '系统顶层逻辑'),
            ('电路应用节点', '较大', '核心应用实现'),
            ('核心技术节点', '中等', '关键技术方法'),
            ('基础概念节点', '较小', '理论基础知识')
        ]

        for name, size_desc, desc in size_info:
            ax_legend.text(0.1, y_pos, f"• {name}: {size_desc}",
                         fontsize=10, ha='left', va='center')
            y_pos -= 0.04

        y_pos -= 0.03

        # 操作说明
        ax_legend.text(0.05, y_pos, '图谱说明:', fontsize=14, fontweight='bold',
                      ha='left', va='top')
        y_pos -= 0.05

        instructions = [
            '• 节点颜色区分知识类型',
            '• 节点形状表示层次级别',
            '• 边的颜色表示关系类型',
            '• 边的样式表示连接强度',
            '• 箭头方向表示依赖关系'
        ]

        for instruction in instructions:
            ax_legend.text(0.1, y_pos, instruction, fontsize=10,
                         ha='left', va='center')
            y_pos -= 0.04

    def _generate_analysis_report(self, kg_data: Dict[str, Any]):
        """生成分析报告"""
        print("📋 生成分析报告...")
        
        try:
            metadata = kg_data.get('metadata', {})
            
            report_content = f"""# CAL-KG 知识图谱分析报告

## 📊 图谱概览

- **生成时间**: {kg_data.get('timestamp', 'Unknown')}
- **图谱标题**: {kg_data.get('title', 'Unknown')}
- **总章节数**: {kg_data.get('total_sections', 0)}
- **总节点数**: {kg_data.get('total_nodes', 0)}
- **总边数**: {kg_data.get('total_edges', 0)}
- **跨章节连接**: {kg_data.get('total_connections', 0)}

## 📈 节点类型分布

"""
            
            node_dist = metadata.get('node_type_distribution', {})
            total_nodes = sum(node_dist.values()) if node_dist else 1
            
            for node_type, count in node_dist.items():
                percentage = (count / total_nodes) * 100
                color = self.node_colors.get(node_type, '#BDC3C7')
                report_content += f"- **{node_type}**: {count} 个 ({percentage:.1f}%) `{color}`\n"
            
            report_content += f"""
## 🔗 连接类型分布

"""
            
            conn_dist = metadata.get('connection_type_distribution', {})
            total_connections = sum(conn_dist.values()) if conn_dist else 1
            
            for conn_type, count in conn_dist.items():
                percentage = (count / total_connections) * 100
                color = self.edge_colors.get(conn_type, '#95A5A6')
                report_content += f"- **{conn_type}**: {count} 个 ({percentage:.1f}%) `{color}`\n"
            
            # 分析图谱特性
            G = self._build_networkx_graph(kg_data)
            graph_metrics = self._calculate_graph_metrics(G)
            
            report_content += f"""
## 📊 图谱特性分析

### 网络拓扑特性
- **节点数**: {graph_metrics['nodes']}
- **边数**: {graph_metrics['edges']}
- **平均度**: {graph_metrics['avg_degree']:.2f}
- **图密度**: {graph_metrics['density']:.4f}
- **连通分量数**: {graph_metrics['components']}

### 中心性分析
- **度中心性最高**: {graph_metrics['top_degree_nodes'][:3]}
- **介数中心性最高**: {graph_metrics['top_betweenness_nodes'][:3]}

### 电路应用分析
- **电路应用节点数**: {graph_metrics['circuit_app_count']}
- **平均连接度**: {graph_metrics['avg_circuit_connections']:.2f}

## 📁 输出文件

### 可视化文件
- `interactive_graph.html` - 交互式网页图谱，支持缩放、拖拽、悬停查看详情
- `static_graph.png` - 静态图谱图像，适合文档展示

### 数据文件
- `knowledge_graph.json` - 完整的知识图谱数据
- `analysis_report.md` - 本分析报告

## 🎯 使用建议

1. **浏览知识图谱**: 打开 `interactive_graph.html` 进行交互式探索
2. **查看节点详情**: 在交互式图谱中悬停在节点上查看详细信息
3. **分析连接关系**: 不同颜色的边表示不同类型的知识关联
4. **学习路径规划**: 跟随 prerequisite 类型的连接构建学习路径

## 🔍 图谱特色

✅ **多层次知识结构**: 从基础概念到电路应用的完整知识层次
✅ **智能跨章节连接**: 基于电路应用的技术关联分析
✅ **丰富的节点信息**: 每个节点包含详细的技术描述和应用场景
✅ **可视化友好**: 支持交互式探索和静态展示

---
*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*CAL-KG System v1.0.0*
"""
            
            # 保存报告
            report_path = file_manager.get_path("final", "analysis_report.md")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            print(f"✅ 分析报告保存到: {report_path}")
            
        except Exception as e:
            logger.error(f"生成分析报告失败: {e}")
    
    def _calculate_node_size(self, node: Dict[str, Any]) -> int:
        """计算节点大小"""
        base_size = 20
        
        # 根据节点类型调整大小
        type_sizes = {
            'circuit_application': 30,  # 电路应用节点更大
            'core_technology': 25,
            'basic_concept': 20,
            'design_method': 20,
            'analysis_tool': 15
        }
        
        node_type = node.get('node_type', 'unknown')
        size = type_sizes.get(node_type, base_size)
        
        # 根据难度调整大小
        difficulty = node.get('difficulty', 3)
        size += difficulty * 2
        
        return min(size, 50)  # 限制最大大小
    
    def _create_node_tooltip(self, node: Dict[str, Any]) -> str:
        """创建节点悬停提示"""
        tooltip = f"""
<b>{node.get('label', 'Unknown')}</b><br>
类型: {node.get('node_type', 'unknown')}<br>
难度: {node.get('difficulty', 3)}/5<br>
章节: {node.get('source_section', 'Unknown')}<br>
<br>
<b>描述:</b><br>
{node.get('summary', 'No description')[:200]}...
<br>
<b>关键词:</b> {', '.join(node.get('keywords', [])[:5])}
"""
        return tooltip
    
    def _extract_core_subgraph(self, G: nx.DiGraph, max_nodes: int = 100) -> nx.DiGraph:
        """提取核心子图"""
        # 计算节点重要性（度中心性）
        centrality = nx.degree_centrality(G)
        
        # 选择最重要的节点
        important_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:max_nodes]
        core_nodes = [node for node, _ in important_nodes]
        
        # 创建子图
        subgraph = G.subgraph(core_nodes).copy()
        
        return subgraph
    
    def _select_important_nodes(self, G: nx.DiGraph, max_labels: int = 30) -> List[str]:
        """选择重要节点用于显示标签"""
        # 优先选择电路应用节点
        circuit_apps = [n for n, d in G.nodes(data=True) if d.get('node_type') == 'circuit_application']
        
        # 计算度中心性
        centrality = nx.degree_centrality(G)
        other_important = sorted(
            [n for n in G.nodes() if n not in circuit_apps],
            key=lambda x: centrality.get(x, 0),
            reverse=True
        )
        
        # 组合选择
        selected = circuit_apps[:max_labels//2] + other_important[:max_labels//2]
        
        return selected[:max_labels]
    
    def _build_networkx_graph(self, kg_data: Dict[str, Any]) -> nx.DiGraph:
        """构建NetworkX图用于分析"""
        G = nx.DiGraph()
        
        # 添加节点
        for node in kg_data.get('nodes', []):
            G.add_node(node.get('id', ''), **node)
        
        # 添加边
        for edge in kg_data.get('edges', []):
            source_id = edge.get('source_id', '')
            target_id = edge.get('target_id', '')
            if source_id and target_id and G.has_node(source_id) and G.has_node(target_id):
                G.add_edge(source_id, target_id, **edge)
        
        return G
    
    def _calculate_graph_metrics(self, G: nx.DiGraph) -> Dict[str, Any]:
        """计算图谱指标"""
        metrics = {
            'nodes': G.number_of_nodes(),
            'edges': G.number_of_edges(),
            'avg_degree': sum(dict(G.degree()).values()) / G.number_of_nodes() if G.number_of_nodes() > 0 else 0,
            'density': nx.density(G),
            'components': nx.number_weakly_connected_components(G)
        }
        
        # 中心性分析
        if G.number_of_nodes() > 0:
            degree_centrality = nx.degree_centrality(G)
            betweenness_centrality = nx.betweenness_centrality(G)
            
            metrics['top_degree_nodes'] = [
                G.nodes[node].get('label', node)
                for node, _ in sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:5]
            ]
            
            metrics['top_betweenness_nodes'] = [
                G.nodes[node].get('label', node)
                for node, _ in sorted(betweenness_centrality.items(), key=lambda x: x[1], reverse=True)[:5]
            ]
        else:
            metrics['top_degree_nodes'] = []
            metrics['top_betweenness_nodes'] = []
        
        # 电路应用分析
        circuit_apps = [n for n, d in G.nodes(data=True) if d.get('node_type') == 'circuit_application']
        metrics['circuit_app_count'] = len(circuit_apps)
        
        if circuit_apps:
            total_connections = sum(G.degree(app) for app in circuit_apps)
            metrics['avg_circuit_connections'] = total_connections / len(circuit_apps)
        else:
            metrics['avg_circuit_connections'] = 0
        
        return metrics
    
    def _count_node_types(self, nodes: List[Dict[str, Any]]) -> Dict[str, int]:
        """统计节点类型"""
        type_counts = {}
        for node in nodes:
            node_type = node.get('node_type', 'unknown')
            type_counts[node_type] = type_counts.get(node_type, 0) + 1
        return type_counts
    
    def _count_edge_types(self, edges: List[Dict[str, Any]]) -> Dict[str, int]:
        """统计边类型"""
        type_counts = {}
        for edge in edges:
            edge_type = edge.get('relationship', 'unknown')
            type_counts[edge_type] = type_counts.get(edge_type, 0) + 1
        return type_counts
    
    def _count_connection_types(self, connections: List[Dict[str, Any]]) -> Dict[str, int]:
        """统计连接类型"""
        type_counts = {}
        for conn in connections:
            conn_type = conn.get('connection_type', 'unknown')
            type_counts[conn_type] = type_counts.get(conn_type, 0) + 1
        return type_counts

def main():
    """测试函数"""
    visualizer = Visualizer()
    
    # 测试可视化
    success = visualizer.generate_visualizations()
    
    if success:
        print("可视化生成成功")
    else:
        print("可视化生成失败")

if __name__ == "__main__":
    main()
