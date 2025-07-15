"""
Test cases for Format Validator module.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.cot.format_validator import FormatValidator
from src.utils.config_manager import ConfigManager


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config_data = {
        "quality": {
            "required_sections": ["logic", "think", "answer"],
            "min_logic_length": 100,
            "min_think_length": 500,
            "min_answer_length": 100,
            "max_total_length": 5000
        }
    }
    
    class MockConfig:
        def __init__(self, data):
            self.data = data
        
        def get(self, key, default=None):
            keys = key.split('.')
            value = self.data
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value
    
    return MockConfig(config_data)


@pytest.fixture
def valid_cot_data():
    """Valid CoT data for testing."""
    return {
        "data_id": "test_001",
        "source_application": "测试应用",
        "logic": """【目标应用】: 测试应用
【关键瓶颈】: 测试瓶颈问题
【支撑路径】: 
1. [基础概念] 基础概念1
2. [核心技术] 核心技术1
3. [应用] 测试应用
【因果链简述】: 这是一个测试的因果链描述，说明了各技术点之间的逻辑关系。""",
        "think": """推理开始。目标是实现测试应用。

第一步，分析基础概念。根据`<logic>`，我们需要理解基础概念1。RAG证据[定义A]证实，这个概念是基础的。

第二步，分析核心技术。核心技术1是关键。RAG证据[技术B]解释，这个技术能够解决问题。

第三步，分析应用实现。`<logic>`指向测试应用。为什么？RAG证据[应用C]显示，这个应用能够满足需求。

第四步，整合分析。通过以上分析，我们可以解决测试瓶颈问题。RAG证据[设计D]强调了设计要点。

推理结束。我通过层层递进，从基础概念出发，认识到核心技术的重要性，选择了合适的技术，并最终实现了测试应用，解决了设计核心矛盾。""",
        "answer": """为了实现测试应用，核心策略是采用核心技术1。原理在于：该技术能够有效解决测试瓶颈问题。核心技术1能提供稳定的性能，从而解决了关键问题。同时，基础概念1能确保理论基础，从而实现最终的应用目标。这是解决测试矛盾的经典方法。""",
        "metadata": {
            "generated_at": "2024-01-01T00:00:00",
            "subgraph_nodes": 5,
            "rag_references_count": 4
        }
    }


@pytest.fixture
def invalid_cot_data():
    """Invalid CoT data for testing."""
    return {
        "data_id": "test_002",
        "logic": "短的逻辑内容",  # Too short
        "think": "短的思考内容",  # Too short, missing structure
        "answer": "短答案"  # Too short
    }


class TestFormatValidator:
    """Test cases for FormatValidator class."""
    
    def test_init(self, mock_config):
        """Test FormatValidator initialization."""
        validator = FormatValidator(mock_config)
        assert validator.config == mock_config
        assert validator.required_sections == ["logic", "think", "answer"]
        assert validator.min_lengths['logic'] == 100
        assert validator.min_lengths['think'] == 500
        assert validator.min_lengths['answer'] == 100
    
    def test_validate_valid_cot_data(self, mock_config, valid_cot_data):
        """Test validation of valid CoT data."""
        validator = FormatValidator(mock_config)
        result = validator.validate(valid_cot_data)
        
        assert result['is_valid'] == True
        assert len(result['errors']) == 0
        assert result['section_checks']['all_present'] == True
        assert result['length_checks']['all_valid'] == True
    
    def test_validate_invalid_cot_data(self, mock_config, invalid_cot_data):
        """Test validation of invalid CoT data."""
        validator = FormatValidator(mock_config)
        result = validator.validate(invalid_cot_data)
        
        assert result['is_valid'] == False
        assert len(result['errors']) > 0
        assert result['section_checks']['all_present'] == False  # Missing source_application
        assert result['length_checks']['all_valid'] == False  # Too short
    
    def test_validate_logic_structure(self, mock_config):
        """Test logic structure validation."""
        validator = FormatValidator(mock_config)
        
        # Valid logic structure
        valid_logic = """【目标应用】: 测试应用
【关键瓶颈】: 测试问题
【支撑路径】: 
1. [基础概念] 概念1
【因果链简述】: 因果关系"""
        
        result = validator._validate_logic_structure(valid_logic)
        assert result['is_valid'] == True
        assert len(result['found_elements']) == 4
        
        # Invalid logic structure
        invalid_logic = "缺少必要元素的逻辑内容"
        result = validator._validate_logic_structure(invalid_logic)
        assert result['is_valid'] == False
        assert len(result['issues']) > 0
    
    def test_validate_think_structure(self, mock_config):
        """Test think structure validation."""
        validator = FormatValidator(mock_config)
        
        # Valid think structure
        valid_think = """推理开始。
第一步，分析问题。RAG证据[A]证实。
第二步，分析技术。RAG证据[B]解释。
第三步，分析方案。RAG证据[C]显示。
推理结束。通过层层递进。"""
        
        result = validator._validate_think_structure(valid_think)
        assert result['is_valid'] == True
        assert result['reasoning_steps'] >= 3
        assert result['rag_references'] >= 3
        assert result['has_conclusion'] == True
        
        # Invalid think structure
        invalid_think = "简单的思考内容，没有结构"
        result = validator._validate_think_structure(invalid_think)
        assert result['is_valid'] == False
        assert len(result['issues']) > 0
    
    def test_validate_answer_structure(self, mock_config):
        """Test answer structure validation."""
        validator = FormatValidator(mock_config)
        
        # Valid answer structure
        valid_answer = "核心解决方案基于技术原理。该技术能够解决关键问题。这是经典的设计方法。"
        
        result = validator._validate_answer_structure(valid_answer)
        assert result['is_valid'] == True
        assert len(result['found_components']) >= 2
        
        # Invalid answer structure
        invalid_answer = "简单答案"
        result = validator._validate_answer_structure(invalid_answer)
        assert result['is_valid'] == False
        assert len(result['issues']) > 0
    
    def test_check_lengths(self, mock_config, valid_cot_data):
        """Test length checking."""
        validator = FormatValidator(mock_config)
        
        # Valid lengths
        result = validator._check_lengths(valid_cot_data)
        assert result['all_valid'] == True
        assert len(result['length_errors']) == 0
        
        # Invalid lengths
        short_data = {
            "logic": "短",
            "think": "短",
            "answer": "短"
        }
        result = validator._check_lengths(short_data)
        assert result['all_valid'] == False
        assert len(result['length_errors']) > 0
    
    def test_validate_batch(self, mock_config, valid_cot_data, invalid_cot_data):
        """Test batch validation."""
        validator = FormatValidator(mock_config)
        
        batch_data = [valid_cot_data, invalid_cot_data]
        result = validator.validate_batch(batch_data)
        
        assert result['total_items'] == 2
        assert result['valid_items'] == 1
        assert result['invalid_items'] == 1
        assert result['overall_valid'] == False
        assert len(result['validation_details']) == 2
    
    def test_get_validation_summary(self, mock_config, valid_cot_data, invalid_cot_data):
        """Test validation summary generation."""
        validator = FormatValidator(mock_config)
        
        # Valid data summary
        valid_result = validator.validate(valid_cot_data)
        summary = validator.get_validation_summary(valid_result)
        assert "✅" in summary
        assert "valid" in summary
        
        # Invalid data summary
        invalid_result = validator.validate(invalid_cot_data)
        summary = validator.get_validation_summary(invalid_result)
        assert "❌" in summary
        assert "failed" in summary


if __name__ == "__main__":
    pytest.main([__file__])
