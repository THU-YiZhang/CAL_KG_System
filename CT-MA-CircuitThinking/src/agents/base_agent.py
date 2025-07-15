"""
Base Agent for CT-MA System.

Provides common functionality for all agents in the system.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from openai import AsyncOpenAI

from ..utils.logger import LoggerMixin
from ..utils.config_manager import ConfigManager


class BaseAgent(LoggerMixin, ABC):
    """Base class for all agents in the CT-MA system."""
    
    def __init__(self, config: ConfigManager, agent_name: str):
        """
        Initialize base agent.
        
        Args:
            config: Configuration manager instance
            agent_name: Name of the agent
        """
        self.config = config
        self.agent_name = agent_name
        self.client = None
        
        # Agent configuration
        self.role = config.get(f"agents.{agent_name}.role", "")
        self.goal = config.get(f"agents.{agent_name}.goal", "")
        self.backstory = config.get(f"agents.{agent_name}.backstory", "")
        self.system_prompt = config.get(f"agents.{agent_name}.system_prompt", "")
        self.max_execution_time = config.get(f"agents.{agent_name}.max_execution_time", 300)
        
        # LLM configuration
        self.model = config.get("models.llm.model", "deepseek-chat")
        self.temperature = config.get("models.llm.temperature", 0.3)
        self.max_tokens = config.get("models.llm.max_tokens", 4000)
        
    async def initialize(self) -> None:
        """Initialize the agent."""
        self.logger.info(f"Initializing {self.agent_name} agent...")
        
        # Initialize LLM client
        api_key = self.config.get("models.llm.api_key")
        base_url = self.config.get("models.llm.base_url")
        
        if not api_key:
            raise ValueError(f"API key not configured for {self.agent_name}")
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        self.logger.info(f"{self.agent_name} agent initialized")
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's main task.
        
        Args:
            input_data: Input data for the agent
            
        Returns:
            Agent execution results
        """
        pass
    
    async def _call_llm(
        self, 
        messages: List[Dict[str, str]], 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Call the language model.
        
        Args:
            messages: List of messages for the conversation
            temperature: Temperature override
            max_tokens: Max tokens override
            
        Returns:
            LLM response
        """
        if not self.client:
            raise RuntimeError("Agent not initialized")
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"LLM call failed for {self.agent_name}: {e}")
            raise
    
    def _build_system_message(self, context: Optional[str] = None) -> Dict[str, str]:
        """Build system message for the agent."""
        system_content = f"""你是{self.role}。

目标: {self.goal}

背景: {self.backstory}

{self.system_prompt}"""
        
        if context:
            system_content += f"\n\n当前任务上下文:\n{context}"
        
        return {"role": "system", "content": system_content}
    
    def _build_user_message(self, content: str) -> Dict[str, str]:
        """Build user message."""
        return {"role": "user", "content": content}
    
    async def _execute_with_timeout(self, coro, timeout: Optional[float] = None) -> Any:
        """Execute coroutine with timeout."""
        timeout = timeout or self.max_execution_time
        
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            self.logger.error(f"{self.agent_name} execution timed out after {timeout} seconds")
            raise
    
    def _validate_output_format(self, output: str, required_tags: List[str]) -> bool:
        """
        Validate that output contains required XML tags.
        
        Args:
            output: Agent output to validate
            required_tags: List of required XML tags
            
        Returns:
            True if all tags are present
        """
        for tag in required_tags:
            start_tag = f"<{tag}>"
            end_tag = f"</{tag}>"
            
            if start_tag not in output or end_tag not in output:
                self.logger.warning(f"Missing required tag: {tag}")
                return False
        
        return True
    
    def _extract_tagged_content(self, output: str, tag: str) -> str:
        """
        Extract content between XML tags.
        
        Args:
            output: Text containing XML tags
            tag: Tag name to extract
            
        Returns:
            Content between tags
        """
        start_tag = f"<{tag}>"
        end_tag = f"</{tag}>"
        
        start_idx = output.find(start_tag)
        end_idx = output.find(end_tag)
        
        if start_idx == -1 or end_idx == -1:
            return ""
        
        start_idx += len(start_tag)
        return output[start_idx:end_idx].strip()
    
    def _log_execution_metrics(self, start_time: float, success: bool) -> None:
        """Log execution metrics."""
        execution_time = time.time() - start_time
        
        self.logger.info(f"{self.agent_name} execution completed in {execution_time:.2f}s, success: {success}")
        
        # Record metrics if metrics collector is available
        if hasattr(self, 'metrics_collector') and self.metrics_collector:
            self.metrics_collector.record_agent_metrics(
                self.agent_name, execution_time, success
            )
    
    def set_metrics_collector(self, metrics_collector) -> None:
        """Set metrics collector for the agent."""
        self.metrics_collector = metrics_collector
