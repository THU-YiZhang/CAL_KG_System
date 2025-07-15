"""
Format Validator for CT-MA System.

Validates the format and structure of generated CoT data.
"""

import re
from typing import Dict, List, Any, Optional

from ..utils.logger import LoggerMixin
from ..utils.config_manager import ConfigManager


class FormatValidator(LoggerMixin):
    """Validates CoT data format and structure."""
    
    def __init__(self, config: ConfigManager):
        """
        Initialize Format Validator.
        
        Args:
            config: Configuration manager instance
        """
        self.config = config
        self.required_sections = config.get("quality.required_sections", ["logic", "think", "answer"])
        self.min_lengths = {
            'logic': config.get("quality.min_logic_length", 100),
            'think': config.get("quality.min_think_length", 500),
            'answer': config.get("quality.min_answer_length", 100)
        }
        self.max_total_length = config.get("quality.max_total_length", 5000)
    
    def validate(self, cot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate CoT data format.
        
        Args:
            cot_data: CoT data to validate
            
        Returns:
            Validation result with details
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'section_checks': {},
            'structure_checks': {},
            'length_checks': {}
        }
        
        try:
            # Check required sections
            section_result = self._check_required_sections(cot_data)
            validation_result['section_checks'] = section_result
            
            if not section_result['all_present']:
                validation_result['is_valid'] = False
                validation_result['errors'].extend(section_result['missing_sections'])
            
            # Check section structure
            structure_result = self._check_section_structure(cot_data)
            validation_result['structure_checks'] = structure_result
            
            if not structure_result['all_valid']:
                validation_result['warnings'].extend(structure_result['structure_issues'])
            
            # Check lengths
            length_result = self._check_lengths(cot_data)
            validation_result['length_checks'] = length_result
            
            if not length_result['all_valid']:
                validation_result['is_valid'] = False
                validation_result['errors'].extend(length_result['length_errors'])
            
            # Check metadata
            metadata_result = self._check_metadata(cot_data)
            if not metadata_result['is_valid']:
                validation_result['warnings'].extend(metadata_result['issues'])
            
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
            self.logger.error(f"Format validation failed: {e}")
        
        return validation_result
    
    def _check_required_sections(self, cot_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if all required sections are present."""
        missing_sections = []
        present_sections = []
        
        for section in self.required_sections:
            if section in cot_data and cot_data[section]:
                present_sections.append(section)
            else:
                missing_sections.append(f"Missing section: {section}")
        
        return {
            'all_present': len(missing_sections) == 0,
            'present_sections': present_sections,
            'missing_sections': missing_sections,
            'section_count': len(present_sections)
        }
    
    def _check_section_structure(self, cot_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check the internal structure of each section."""
        structure_issues = []
        section_structures = {}
        
        # Check logic section structure
        if 'logic' in cot_data:
            logic_check = self._validate_logic_structure(cot_data['logic'])
            section_structures['logic'] = logic_check
            if not logic_check['is_valid']:
                structure_issues.extend(logic_check['issues'])
        
        # Check think section structure
        if 'think' in cot_data:
            think_check = self._validate_think_structure(cot_data['think'])
            section_structures['think'] = think_check
            if not think_check['is_valid']:
                structure_issues.extend(think_check['issues'])
        
        # Check answer section structure
        if 'answer' in cot_data:
            answer_check = self._validate_answer_structure(cot_data['answer'])
            section_structures['answer'] = answer_check
            if not answer_check['is_valid']:
                structure_issues.extend(answer_check['issues'])
        
        return {
            'all_valid': len(structure_issues) == 0,
            'structure_issues': structure_issues,
            'section_structures': section_structures
        }
    
    def _validate_logic_structure(self, logic_content: str) -> Dict[str, Any]:
        """Validate logic section structure."""
        required_elements = ['目标应用', '关键瓶颈', '支撑路径', '因果链']
        issues = []
        found_elements = []
        
        for element in required_elements:
            pattern = f'【{element}】'
            if pattern in logic_content:
                found_elements.append(element)
            else:
                issues.append(f"Logic missing element: {element}")
        
        # Check for support path structure
        path_pattern = r'\d+\.\s*\[.*?\]\s*.*'
        path_matches = re.findall(path_pattern, logic_content)
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'found_elements': found_elements,
            'support_path_items': len(path_matches)
        }
    
    def _validate_think_structure(self, think_content: str) -> Dict[str, Any]:
        """Validate think section structure."""
        issues = []
        
        # Check for reasoning steps
        step_patterns = ['第一步', '第二步', '第三步', '第四步']
        found_steps = []
        
        for step in step_patterns:
            if step in think_content:
                found_steps.append(step)
        
        if len(found_steps) < 3:
            issues.append(f"Think section has insufficient reasoning steps: {len(found_steps)}")
        
        # Check for RAG references
        rag_pattern = r'RAG证据\[.*?\]'
        rag_matches = re.findall(rag_pattern, think_content)
        
        if len(rag_matches) < 3:
            issues.append(f"Think section has insufficient RAG references: {len(rag_matches)}")
        
        # Check for conclusion
        conclusion_patterns = ['推理结束', '通过层层递进']
        has_conclusion = any(pattern in think_content for pattern in conclusion_patterns)
        
        if not has_conclusion:
            issues.append("Think section missing conclusion")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'reasoning_steps': len(found_steps),
            'rag_references': len(rag_matches),
            'has_conclusion': has_conclusion
        }
    
    def _validate_answer_structure(self, answer_content: str) -> Dict[str, Any]:
        """Validate answer section structure."""
        issues = []
        
        # Check for key components
        required_components = ['原理', '技术', '解决']
        found_components = []
        
        for component in required_components:
            if component in answer_content:
                found_components.append(component)
        
        if len(found_components) < 2:
            issues.append(f"Answer missing key components: {len(found_components)}/{len(required_components)}")
        
        # Check for conclusion phrase
        conclusion_patterns = ['经典', '方法', '解决.*矛盾']
        has_conclusion = any(re.search(pattern, answer_content) for pattern in conclusion_patterns)
        
        if not has_conclusion:
            issues.append("Answer missing conclusion phrase")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'found_components': found_components,
            'has_conclusion': has_conclusion
        }
    
    def _check_lengths(self, cot_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check section lengths."""
        length_errors = []
        section_lengths = {}
        
        total_length = 0
        
        for section in self.required_sections:
            if section in cot_data:
                content = cot_data[section]
                length = len(content)
                section_lengths[section] = length
                total_length += length
                
                # Check minimum length
                min_length = self.min_lengths.get(section, 0)
                if length < min_length:
                    length_errors.append(f"{section} too short: {length} < {min_length}")
        
        # Check total length
        if total_length > self.max_total_length:
            length_errors.append(f"Total length too long: {total_length} > {self.max_total_length}")
        
        return {
            'all_valid': len(length_errors) == 0,
            'length_errors': length_errors,
            'section_lengths': section_lengths,
            'total_length': total_length
        }
    
    def _check_metadata(self, cot_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check metadata completeness."""
        issues = []
        
        # Check for required metadata fields
        required_metadata = ['data_id', 'source_application']
        for field in required_metadata:
            if field not in cot_data or not cot_data[field]:
                issues.append(f"Missing metadata field: {field}")
        
        # Check metadata structure
        if 'metadata' in cot_data:
            metadata = cot_data['metadata']
            recommended_fields = ['generated_at', 'subgraph_nodes', 'rag_references_count']
            
            for field in recommended_fields:
                if field not in metadata:
                    issues.append(f"Missing recommended metadata: {field}")
        else:
            issues.append("Missing metadata section")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues
        }
    
    def validate_batch(self, cot_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate a batch of CoT data.
        
        Args:
            cot_batch: List of CoT data items
            
        Returns:
            Batch validation summary
        """
        batch_result = {
            'total_items': len(cot_batch),
            'valid_items': 0,
            'invalid_items': 0,
            'validation_details': [],
            'common_issues': {},
            'overall_valid': True
        }
        
        issue_counts = {}
        
        for i, cot_item in enumerate(cot_batch):
            item_result = self.validate(cot_item)
            batch_result['validation_details'].append({
                'item_index': i,
                'data_id': cot_item.get('data_id', f'item_{i}'),
                'is_valid': item_result['is_valid'],
                'error_count': len(item_result['errors']),
                'warning_count': len(item_result['warnings'])
            })
            
            if item_result['is_valid']:
                batch_result['valid_items'] += 1
            else:
                batch_result['invalid_items'] += 1
                batch_result['overall_valid'] = False
                
                # Count common issues
                for error in item_result['errors']:
                    issue_counts[error] = issue_counts.get(error, 0) + 1
        
        # Identify most common issues
        if issue_counts:
            sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
            batch_result['common_issues'] = dict(sorted_issues[:5])  # Top 5 issues
        
        return batch_result
    
    def get_validation_summary(self, validation_result: Dict[str, Any]) -> str:
        """Generate human-readable validation summary."""
        if validation_result['is_valid']:
            return "✅ CoT data format is valid"
        
        summary_lines = ["❌ CoT data format validation failed:"]
        
        for error in validation_result['errors']:
            summary_lines.append(f"  • {error}")
        
        if validation_result['warnings']:
            summary_lines.append("\nWarnings:")
            for warning in validation_result['warnings']:
                summary_lines.append(f"  • {warning}")
        
        return "\n".join(summary_lines)
