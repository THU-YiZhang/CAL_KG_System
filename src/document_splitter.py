"""
文档分割器 - 基于目录匹配正文进行内容分割
功能：智能识别目录结构，精确分割章节内容
"""

import os
import re
import json
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from openai import OpenAI
from .utils import config_manager, file_manager, logger, retry_on_failure

@dataclass
class TOCTitle:
    """目录标题"""
    section_num: str
    title: str
    page_num: str
    line_num: int

@dataclass
class ContentTitle:
    """正文标题"""
    line_num: int
    section_num: str
    title: str
    full_line: str
    title_type: str  # markdown, numbered, chapter

class DocumentSplitter:
    """文档分割器 - 基于目录匹配的智能分割"""

    def __init__(self, workers: int = 8):
        """初始化"""
        self.client = OpenAI(
            api_key="sk-pBUBTdSpfx0ppYf30rzzmbr60WiffKq52EQzx45r9rntGjli",
            base_url="https://www.dmxapi.cn/v1",
        )
        self.model = "DMXAPI-DeepSeek-V3"
        self.workers = workers

        # 分割器状态
        self.toc_titles = []
        self.content_titles = []
        self.toc_end_line = 0
        self.matched_sections = []

        print("📚 [文档分割器] 初始化完成")
        print(f"📡 使用模型: {self.model}")
        print(f"🚀 并发数: {workers}")
    
    def split_document(self, input_file: str) -> Dict[str, Any]:
        """分割文档 - 基于目录匹配的智能分割"""
        print("\n" + "="*60)
        print("📚 开始智能文档分割")
        print("="*60)
        
        try:
            # 1. 读取输入文件
            lines = self._read_input_file(input_file)
            if not lines:
                logger.error("无法读取输入文件")
                return {}
            
            # 2. 提取目录标题
            toc_titles, toc_end_line = self._extract_toc_titles(lines)
            if not toc_titles:
                logger.warning("未找到目录标题，使用简单分割")
                return self._simple_split_fallback(lines)
            
            # 3. 提取正文标题
            content_titles = self._extract_content_titles(lines, toc_end_line)
            if not content_titles:
                logger.warning("未找到正文标题，使用简单分割")
                return self._simple_split_fallback(lines)
            
            # 4. AI智能匹配目录和正文
            matched_sections = self._match_toc_with_content()
            if not matched_sections:
                logger.warning("目录和正文匹配失败，使用简单分割")
                return self._simple_split_fallback(lines)
            
            # 5. 根据匹配结果分割内容
            sections = self._split_content_by_sections(lines)
            if not sections:
                logger.error("内容分割失败")
                return {}
            
            # 6. 构建最终数据结构
            sections_data = self._build_sections_data(sections)
            
            # 7. 保存结果
            self._save_sections(sections_data)
            
            print(f"✅ 文档分割完成，共分割出 {len(sections)} 个章节")
            return sections_data
            
        except Exception as e:
            logger.error(f"文档分割失败: {e}")
            return {}
    
    def _read_input_file(self, input_file: str) -> List[str]:
        """读取输入文件并按行分割"""
        try:
            input_path = Path(input_file)
            if not input_path.exists():
                # 尝试在data/input目录中查找
                input_path = file_manager.get_path("input", input_file)
            
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            print(f"📖 成功读取文件: {input_path}")
            print(f"📊 总行数: {len(lines):,}")
            return lines
            
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            return []
    
    def _extract_toc_titles(self, lines: List[str]) -> Tuple[List[TOCTitle], int]:
        """提取目录标题，返回目录标题列表和目录结束行号"""
        print("📚 [步骤1] 提取目录标题...")
        
        toc_titles = []
        in_toc_section = False
        toc_end_line = 0
        
        # 目录标识符
        toc_indicators = ['目录', '目 录', 'Contents', 'TOC', '内容目录', '章节目录']
        
        for line_num, line in enumerate(lines):
            line_clean = line.strip()
            
            if not line_clean:
                continue
            
            # 检查是否进入目录部分
            if not in_toc_section:
                if any(indicator in line_clean for indicator in toc_indicators):
                    in_toc_section = True
                    print(f"📍 发现目录开始: 第{line_num+1}行 - {line_clean}")
                    continue
            
            # 如果在目录部分，尝试提取标题
            if in_toc_section:
                # 匹配目录格式
                patterns = [
                    r'^(\d+\.?\d*\.?\d*)\s+(.+?)\s*\.+\s*(\d+)$',  # 1.1 标题...... 页码
                    r'^(\d+\.?\d*\.?\d*)\s+(.+?)\s+(\d+)$',  # 1.1 标题 页码
                    r'^(\d+\.?\d*\.?\d*)\s+(.+)$',  # 1.1 标题 (无页码)
                    r'^第(\d+)[章节]\s+(.+?)\s*\.+\s*(\d+)$',  # 第1章 标题...... 页码
                    r'^第(\d+)[章节]\s+(.+?)\s+(\d+)$',  # 第1章 标题 页码
                    r'^第(\d+)[章节]\s+(.+)$',  # 第1章 标题
                ]
                
                matched = False
                for pattern in patterns:
                    match = re.match(pattern, line_clean)
                    if match:
                        if pattern.startswith('^第'):
                            section_num = match.group(1)
                            title = match.group(2).strip()
                            page_num = match.group(3) if len(match.groups()) >= 3 else ""
                        else:
                            section_num = match.group(1)
                            title = match.group(2).strip()
                            page_num = match.group(3) if len(match.groups()) >= 3 else ""
                        
                        # 清理标题
                        title = re.sub(r'\.+$', '', title).strip()
                        
                        if title and len(title) > 1:  # 有效标题
                            toc_title = TOCTitle(
                                section_num=section_num,
                                title=title,
                                page_num=page_num,
                                line_num=line_num + 1
                            )
                            toc_titles.append(toc_title)
                            matched = True
                            break
                
                # 检查是否目录结束
                if not matched and len(toc_titles) > 3:
                    # 连续几行都不匹配，可能目录结束了
                    if (len(line_clean) > 50 or  # 长文本
                        re.match(r'^第?\d+[章节]', line_clean) or  # 章节开始
                        re.match(r'^\d+\.\d+', line_clean) or  # 子章节开始
                        re.match(r'^#+\s', line_clean)):  # markdown标题
                        toc_end_line = line_num
                        print(f"📍 目录结束: 第{line_num+1}行")
                        break
        
        # 如果没有明确的结束标记，估算目录结束位置
        if toc_end_line == 0 and toc_titles:
            toc_end_line = toc_titles[-1].line_num + 5  # 目录最后一行后5行
        
        print(f"📊 提取目录标题: {len(toc_titles)} 个")
        print(f"📊 目录结束行: {toc_end_line}")
        
        # 显示提取的目录标题
        if toc_titles:
            print("\n📋 目录标题:")
            for i, title in enumerate(toc_titles):
                print(f"  {i+1:2d}. {title.section_num} - {title.title}")
        
        self.toc_titles = toc_titles
        self.toc_end_line = toc_end_line
        return toc_titles, toc_end_line
    
    def _extract_content_titles(self, lines: List[str], start_line: int) -> List[ContentTitle]:
        """提取正文标题（从目录结束后开始）"""
        print(f"\n🔍 [步骤2] 提取正文标题 (从第{start_line+1}行开始)...")
        
        content_titles = []
        
        for line_num in range(start_line, len(lines)):
            line_clean = lines[line_num].strip()
            
            if not line_clean or len(line_clean) < 3:
                continue
            
            # 提取各种格式的标题
            title_found = False
            
            # 1. Markdown格式标题 (# ## ### ####)
            markdown_match = re.match(r'^(#+)\s+(.+)$', line_clean)
            if markdown_match:
                hash_count = len(markdown_match.group(1))
                title = markdown_match.group(2).strip()
                
                # 尝试从title中提取章节号
                section_num = ""
                section_match = re.match(r'^(\d+\.?\d*\.?\d*)\s+(.+)$', title)
                if section_match:
                    section_num = section_match.group(1)
                    title = section_match.group(2).strip()
                else:
                    section_num = f"h{hash_count}"  # 用hash数量作为编号
                
                content_title = ContentTitle(
                    line_num=line_num + 1,
                    section_num=section_num,
                    title=title,
                    full_line=line_clean,
                    title_type="markdown"
                )
                content_titles.append(content_title)
                title_found = True
            
            # 2. 数字编号标题 (1. 1.1 1.1.1 等)
            if not title_found:
                numbered_patterns = [
                    r'^(\d+)\.\s+(.+)$',  # 1. 标题
                    r'^(\d+\.\d+)\s+(.+)$',  # 1.1 标题
                    r'^(\d+\.\d+\.\d+)\s+(.+)$',  # 1.1.1 标题
                    r'^(\d+\.\d+\.\d+\.\d+)\s+(.+)$',  # 1.1.1.1 标题
                ]
                
                for pattern in numbered_patterns:
                    match = re.match(pattern, line_clean)
                    if match:
                        section_num = match.group(1)
                        title = match.group(2).strip()
                        
                        content_title = ContentTitle(
                            line_num=line_num + 1,
                            section_num=section_num,
                            title=title,
                            full_line=line_clean,
                            title_type="numbered"
                        )
                        content_titles.append(content_title)
                        title_found = True
                        break
            
            # 3. 章节标题 (第1章 第2节等)
            if not title_found:
                chapter_patterns = [
                    r'^第(\d+)[章节]\s+(.+)$',  # 第1章 标题
                    r'^第(\d+)[章节]\s*(.*)$',  # 第1章 (可能没有标题)
                ]
                
                for pattern in chapter_patterns:
                    match = re.match(pattern, line_clean)
                    if match:
                        section_num = match.group(1)
                        title = match.group(2).strip() if match.group(2) else f"第{section_num}章"
                        
                        content_title = ContentTitle(
                            line_num=line_num + 1,
                            section_num=section_num,
                            title=title,
                            full_line=line_clean,
                            title_type="chapter"
                        )
                        content_titles.append(content_title)
                        title_found = True
                        break
        
        print(f"📊 提取正文标题: {len(content_titles)} 个")
        
        # 显示提取的正文标题
        if content_titles:
            print("\n📋 正文标题:")
            for i, title in enumerate(content_titles[:20]):  # 显示前20个
                print(f"  {i+1:2d}. 第{title.line_num:4d}行 [{title.title_type}]: {title.section_num} - {title.title}")
            if len(content_titles) > 20:
                print(f"  ... 还有 {len(content_titles) - 20} 个标题")
        
        self.content_titles = content_titles
        return content_titles

    @retry_on_failure(max_retries=3, delay=2.0)
    def _match_toc_with_content(self) -> List[Dict]:
        """使用大模型匹配目录和正文标题"""
        print(f"\n🤖 [步骤3] 使用大模型匹配目录和正文标题...")

        if not self.toc_titles or not self.content_titles:
            print("❌ 目录标题或正文标题为空")
            return []

        try:
            # 准备数据
            toc_data = [
                {
                    'section_num': toc.section_num,
                    'title': toc.title,
                    'page_num': toc.page_num
                }
                for toc in self.toc_titles
            ]

            content_data = [
                {
                    'line_num': content.line_num,
                    'section_num': content.section_num,
                    'title': content.title,
                    'full_line': content.full_line,
                    'title_type': content.title_type
                }
                for content in self.content_titles
            ]

            # 调用大模型匹配
            matches = self._call_llm_for_matching(toc_data, content_data)

            # 处理匹配结果
            matched_sections = []
            if matches:
                for match in matches:
                    try:
                        matched_sections.append({
                            'toc_section_num': match['toc_section_num'],
                            'toc_title': match['toc_title'],
                            'content_line_num': match['content_line_num'],
                            'content_section_num': match['content_section_num'],
                            'content_title': match['content_title'],
                            'confidence': match.get('confidence', 0.0)
                        })
                    except Exception as e:
                        print(f"⚠️ 解析匹配结果错误: {e}")
                        continue

            # 按行号排序
            matched_sections.sort(key=lambda x: x['content_line_num'])

            print(f"📊 匹配完成: {len(matched_sections)} 个匹配")

            # 显示匹配结果
            if matched_sections:
                print("\n🎯 匹配结果:")
                for i, match in enumerate(matched_sections):
                    print(f"  {i+1:2d}. 目录: {match['toc_section_num']} {match['toc_title']}")
                    print(f"      正文: 第{match['content_line_num']:4d}行 {match['content_section_num']} {match['content_title']}")
                    print(f"      置信度: {match['confidence']:.2f}")

            self.matched_sections = matched_sections
            return matched_sections

        except Exception as e:
            logger.error(f"匹配失败: {e}")
            return []

    def _call_llm_for_matching(self, toc_data: List[Dict], content_data: List[Dict]) -> Optional[List[Dict]]:
        """调用大模型进行匹配"""
        try:
            # 由于数据量可能很大，分批处理
            batch_size = 30
            all_matches = []

            for i in range(0, len(toc_data), batch_size):
                toc_batch = toc_data[i:i+batch_size]

                prompt = f"""
请将以下目录标题与正文标题进行匹配。

目录标题:
{json.dumps(toc_batch, ensure_ascii=False, indent=2)}

正文标题:
{json.dumps(content_data, ensure_ascii=False, indent=2)}

匹配要求:
1. 每个目录标题匹配一个最相似的正文标题
2. 优先考虑章节号的匹配，其次考虑标题内容的相似性
3. 允许格式差异（如 "1.1" 与 "## 1.1"）
4. 如果标题内容高度相似，即使章节号不同也可以匹配
5. 给出匹配置信度(0-1)，置信度低于0.5的可以不匹配

请返回JSON格式:
{{
  "matches": [
    {{
      "toc_section_num": "目录章节号",
      "toc_title": "目录标题",
      "content_line_num": 正文行号,
      "content_section_num": "正文章节号",
      "content_title": "正文标题",
      "confidence": 0.95
    }}
  ]
}}

只返回JSON，不要其他内容。
"""

                print(f"[调试] 调用API匹配第{i//batch_size + 1}批...")
                response = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "你是专业的文档分析助手。请仔细分析目录和正文标题的对应关系，严格按JSON格式返回。"},
                        {"role": "user", "content": prompt}
                    ],
                    model=self.model,
                    temperature=0.1,
                    max_tokens=8000
                )

                content = response.choices[0].message.content.strip()

                # 解析JSON - 使用改进的清理方法
                json_str = self._clean_json_response(content)
                data = json.loads(json_str)
                matches = data.get("matches", [])
                all_matches.extend(matches)
                print(f"[成功] 第{i//batch_size + 1}批匹配: {len(matches)} 个")

            return all_matches

        except Exception as e:
            print(f"[错误] 大模型匹配失败: {e}")
            return None

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

    def _split_content_by_sections(self, lines: List[str]) -> List[Dict]:
        """根据匹配结果分割内容"""
        print(f"\n✂️ [步骤4] 根据匹配结果分割内容...")

        if not self.matched_sections:
            print("❌ 没有匹配结果")
            return []

        sections = []

        for i, match in enumerate(self.matched_sections):
            start_line = match['content_line_num'] - 1  # 转为0索引

            # 确定结束行（下一个章节的开始行）
            if i < len(self.matched_sections) - 1:
                end_line = self.matched_sections[i + 1]['content_line_num'] - 1
            else:
                end_line = len(lines)

            # 提取内容
            content_lines = []
            for line_idx in range(start_line, end_line):
                if line_idx < len(lines):
                    line = lines[line_idx].strip()
                    if line:  # 只保留非空行
                        content_lines.append(line)

            # 创建章节数据
            section = {
                'section_num': match['toc_section_num'],
                'title': match['toc_title'],
                'start_line': start_line + 1,
                'end_line': end_line,
                'content': '\n'.join(content_lines)
            }

            sections.append(section)

        print(f"📊 分割完成: {len(sections)} 个章节")

        # 显示分割结果
        if sections:
            print("\n📋 章节分割:")
            for i, section in enumerate(sections):
                content_preview = section['content'][:100] + "..." if len(section['content']) > 100 else section['content']
                print(f"  {i+1:2d}. {section['section_num']} {section['title']}")
                print(f"      行数: {section['start_line']}-{section['end_line']}")
                print(f"      内容: {content_preview}")
                print()

        return sections

    def _build_sections_data(self, sections: List[Dict]) -> Dict[str, Any]:
        """构建最终数据结构"""
        return {
            'title': '智能分割文档',
            'timestamp': datetime.now().isoformat(),
            'total_sections': len(sections),
            'sections': sections,
            'metadata': {
                'splitter_method': 'toc_content_matching',
                'toc_titles_count': len(self.toc_titles),
                'content_titles_count': len(self.content_titles),
                'matched_count': len(self.matched_sections),
                'toc_end_line': self.toc_end_line
            }
        }

    def _simple_split_fallback(self, lines: List[str]) -> Dict[str, Any]:
        """简单分割降级方案"""
        print("🔧 使用简单分割作为降级方案...")

        sections = []
        current_section = None
        current_content = []
        section_count = 1

        for line_num, line in enumerate(lines):
            line_clean = line.strip()

            # 检查是否是标题行
            if re.match(r'^#+\s+', line_clean) or re.match(r'^\d+\.?\d*\.?\d*\s+', line_clean):
                # 保存前一个章节
                if current_section:
                    current_section['content'] = '\n'.join(current_content).strip()
                    if current_section['content']:
                        sections.append(current_section)

                # 开始新章节
                title = re.sub(r'^#+\s*', '', line_clean)
                title = re.sub(r'^\d+\.?\d*\.?\d*\s*', '', title)

                current_section = {
                    'section_num': str(section_count),
                    'title': title or f'章节{section_count}',
                    'start_line': line_num + 1,
                    'end_line': line_num + 1,
                    'content': ''
                }
                current_content = []
                section_count += 1
            else:
                if current_section and line_clean:
                    current_content.append(line_clean)

        # 保存最后一个章节
        if current_section:
            current_section['content'] = '\n'.join(current_content).strip()
            if current_section['content']:
                sections.append(current_section)

        return self._build_sections_data(sections)

    def _save_sections(self, sections_data: Dict[str, Any]):
        """保存分割结果"""
        print("💾 保存分割结果...")

        # 保存完整的章节数据
        file_manager.save_json(sections_data, "sections", "document_sections.json")

        # 保存每个章节的单独文件
        for i, section in enumerate(sections_data.get('sections', [])):
            section_filename = f"section_{section['section_num'].replace('.', '_')}.json"
            file_manager.save_json(section, "sections", section_filename)

        # 生成章节摘要
        summary = {
            'title': sections_data.get('title', 'Unknown'),
            'total_sections': len(sections_data.get('sections', [])),
            'sections_summary': [
                {
                    'section_num': s['section_num'],
                    'title': s['title'],
                    'content_length': len(s['content'])
                }
                for s in sections_data.get('sections', [])
            ]
        }

        file_manager.save_json(summary, "sections", "sections_summary.json")

        print(f"✅ 章节数据保存完成")

def main():
    """测试函数"""
    splitter = DocumentSplitter(workers=8)

    # 测试分割
    result = splitter.split_document("data/input/06_12CMOS模拟IP线性集成电路_吴金 (1).md")

    if result:
        print(f"分割成功: {len(result.get('sections', []))} 个章节")
    else:
        print("分割失败")

if __name__ == "__main__":
    main()
