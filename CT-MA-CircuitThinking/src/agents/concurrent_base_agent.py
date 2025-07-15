"""
Concurrent Base Agent for CT-MA System.

Optimized base agent with 8-concurrent API call support.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional
from openai import AsyncOpenAI

from ..utils.logger import LoggerMixin
from ..utils.config_manager import ConfigManager


class ConcurrentBaseAgent(LoggerMixin):
    """并发优化的基础Agent类"""
    
    # 全局并发控制
    _global_semaphore = None
    _api_call_count = 0
    _concurrent_call_count = 0
    
    @classmethod
    def set_global_concurrency(cls, max_concurrent: int = 8):
        """设置全局并发限制"""
        cls._global_semaphore = asyncio.Semaphore(max_concurrent)
    
    def __init__(self, config: ConfigManager, agent_name: str):
        """
        初始化并发基础Agent
        
        Args:
            config: 配置管理器
            agent_name: Agent名称
        """
        self.config = config
        self.agent_name = agent_name
        self.client = None
        
        # 确保全局并发控制已设置
        if self._global_semaphore is None:
            self.set_global_concurrency()
    
    async def initialize(self) -> None:
        """初始化Agent"""
        self.logger.info(f"正在初始化 {self.agent_name}...")
        
        api_key = self.config.get("models.llm.api_key")
        base_url = self.config.get("models.llm.base_url")
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        self.logger.info(f"{self.agent_name} 初始化完成")
    
    async def _call_llm_with_concurrency(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        并发控制的LLM调用
        
        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            LLM响应内容
        """
        if not self.client:
            raise RuntimeError(f"{self.agent_name} 未初始化")
        
        if model is None:
            model = self.config.get("models.llm.model", "DMXAPI-DeepSeek-V3")
        
        # 使用全局并发控制
        async with self._global_semaphore:
            # 更新计数器
            self.__class__._api_call_count += 1
            self.__class__._concurrent_call_count += 1
            
            call_start_time = time.time()
            
            try:
                self.logger.debug(f"{self.agent_name} 开始API调用 (并发数: {self._concurrent_call_count})")
                
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                call_duration = time.time() - call_start_time
                content = response.choices[0].message.content
                
                self.logger.debug(f"{self.agent_name} API调用完成，耗时 {call_duration:.2f}s，响应长度 {len(content)} 字符")
                
                return content
                
            except Exception as e:
                call_duration = time.time() - call_start_time
                self.logger.error(f"{self.agent_name} API调用失败，耗时 {call_duration:.2f}s：{e}")
                raise
            finally:
                # 减少并发计数
                self.__class__._concurrent_call_count -= 1
    
    def _build_system_message(self, content: str) -> Dict[str, str]:
        """构建系统消息"""
        return {"role": "system", "content": content}
    
    def _build_user_message(self, content: str) -> Dict[str, str]:
        """构建用户消息"""
        return {"role": "user", "content": content}
    
    def _validate_output_format(self, content: str, required_tags: List[str]) -> bool:
        """验证输出格式"""
        for tag in required_tags:
            if f"<{tag}>" not in content or f"</{tag}>" not in content:
                return False
        return True
    
    def _extract_tagged_content(self, content: str, tag: str) -> str:
        """提取标签内容"""
        start_tag = f"<{tag}>"
        end_tag = f"</{tag}>"
        
        start_idx = content.find(start_tag)
        end_idx = content.find(end_tag)
        
        if start_idx == -1 or end_idx == -1:
            return ""
        
        start_idx += len(start_tag)
        return content[start_idx:end_idx].strip()
    
    @classmethod
    def get_api_statistics(cls) -> Dict[str, Any]:
        """获取API调用统计"""
        return {
            'total_api_calls': cls._api_call_count,
            'current_concurrent_calls': cls._concurrent_call_count,
            'max_concurrent_limit': cls._global_semaphore._value if cls._global_semaphore else 0
        }
    
    @classmethod
    def reset_api_statistics(cls):
        """重置API调用统计"""
        cls._api_call_count = 0
        cls._concurrent_call_count = 0


class ConcurrentQuestionAgent(ConcurrentBaseAgent):
    """并发优化的问题生成Agent"""
    
    def __init__(self, config: ConfigManager, agent_type: str):
        """初始化问题生成Agent"""
        super().__init__(config, f"question_{agent_type}_agent")
        self.agent_type = agent_type
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行问题生成"""
        subgraph = input_data.get('subgraph')
        if not subgraph:
            raise ValueError("未提供子图数据")
        
        start_time = time.time()
        
        try:
            # 构建提示
            prompt = self._build_question_prompt(subgraph)
            
            # 构建消息
            system_message = self._build_system_message(self._get_system_prompt())
            user_message = self._build_user_message(prompt)
            
            # 并发调用LLM
            response = await self._call_llm_with_concurrency(
                messages=[system_message, user_message],
                temperature=0.8,
                max_tokens=1500
            )
            
            # 解析问题
            questions = self._parse_questions(response)
            
            execution_time = time.time() - start_time
            
            return {
                'agent_type': self.agent_type,
                'questions': questions,
                'raw_output': response,
                'execution_time': execution_time
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"{self.agent_name} 执行失败，耗时 {execution_time:.2f}s：{e}")
            raise
    
    def _get_system_prompt(self) -> str:
        """获取系统提示"""
        if self.agent_type == "complexity":
            return """你是电路复杂度分析专家，专门设计多跳推理问题来测试对电路复杂性的理解。
