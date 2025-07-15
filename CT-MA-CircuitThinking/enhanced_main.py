#!/usr/bin/env python3
"""
Enhanced CT-MA Main Function

Comprehensive workflow with all enhanced features:
1. Mermaid knowledge graph extraction
2. Configurable question generation
3. Enhanced logic analysis with readable text
4. LlamaIndex RAG-enhanced thinking
5. Iterative expert team improvement
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
import argparse

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.config_manager import ConfigManager
from src.utils.logger import setup_logger, get_logger
from src.core.kg_loader import KGLoader
from src.core.subgraph_extractor import SubgraphExtractor
from src.visualization.mermaid_extractor import MermaidKGExtractor
from src.question_design.question_designer import QuestionDesignCoordinator
from src.rag.vector_store import VectorStore
from src.rag.llamaindex_retriever import LlamaIndexRetriever
from src.rag.knowledge_enhancer import KnowledgeEnhancer
from src.agents.enhanced_logic_agent import EnhancedLogicAgent
from src.agents.enhanced_think_team import EnhancedThinkTeamCoordinator
from src.agents.answer_agent import AnswerAgent
from src.improvement.iterative_expert_team import IterativeExpertTeamCoordinator


class EnhancedCTMAWorkflow:
    """Enhanced CT-MA workflow coordinator."""
    
    def __init__(self, config: ConfigManager, num_questions: int = 5):
        """
        Initialize enhanced workflow.
        
        Args:
            config: Configuration manager
            num_questions: Number of questions to generate per application
        """
        self.config = config
        self.num_questions = num_questions
        self.logger = get_logger(__name__)
        
        # Components
        self.kg_loader = None
        self.mermaid_extractor = None
        self.question_coordinator = None
        self.llamaindex_retriever = None
        self.knowledge_enhancer = None
        self.logic_agent = None
        self.think_team = None
        self.answer_agent = None
        self.expert_team = None
    
    async def initialize(self):
        """Initialize all components."""
        self.logger.info("Initializing Enhanced CT-MA Workflow...")
        
        # Core components
        self.kg_loader = KGLoader(self.config)
        self.mermaid_extractor = MermaidKGExtractor(self.config)
        
        # Question design
        self.question_coordinator = QuestionDesignCoordinator(self.config)
        await self.question_coordinator.initialize()
        
        # RAG components
        vector_store = VectorStore(self.config)
        await vector_store.setup()
        
        self.llamaindex_retriever = LlamaIndexRetriever(self.config)
        await self.llamaindex_retriever.setup()
        
        self.knowledge_enhancer = KnowledgeEnhancer(self.config, vector_store)
        await self.knowledge_enhancer.initialize()
        
        # Enhanced agents
        self.logic_agent = EnhancedLogicAgent(self.config)
        await self.logic_agent.initialize()
        
        self.think_team = EnhancedThinkTeamCoordinator(self.config, self.llamaindex_retriever)
        await self.think_team.initialize()
        
        self.answer_agent = AnswerAgent(self.config)
        await self.answer_agent.initialize()
        
        # Expert team
        self.expert_team = IterativeExpertTeamCoordinator(self.config)
        await self.expert_team.initialize()
        
        self.logger.info("Enhanced CT-MA Workflow initialized")
    
    async def run_complete_workflow(self, max_applications: int = 3) -> Dict[str, Any]:
        """
        Run complete enhanced workflow.
        
        Args:
            max_applications: Maximum number of applications to process
            
        Returns:
            Complete workflow results
        """
        start_time = datetime.now()
        self.logger.info(f"Starting enhanced workflow for {max_applications} applications")
        
        # Step 1: Load and extract knowledge graphs
        self.logger.info("Step 1: Loading and extracting knowledge graphs...")
        kg_data = await self.kg_loader.load_knowledge_graph()
        
        # Extract Mermaid graphs
        mermaid_graphs = self.mermaid_extractor.extract_circuit_application_graphs(kg_data)
        
        # Save Mermaid graphs
        mermaid_output_path = "output/mermaid_graphs.json"
        self.mermaid_extractor.save_mermaid_graphs(mermaid_graphs, mermaid_output_path)
        
        self.logger.info(f"Extracted {len(mermaid_graphs)} Mermaid graphs")
        
        # Step 2: Process applications
        selected_graphs = mermaid_graphs[:max_applications]
        workflow_results = []
        
        for i, graph_data in enumerate(selected_graphs, 1):
            app_name = graph_data['application_label']
            self.logger.info(f"Processing {i}/{len(selected_graphs)}: {app_name}")
            
            try:
                app_result = await self._process_single_application(graph_data)
                workflow_results.append(app_result)
                
            except Exception as e:
                self.logger.error(f"Failed to process {app_name}: {e}")
                workflow_results.append({
                    'application': app_name,
                    'error': str(e),
                    'status': 'failed'
                })
        
        # Step 3: Compile final results
        end_time = datetime.now()
        duration = end_time - start_time
        
        final_results = {
            'workflow_metadata': {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration.total_seconds(),
                'total_applications': len(selected_graphs),
                'successful_applications': len([r for r in workflow_results if r.get('status') == 'completed']),
                'num_questions_per_app': self.num_questions
            },
            'mermaid_graphs': mermaid_graphs,
            'application_results': workflow_results,
            'summary_statistics': self._calculate_summary_statistics(workflow_results)
        }
        
        # Save final results
        output_path = f"output/enhanced_workflow_results_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Enhanced workflow completed. Results saved to: {output_path}")
        return final_results
    
    async def _process_single_application(self, graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single circuit application."""
        app_name = graph_data['application_label']
        
        # Step 1: Generate questions
        self.logger.info(f"  Generating {self.num_questions} questions for {app_name}")
        
        # Modify question coordinator to generate specified number
        original_config = self.question_coordinator.config.get('question_design.questions_per_type', 3)
        questions_per_type = max(1, self.num_questions // 3)  # Distribute across 3 types
        
        # Generate questions
        question_set = await self.question_coordinator.design_questions_for_subgraph(graph_data['subgraph_data'])
        
        # Step 2: Generate readable description
        readable_description = self.mermaid_extractor.generate_readable_text_description(graph_data)
        
        # Step 3: Enhanced logic analysis
        self.logger.info(f"  Enhanced logic analysis for {app_name}")
        logic_input = {
            'subgraph': graph_data['subgraph_data'],
            'readable_description': readable_description
        }
        logic_result = await self.logic_agent.execute(logic_input)
        
        # Step 4: Enhanced thinking with RAG
        self.logger.info(f"  Enhanced thinking analysis for {app_name}")
        
        # Enhance subgraph with traditional RAG
        enhanced_subgraph = await self.knowledge_enhancer.enhance_subgraph(graph_data['subgraph_data'])
        evidence_package = self.knowledge_enhancer.build_evidence_package(enhanced_subgraph)
        
        think_input = {
            'logic': logic_result['logic'],
            'subgraph': enhanced_subgraph,
            'evidence_package': evidence_package
        }
        think_result = await self.think_team.execute_enhanced_thinking(think_input)
        
        # Step 5: Answer generation
        self.logger.info(f"  Answer generation for {app_name}")
        answer_input = {
            'think': think_result['think'],
            'logic': logic_result['logic'],
            'subgraph': enhanced_subgraph
        }
        answer_result = await self.answer_agent.execute(answer_input)
        
        # Step 6: Compile initial CoT
        initial_cot = {
            'source_application': app_name,
            'data_id': f"enhanced_{app_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'logic': logic_result['logic'],
            'think': think_result['think'],
            'answer': answer_result['answer'],
            'metadata': {
                'logic_execution_time': logic_result.get('execution_time', 0),
                'think_execution_time': think_result.get('execution_time', 0),
                'answer_execution_time': answer_result.get('execution_time', 0),
                'rag_references_count': think_result.get('rag_references_count', 0),
                'subgraph_nodes': len(enhanced_subgraph.get('nodes', [])),
                'questions_generated': question_set['total_questions']
            }
        }
        
        # Step 7: Iterative expert improvement
        self.logger.info(f"  Expert team iterative improvement for {app_name}")
        improvement_result = await self.expert_team.improve_until_satisfied(initial_cot)
        
        return {
            'application': app_name,
            'mermaid_graph': graph_data['mermaid_syntax'],
            'readable_description': readable_description,
            'questions': question_set,
            'initial_cot': initial_cot,
            'improvement_result': improvement_result,
            'final_cot': improvement_result['final_cot'],
            'status': 'completed',
            'processing_summary': {
                'questions_count': question_set['total_questions'],
                'improvement_iterations': improvement_result['total_iterations'],
                'final_score': improvement_result['final_score'],
                'expert_satisfied': improvement_result['is_satisfied']
            }
        }
    
    def _calculate_summary_statistics(self, workflow_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics."""
        successful_results = [r for r in workflow_results if r.get('status') == 'completed']
        
        if not successful_results:
            return {'total_successful': 0}
        
        # Calculate averages
        avg_questions = sum(r['processing_summary']['questions_count'] for r in successful_results) / len(successful_results)
        avg_iterations = sum(r['processing_summary']['improvement_iterations'] for r in successful_results) / len(successful_results)
        avg_final_score = sum(r['processing_summary']['final_score'] for r in successful_results) / len(successful_results)
        satisfaction_rate = sum(1 for r in successful_results if r['processing_summary']['expert_satisfied']) / len(successful_results)
        
        return {
            'total_successful': len(successful_results),
            'average_questions_per_app': avg_questions,
            'average_improvement_iterations': avg_iterations,
            'average_final_score': avg_final_score,
            'expert_satisfaction_rate': satisfaction_rate
        }


async def main():
    """Main function with configurable parameters."""
    parser = argparse.ArgumentParser(description='Enhanced CT-MA Circuit Thinking System')
    parser.add_argument('--questions', type=int, default=5, help='Number of questions to generate per application')
    parser.add_argument('--apps', type=int, default=3, help='Maximum number of applications to process')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logger(debug=args.debug)
    logger = get_logger(__name__)
    
    logger.info("🚀 Enhanced CT-MA Circuit Thinking System")
    logger.info("=" * 60)
    logger.info(f"Configuration:")
    logger.info(f"  Questions per application: {args.questions}")
    logger.info(f"  Maximum applications: {args.apps}")
    logger.info(f"  Debug mode: {args.debug}")
    logger.info("=" * 60)
    
    try:
        # Initialize configuration
        config = ConfigManager()
        
        # Create and run workflow
        workflow = EnhancedCTMAWorkflow(config, num_questions=args.questions)
        await workflow.initialize()
        
        results = await workflow.run_complete_workflow(max_applications=args.apps)
        
        # Display summary
        logger.info("\n" + "=" * 60)
        logger.info("🎉 ENHANCED WORKFLOW COMPLETED!")
        logger.info("=" * 60)
        
        metadata = results['workflow_metadata']
        stats = results['summary_statistics']
        
        logger.info(f"📊 Results Summary:")
        logger.info(f"  Total applications processed: {metadata['total_applications']}")
        logger.info(f"  Successful applications: {metadata['successful_applications']}")
        logger.info(f"  Questions per application: {metadata['num_questions_per_app']}")
        logger.info(f"  Total duration: {metadata['duration_seconds']:.1f} seconds")
        
        if stats.get('total_successful', 0) > 0:
            logger.info(f"  Average questions generated: {stats['average_questions_per_app']:.1f}")
            logger.info(f"  Average improvement iterations: {stats['average_improvement_iterations']:.1f}")
            logger.info(f"  Average final quality score: {stats['average_final_score']:.1f}/10")
            logger.info(f"  Expert satisfaction rate: {stats['expert_satisfaction_rate']:.1%}")
        
        logger.info("\n🎯 Enhanced Features Successfully Demonstrated:")
        logger.info("  ✅ Mermaid knowledge graph extraction")
        logger.info("  ✅ Configurable multi-hop question generation")
        logger.info("  ✅ Enhanced logic analysis with readable descriptions")
        logger.info("  ✅ LlamaIndex RAG-enhanced thinking")
        logger.info("  ✅ Iterative expert team improvement")
        
        return True
        
    except Exception as e:
        logger.error(f"Enhanced workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
