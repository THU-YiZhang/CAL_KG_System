"""
Enhanced Think Agent Team for CT-MA System.

Provides detailed thinking with LlamaIndex RAG support and agent team execution.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional

from .base_agent import BaseAgent
from ..rag.llamaindex_retriever import LlamaIndexRetriever


class EnhancedThinkAgent(BaseAgent):
    """Enhanced Think Agent with LlamaIndex RAG support."""
    
    def __init__(self, config, llamaindex_retriever: LlamaIndexRetriever, agent_name: str = "enhanced_think_agent"):
        """
        Initialize Enhanced Think Agent.
        
        Args:
            config: Configuration manager
            llamaindex_retriever: LlamaIndex retriever instance
            agent_name: Name of the agent
        """
        super().__init__(config, agent_name)
        self.llamaindex_retriever = llamaindex_retriever
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute enhanced thinking analysis.
        
        Args:
            input_data: Contains 'logic', 'subgraph', and 'evidence_package'
            
        Returns:
            Dictionary with enhanced thinking result
        """
        start_time = time.time()
        success = False
        
        try:
            logic = input_data.get('logic', '')
            subgraph = input_data.get('subgraph', {})
            evidence_package = input_data.get('evidence_package', {})
            
            if not logic:
                raise ValueError("No logic provided for thinking analysis")
            
            app_label = subgraph.get('application_label', 'unknown')
            self.logger.info(f"Enhanced thinking analysis for: {app_label}")
            
            # Generate enhanced thinking with RAG support
            think_content = await self._generate_enhanced_thinking(logic, subgraph, evidence_package)
            
            # Validate and extract thinking
            if not self._validate_output_format(think_content, ['think']):
                raise ValueError("Think output does not contain required <think> tags")
            
            extracted_think = self._extract_tagged_content(think_content, 'think')
            
            if not extracted_think:
                raise ValueError("No think content extracted")
            
            success = True
            result = {
                'success': True,
                'think': extracted_think,
                'raw_output': think_content,
                'agent': self.agent_name,
                'execution_time': time.time() - start_time,
                'rag_references_count': think_content.count('RAG证据')
            }

            self.logger.info(f"Enhanced thinking analysis completed for {app_label}")
            return result

        except Exception as e:
            self.logger.error(f"Enhanced thinking analysis failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'agent': self.agent_name,
                'execution_time': time.time() - start_time
            }
        finally:
            self._log_execution_metrics(start_time, success)
    
    async def _generate_enhanced_thinking(
        self, 
        logic: str, 
        subgraph: Dict[str, Any], 
        evidence_package: Dict[str, Any]
    ) -> str:
        """Generate enhanced thinking with RAG support."""
        
        # Extract key technical terms and concepts for RAG retrieval
        technical_terms = self._extract_technical_terms(logic, subgraph)
        
        # Retrieve relevant content from books for each reasoning step
        rag_contexts = await self._retrieve_rag_contexts(technical_terms)
        
        # Build enhanced thinking prompt
        prompt = self._build_enhanced_thinking_prompt(logic, subgraph, evidence_package, rag_contexts)
        
        # Prepare messages
        system_message = self._build_enhanced_system_message()
        user_message = self._build_user_message(prompt)
        
        messages = [system_message, user_message]
        
        # Call LLM
        response = await self._call_llm(messages)
        
        return response
    
    def _extract_technical_terms(self, logic: str, subgraph: Dict[str, Any]) -> List[str]:
        """Extract technical terms for RAG retrieval."""
        terms = []
        
        # Extract from logic content
        if '【支撑路径】' in logic:
            path_section = logic.split('【支撑路径】')[1].split('【')[0]
            # Extract terms in brackets
            import re
            bracket_terms = re.findall(r'\[([^\]]+)\]', path_section)
            terms.extend([term for term in bracket_terms if term not in ['基础概念', '核心技术', '应用']])
        
        # Extract from subgraph nodes
        nodes = subgraph.get('nodes', [])
        for node in nodes:
            if node.get('node_type') in ['basic_concept', 'core_technology']:
                label = node.get('label', '')
                if label and len(label) > 2:  # Filter out very short terms
                    terms.append(label)
        
        # Remove duplicates and limit to top terms
        unique_terms = list(set(terms))
        return unique_terms[:8]  # Limit to 8 terms to avoid too many API calls
    
    async def _retrieve_rag_contexts(self, technical_terms: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieve RAG contexts for technical terms."""
        rag_contexts = {}
        
        for term in technical_terms:
            try:
                # Query LlamaIndex for this term
                query = f"{term}的工作原理和技术细节"
                contexts = await self.llamaindex_retriever.get_relevant_context_for_reasoning(
                    reasoning_step=f"分析{term}的技术特性",
                    technical_terms=[term]
                )
                
                if contexts:
                    rag_contexts[term] = contexts[:2]  # Top 2 contexts per term
                
            except Exception as e:
                self.logger.warning(f"RAG retrieval failed for term '{term}': {e}")
        
        return rag_contexts
    
    def _build_enhanced_system_message(self) -> Dict[str, str]:
        """Build enhanced system message for thinking analysis."""
        system_prompt = """你是电路设计深度思维专家，专门基于逻辑分析进行精细化技术思考。

你的核心任务是：
1. 基于用户提出的logic逻辑，进行更加精细化的技术思考
2. 不仅关注知识点，更要延伸技术和概念的细节和意义
3. 结合RAG检索的原始书籍内容，提供深度技术分析和具体参数
4. 建立完整的推理链条，体现专业的工程思维

输出格式要求：
- 必须使用<think></think>标签包围全部内容
- 采用"推理开始→多个推理步骤→推理结束"的结构
- 每个推理步骤都要深入分析技术细节和工程意义

推理深度要求：
- 分析技术原理的物理机制和数学模型
- 解释设计参数的选择依据和计算方法
- 评估性能指标的实现方法和优化策略
- 讨论技术方案的优缺点和适用场景
- 考虑实际工程中的约束条件和设计权衡
- 结合RAG证据提供具体的技术参数和公式

RAG证据使用要求：
- 每个推理步骤都要引用相关的RAG证据
- 从RAG证据中提取具体的技术参数、公式、性能数据
- 解释RAG证据如何支撑当前的技术分析
- 将理论知识与实际工程应用相结合"""

        return {"role": "system", "content": system_prompt}
    
    def _build_enhanced_thinking_prompt(
        self, 
        logic: str, 
        subgraph: Dict[str, Any], 
        evidence_package: Dict[str, Any], 
        rag_contexts: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """Build enhanced thinking prompt with RAG contexts."""
        
        app_label = subgraph.get('application_label', '未知应用')
        
        # Build RAG evidence section
        rag_evidence = self._format_rag_evidence(rag_contexts)
        
        prompt = f"""请基于以下logic逻辑分析，进行更加精细化的技术思考：

【用户提出的Logic逻辑】:
{logic}

【目标应用】: {app_label}

【RAG检索的技术证据】:
{rag_evidence}

请基于用户的logic逻辑，进行深度的精细化技术思考：

<think>
推理开始。基于用户提出的逻辑分析，我需要对每个技术环节进行更深入的思考。

第一步，深入分析用户logic中提到的直接关联核心技术。用户在logic中提到了[从logic中提取的核心技术]，我需要进一步分析其技术细节和工程意义。RAG证据[引用具体证据]表明，[从RAG中提取的具体技术参数、工作原理、物理机制]。这意味着在实际设计中，[具体的设计考虑、参数选择、性能权衡]。

第二步，深化用户logic中涉及的基础概念理解。用户提到的基础概念[从logic中提取]不仅是理论基础，更有深层的工程含义。RAG证据[引用相关证据]详细解释了[具体的理论公式、物理原理、数学模型]。从工程实现角度，这要求我们[具体的设计约束、实现方法、优化策略]。

第三步，扩展分析用户logic中的其他关联技术。用户提到的其他关联技术[从logic中提取]与主要技术路径形成协同效应。RAG证据[引用相关证据]显示，[技术协同的具体机制、性能提升效果、实现复杂度]。这种技术组合的优势在于[具体的性能优势、成本效益、可靠性提升]。

第四步，综合分析用户logic的技术路径合理性。用户提出的从基础概念到核心技术再到应用实现的路径具有深层的技术逻辑。RAG证据[引用相关证据]证实了[技术演进的必然性、设计选择的合理性、性能指标的可达性]。在实际工程中，这种技术路径能够[具体的工程优势、实现可行性、市场竞争力]。

推理结束。通过对用户logic的深度分析，我认识到这种技术选择不仅在理论上合理，在工程实践中也具有很强的可操作性和优越性。
</think>

要求：
1. 严格基于用户提出的logic进行深化分析，不要偏离
2. 每个推理步骤都要结合RAG证据提供具体技术细节
3. 包含具体的技术参数、公式、性能指标、设计约束
4. 体现从理论到工程实践的深度思考
5. 推理过程要逻辑清晰、技术深入、内容充实"""

        return prompt
    
    def _format_rag_evidence(self, rag_contexts: Dict[str, List[Dict[str, Any]]]) -> str:
        """Format RAG evidence for prompt."""
        if not rag_contexts:
            return "暂无RAG检索证据"
        
        evidence_text = ""
        for term, contexts in rag_contexts.items():
            evidence_text += f"\n关于'{term}'的技术资料：\n"
            for i, context in enumerate(contexts, 1):
                content = context.get('content', '')[:200]  # Limit length
                source = context.get('source', 'unknown')
                evidence_text += f"  {i}. {content}... (来源: {source})\n"
        
        return evidence_text
    
    def _build_user_message(self, content: str) -> Dict[str, str]:
        """Build user message."""
        return {"role": "user", "content": content}
    
    def _validate_output_format(self, content: str, required_tags: List[str]) -> bool:
        """Validate that output contains required tags."""
        for tag in required_tags:
            if f"<{tag}>" not in content or f"</{tag}>" not in content:
                return False
        return True
    
    def _extract_tagged_content(self, content: str, tag: str) -> str:
        """Extract content between specified tags."""
        start_tag = f"<{tag}>"
        end_tag = f"</{tag}>"
        
        start_idx = content.find(start_tag)
        end_idx = content.find(end_tag)
        
        if start_idx == -1 or end_idx == -1:
            return ""
        
        start_idx += len(start_tag)
        return content[start_idx:end_idx].strip()
    
    def _log_execution_metrics(self, start_time: float, success: bool) -> None:
        """Log execution metrics."""
        execution_time = time.time() - start_time
        status = "success" if success else "failed"
        self.logger.info(f"{self.agent_name} execution completed in {execution_time:.2f}s, status: {status}")


class EnhancedThinkTeamCoordinator:
    """Coordinates enhanced think agent team."""
    
    def __init__(self, config, llamaindex_retriever: LlamaIndexRetriever):
        """Initialize think team coordinator."""
        self.config = config
        self.llamaindex_retriever = llamaindex_retriever
        self.think_agent = None
    
    async def initialize(self):
        """Initialize think team."""
        self.think_agent = EnhancedThinkAgent(self.config, self.llamaindex_retriever)
        await self.think_agent.initialize()
    
    async def execute_enhanced_thinking(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute enhanced thinking with team coordination."""
        if not self.think_agent:
            raise RuntimeError("Think team not initialized")
        
        return await self.think_agent.execute(input_data)