重点关注技术复杂度、实现难度、性能权衡等方面。"""
        elif self.agent_type == "logic":
            return """你是电路逻辑推理专家，专门设计需要多步逻辑推理的复杂问题。
重点关注因果逻辑、技术演进必然性、设计决策合理性等方面。"""
        elif self.agent_type == "application":
            return """你是电路应用专家，专门设计实际应用导向的多跳推理问题。
重点关注实际需求、系统设计、优化改进等方面。"""
        else:
            return "你是电路设计专家，专门设计多跳推理问题。"
    
    def _build_question_prompt(self, subgraph: Dict[str, Any]) -> str:
        """构建问题生成提示"""
        app_label = subgraph.get('application_label', '未知应用')
        
        return f"""基于电路应用"{app_label}"，设计3个高质量的多跳推理问题。

要求：
1. 每个问题需要跨越至少3个技术节点进行推理
2. 问题应该具有实际工程意义
3. 包含定量分析要求
4. 体现{self.agent_type}的特点

输出格式：
<questions>
【问题1】: [具体问题描述]
【推理路径】: [技术节点A] → [技术节点B] → [技术节点C] → [结论]
【考察重点】: [主要考察的技术方面]

【问题2】: [具体问题描述]
【推理路径】: [技术节点A] → [技术节点B] → [技术节点C] → [结论]
【考察重点】: [主要考察的技术方面]

【问题3】: [具体问题描述]
【推理路径】: [技术节点A] → [技术节点B] → [技术节点C] → [结论]
【考察重点】: [主要考察的技术方面]
</questions>"""
    
    def _parse_questions(self, response: str) -> List[Dict[str, Any]]:
        """解析问题"""
        questions = []
        
        if '<questions>' in response and '</questions>' in response:
            content = response.split('<questions>')[1].split('</questions>')[0]
            
            # 分割问题块
            question_blocks = []
            current_block = ""
            
            for line in content.split('\n'):
                if line.strip().startswith('【问题'):
                    if current_block:
                        question_blocks.append(current_block)
                    current_block = line + '\n'
                else:
                    current_block += line + '\n'
            
            if current_block:
                question_blocks.append(current_block)
            
            # 解析每个问题块
            for i, block in enumerate(question_blocks, 1):
                question_data = {
                    'question_id': f"q_{i}",
                    'question_text': "",
                    'metadata': {}
                }
                
                lines = block.strip().split('\n')
                for line in lines:
                    if line.startswith('【问题'):
                        question_data['question_text'] = line.split(':', 1)[-1].strip()
                    elif '】:' in line:
                        key = line.split('】:')[0].replace('【', '')
                        value = line.split('】:')[1].strip()
                        question_data['metadata'][key] = value
                
                if question_data['question_text']:
                    questions.append(question_data)
        
        return questions


class ConcurrentQuestionCoordinator(ConcurrentBaseAgent):
    """并发优化的问题设计协调器"""
    
    def __init__(self, config: ConfigManager):
        """初始化协调器"""
        super().__init__(config, "question_coordinator")
        self.agents = {}
    
    async def initialize(self):
        """初始化所有问题生成Agent"""
        self.logger.info("正在初始化问题设计Agent团队...")
        
        agent_types = ['complexity', 'logic', 'application']
        
        # 并发初始化所有Agent
        init_tasks = []
        for agent_type in agent_types:
            agent = ConcurrentQuestionAgent(self.config, agent_type)
            self.agents[agent_type] = agent
            init_tasks.append(agent.initialize())
        
        await asyncio.gather(*init_tasks)
        
        self.logger.info("问题设计Agent团队初始化完成")
    
    async def design_questions_for_subgraph(self, subgraph: Dict[str, Any]) -> Dict[str, Any]:
        """为子图设计问题"""
        app_label = subgraph.get('application_label', 'Unknown')
        self.logger.info(f"正在为 {app_label} 设计问题...")
        
        # 并发运行所有Agent
        tasks = []
        for agent_type, agent in self.agents.items():
            task = agent.execute({'subgraph': subgraph})
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并结果
        all_questions = []
        agent_results = {}
        
        for i, (agent_type, result) in enumerate(zip(self.agents.keys(), results)):
            if isinstance(result, Exception):
                self.logger.error(f"Agent {agent_type} 失败：{result}")
                continue
            
            agent_results[agent_type] = result
            all_questions.extend(result.get('questions', []))
        
        return {
            'application': app_label,
            'total_questions': len(all_questions),
            'questions_by_type': agent_results,
            'all_questions': all_questions,
            'generated_at': time.time()
        }
