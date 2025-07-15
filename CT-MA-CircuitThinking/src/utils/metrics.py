"""
Metrics Collection for CT-MA System.

Collects and tracks various performance and quality metrics.
"""

import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

from .logger import LoggerMixin
from .config_manager import ConfigManager


class MetricsCollector(LoggerMixin):
    """Collects and manages system metrics."""
    
    def __init__(self, config: Optional[ConfigManager] = None):
        """
        Initialize metrics collector.
        
        Args:
            config: Configuration manager instance
        """
        self.config = config
        self.metrics = defaultdict(list)
        self.timers = {}
        self.counters = defaultdict(int)
        self.start_time = time.time()
        
    def start_timer(self, name: str) -> None:
        """
        Start a timer.
        
        Args:
            name: Timer name
        """
        self.timers[name] = time.time()
    
    def end_timer(self, name: str) -> float:
        """
        End a timer and record the duration.
        
        Args:
            name: Timer name
            
        Returns:
            Duration in seconds
        """
        if name not in self.timers:
            self.logger.warning(f"Timer {name} not found")
            return 0.0
        
        duration = time.time() - self.timers[name]
        self.record_metric(f"timer.{name}", duration)
        del self.timers[name]
        return duration
    
    def record_metric(self, name: str, value: Any, metadata: Optional[Dict] = None) -> None:
        """
        Record a metric value.
        
        Args:
            name: Metric name
            value: Metric value
            metadata: Optional metadata
        """
        metric_entry = {
            'timestamp': datetime.now().isoformat(),
            'value': value,
            'metadata': metadata or {}
        }
        self.metrics[name].append(metric_entry)
    
    def increment_counter(self, name: str, amount: int = 1) -> None:
        """
        Increment a counter.
        
        Args:
            name: Counter name
            amount: Amount to increment
        """
        self.counters[name] += amount
        self.record_metric(f"counter.{name}", self.counters[name])
    
    def record_subgraph_metrics(self, subgraph: Dict[str, Any]) -> None:
        """
        Record metrics for a subgraph.
        
        Args:
            subgraph: Subgraph data
        """
        stats = subgraph.get('statistics', {})
        
        self.record_metric('subgraph.nodes', stats.get('total_nodes', 0))
        self.record_metric('subgraph.edges', stats.get('total_edges', 0))
        self.record_metric('subgraph.max_depth', stats.get('max_depth', 0))
        
        # Node type distribution
        node_types = stats.get('node_types', {})
        for node_type, count in node_types.items():
            self.record_metric(f'subgraph.node_type.{node_type}', count)
    
    def record_cot_metrics(self, cot_data: Dict[str, Any]) -> None:
        """
        Record metrics for CoT data.
        
        Args:
            cot_data: CoT data item
        """
        # Length metrics
        logic_length = len(cot_data.get('logic', ''))
        think_length = len(cot_data.get('think', ''))
        answer_length = len(cot_data.get('answer', ''))
        
        self.record_metric('cot.logic_length', logic_length)
        self.record_metric('cot.think_length', think_length)
        self.record_metric('cot.answer_length', answer_length)
        self.record_metric('cot.total_length', logic_length + think_length + answer_length)
        
        # Quality metrics
        self.record_metric('cot.has_all_sections', 
                          all(section in cot_data for section in ['logic', 'think', 'answer']))
        
        # Content analysis
        think_content = cot_data.get('think', '')
        rag_references = think_content.count('RAG证据')
        self.record_metric('cot.rag_references', rag_references)
    
    def record_agent_metrics(self, agent_name: str, execution_time: float, success: bool) -> None:
        """
        Record metrics for agent execution.
        
        Args:
            agent_name: Name of the agent
            execution_time: Execution time in seconds
            success: Whether execution was successful
        """
        self.record_metric(f'agent.{agent_name}.execution_time', execution_time)
        self.record_metric(f'agent.{agent_name}.success', success)
        self.increment_counter(f'agent.{agent_name}.executions')
        
        if success:
            self.increment_counter(f'agent.{agent_name}.successes')
        else:
            self.increment_counter(f'agent.{agent_name}.failures')
    
    def record_rag_metrics(self, query: str, results_count: int, retrieval_time: float) -> None:
        """
        Record metrics for RAG retrieval.
        
        Args:
            query: Search query
            results_count: Number of results returned
            retrieval_time: Time taken for retrieval
        """
        self.record_metric('rag.query_length', len(query))
        self.record_metric('rag.results_count', results_count)
        self.record_metric('rag.retrieval_time', retrieval_time)
        self.increment_counter('rag.queries')
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics.
        
        Returns:
            Dictionary of summary statistics
        """
        summary = {
            'total_runtime': time.time() - self.start_time,
            'counters': dict(self.counters),
            'metric_counts': {name: len(values) for name, values in self.metrics.items()}
        }
        
        # Calculate averages for key metrics
        for metric_name in ['cot.logic_length', 'cot.think_length', 'cot.answer_length']:
            if metric_name in self.metrics:
                values = [entry['value'] for entry in self.metrics[metric_name]]
                if values:
                    summary[f'{metric_name}_avg'] = sum(values) / len(values)
                    summary[f'{metric_name}_min'] = min(values)
                    summary[f'{metric_name}_max'] = max(values)
        
        return summary
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Generate performance report.
        
        Returns:
            Performance report
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': self.get_summary_stats(),
            'agent_performance': self._analyze_agent_performance(),
            'rag_performance': self._analyze_rag_performance(),
            'quality_metrics': self._analyze_quality_metrics()
        }
        
        return report
    
    def _analyze_agent_performance(self) -> Dict[str, Any]:
        """Analyze agent performance metrics."""
        agent_stats = {}
        
        for counter_name, count in self.counters.items():
            if counter_name.startswith('agent.') and counter_name.endswith('.executions'):
                agent_name = counter_name.split('.')[1]
                
                executions = count
                successes = self.counters.get(f'agent.{agent_name}.successes', 0)
                failures = self.counters.get(f'agent.{agent_name}.failures', 0)
                
                # Calculate average execution time
                time_metric = f'agent.{agent_name}.execution_time'
                if time_metric in self.metrics:
                    times = [entry['value'] for entry in self.metrics[time_metric]]
                    avg_time = sum(times) / len(times) if times else 0
                else:
                    avg_time = 0
                
                agent_stats[agent_name] = {
                    'executions': executions,
                    'successes': successes,
                    'failures': failures,
                    'success_rate': successes / executions if executions > 0 else 0,
                    'avg_execution_time': avg_time
                }
        
        return agent_stats
    
    def _analyze_rag_performance(self) -> Dict[str, Any]:
        """Analyze RAG performance metrics."""
        rag_stats = {}
        
        # Query statistics
        if 'rag.queries' in self.counters:
            rag_stats['total_queries'] = self.counters['rag.queries']
        
        # Average metrics
        for metric in ['rag.query_length', 'rag.results_count', 'rag.retrieval_time']:
            if metric in self.metrics:
                values = [entry['value'] for entry in self.metrics[metric]]
                if values:
                    rag_stats[f'{metric}_avg'] = sum(values) / len(values)
        
        return rag_stats
    
    def _analyze_quality_metrics(self) -> Dict[str, Any]:
        """Analyze quality metrics."""
        quality_stats = {}
        
        # CoT completeness
        if 'cot.has_all_sections' in self.metrics:
            completeness_values = [entry['value'] for entry in self.metrics['cot.has_all_sections']]
            if completeness_values:
                quality_stats['cot_completeness_rate'] = sum(completeness_values) / len(completeness_values)
        
        # RAG reference usage
        if 'cot.rag_references' in self.metrics:
            rag_ref_values = [entry['value'] for entry in self.metrics['cot.rag_references']]
            if rag_ref_values:
                quality_stats['avg_rag_references'] = sum(rag_ref_values) / len(rag_ref_values)
        
        return quality_stats
    
    def save_metrics(self, filepath: Optional[str] = None) -> None:
        """
        Save metrics to file.
        
        Args:
            filepath: Output file path
        """
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"metrics_{timestamp}.json"
        
        metrics_data = {
            'timestamp': datetime.now().isoformat(),
            'metrics': dict(self.metrics),
            'counters': dict(self.counters),
            'summary': self.get_summary_stats(),
            'performance_report': self.get_performance_report()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(metrics_data, f, ensure_ascii=False, indent=2, default=str)
        
        self.logger.info(f"Metrics saved to: {filepath}")
    
    def reset(self) -> None:
        """Reset all metrics."""
        self.metrics.clear()
        self.timers.clear()
        self.counters.clear()
        self.start_time = time.time()
