"""
Main entry point for the Natural Language Data Retrieval System.

Provides:
- CLI for initialization and testing
- Interactive query interface
- API server startup
- Benchmark runner
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime

from src.agents.pipeline import AgentPipeline
from src.engine.ontology import BusinessOntology
from src.db.manager import initialize_databases, DatabaseManager, DatabaseConfig


def init_databases():
    """Initialize all 3 databases with synthetic data."""
    import os
    print("=" * 70)
    print("INITIALIZING DATABASES")
    print("=" * 70)

    dialect = os.getenv("DB_DIALECT", "sqlite")
    use_pg  = dialect == "postgresql"
    print(f"  Engine: {dialect.upper()}")

    try:
        sales_db, inv_db, ana_db, hr_db, fin_db = initialize_databases(use_postgresql=use_pg)
        print("✓ Sales database initialized")
        print("✓ Inventory database initialized")
        print("✓ Analytics database initialized")
        print("✓ HR database initialized")
        print("✓ Finance database initialized")
        print("\nDatabase Initialization Summary:")
        print(f"  - 5 complete databases ready")
        print(f"  - ~1,970,500 records in Sales DB")
        print(f"  - ~170,000 records in Inventory DB")
        print(f"  - ~14,825 records in Analytics DB")
        print(f"  - ~170,000 records in HR DB")
        print(f"  - ~108,000 records in Finance DB")
        print(f"  - ~2,433,325 total records across all databases")
        return True
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False


def run_interactive_demo():
    """Run interactive query demo."""
    import os
    print("=" * 70)
    print("INTERACTIVE QUERY DEMO")
    print("=" * 70)
    print("\nInitializing system...")

    ontology = BusinessOntology()
    db = DatabaseManager(DatabaseConfig(
        engine_type=os.getenv("DB_DIALECT", "sqlite"),
        database=os.getenv("DB_NAME", "sales"),
    ))
    pipeline = AgentPipeline(ontology, db_manager=db)

    print("✓ System ready\n")
    print("Example queries:")
    print("  - 'What was our total revenue last month?'")
    print("  - 'How many customers do we have?'")
    print("  - 'Show me orders from the North America region'")
    print("  - 'What is our average order value?'")
    print("\nType 'exit' to quit.\n")
    
    while True:
        try:
            query = input("Query> ").strip()
            
            if query.lower() in ("exit", "quit", "q"):
                print("Exiting...")
                break
            
            if not query:
                continue
            
            print("\nProcessing query...")
            result = pipeline.process_query(query)
            
            print(f"\nQuery ID: {result.query_id}")
            print(f"Status: {'✓ Success' if result.converged else '✗ Incomplete'}")
            print(f"Drift Score: {result.final_drift:.3f}")
            print(f"Converged: {result.converged}")
            print(f"Iterations: {result.metadata.total_iterations}")
            
            if result.results:
                print(f"Results: {result.results.row_count} rows")
                if result.results.rows:
                    print("Sample:")
                    for row in result.results.rows[:3]:
                        print(f"  {row.data}")
            
            if result.drift_scores:
                print(f"Final Drift Status: {result.drift_scores[-1].notes}")
            
            print()
        
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}\n")


def run_api_server():
    """Start FastAPI development server."""
    import uvicorn
    from src.api.backend import create_app
    
    print("=" * 70)
    print("STARTING API SERVER")
    print("=" * 70)
    
    app = create_app()
    
    print("\n✓ FastAPI application created")
    print("Starting server on http://0.0.0.0:8000\n")
    print("API Documentation:")
    print("  - Swagger UI: http://localhost:8000/docs")
    print("  - ReDoc: http://localhost:8000/redoc")
    print("  - OpenAPI JSON: http://localhost:8000/openapi.json")
    print("\nPress Ctrl+C to stop server\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)


def run_benchmark():
    """Run performance benchmarks."""
    import os
    import time
    print("=" * 70)
    print("RUNNING BENCHMARKS")
    print("=" * 70)

    ontology = BusinessOntology()
    db = DatabaseManager(DatabaseConfig(
        engine_type=os.getenv("DB_DIALECT", "sqlite"),
        database=os.getenv("DB_NAME", "sales"),
    ))
    pipeline = AgentPipeline(ontology, db_manager=db)

    queries = [
        "What was our total revenue?",
        "Show me total revenue by region",
        "Monthly revenue trend for last year",
        "Top 10 customers by revenue",
        "Revenue by product category",
        "What is our gross margin?",
        "Year over year revenue comparison",
        "Customer churn rate by tier",
        "Average order value for delivered orders",
        "Revenue by region and tier",
    ]
    
    print(f"\nRunning {len(queries)} benchmark queries...\n")
    
    latencies = []
    drifts = []
    
    for i, query in enumerate(queries):
        print(f"[{i+1}/{len(queries)}] {query[:50]}...", end=" ", flush=True)
        
        start = time.time()
        result = pipeline.process_query(query)
        elapsed = (time.time() - start) * 1000  # ms
        
        latencies.append(elapsed)
        if result.final_drift:
            drifts.append(result.final_drift)
        
        status = "✓" if result.converged else "✗"
        print(f"{status} {elapsed:.1f}ms (drift={result.final_drift:.3f})")
    
    print("\n" + "=" * 70)
    print("BENCHMARK RESULTS")
    print("=" * 70)
    
    if latencies:
        latencies.sort()
        print(f"\nLatency Metrics (ms):")
        print(f"  Min:  {latencies[0]:.1f}")
        print(f"  P50:  {latencies[len(latencies)//2]:.1f}")
        print(f"  P95:  {latencies[int(len(latencies)*0.95)]:.1f}")
        print(f"  Max:  {latencies[-1]:.1f}")
    
    if drifts:
        drifts.sort()
        converged = sum(1 for d in drifts if d < 0.15)
        print(f"\nDrift Metrics:")
        print(f"  Min:        {drifts[0]:.3f}")
        print(f"  Median:     {drifts[len(drifts)//2]:.3f}")
        print(f"  Max:        {drifts[-1]:.3f}")
        print(f"  Converged:  {converged}/{len(drifts)} ({100*converged/len(drifts):.1f}%)")
    
    print("\n✓ Benchmark complete")


def run_tests():
    """Run test suite."""
    import pytest
    
    print("=" * 70)
    print("RUNNING TESTS")
    print("=" * 70 + "\n")
    
    test_dir = Path(__file__).parent / "tests"
    exit_code = pytest.main([str(test_dir), "-v", "--tb=short"])
    
    return exit_code == 0


def show_system_info():
    """Display system information."""
    print("=" * 70)
    print("SYSTEM INFORMATION")
    print("=" * 70)
    
    from src.engine.ontology import BusinessOntology
    
    ontology = BusinessOntology()
    
    print(f"\nOntology:")
    print(f"  - Entities: {len(ontology.entities)}")
    print(f"    {', '.join(ontology.entities.keys())}")
    print(f"  - Metrics: {len(ontology.metrics)}")
    print(f"    {', '.join(ontology.metrics.keys())}")
    print(f"  - Constraints: {len(ontology.constraints)}")
    print(f"    {', '.join(ontology.constraints.keys())}")
    print(f"  - Join Rules: {len(ontology.joins)}")
    
    print(f"\nAgents:")
    print(f"  1. IntentParserAgent: Extract entities/metrics from NL")
    print(f"  2. OntologyMapperAgent: Ground to business ontology")
    print(f"  3. ConstraintValidatorAgent: Enforce business rules")
    print(f"  4. ExecutionPlannerAgent: Generate query plans")
    print(f"  5. ResultVerifierAgent: Validate results")
    
    print(f"\nDrift Metric:")
    print(f"  - Intent Alignment (40%)")
    print(f"  - Constraint Adherence (30%)")
    print(f"  - Result Plausibility (30%)")
    print(f"  - Convergence Threshold: 0.15")
    
    print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Natural Language Data Retrieval System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py init          # Initialize databases
  python main.py demo          # Run interactive demo
  python main.py api           # Start FastAPI server
  python main.py bench         # Run benchmarks
  python main.py test          # Run tests
  python main.py info          # Show system info
        """
    )
    
    parser.add_argument(
        "command",
        choices=["init", "demo", "api", "bench", "test", "info"],
        help="Command to execute"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    try:
        if args.command == "init":
            success = init_databases()
            sys.exit(0 if success else 1)
        
        elif args.command == "demo":
            run_interactive_demo()
        
        elif args.command == "api":
            run_api_server()
        
        elif args.command == "bench":
            run_benchmark()
        
        elif args.command == "test":
            success = run_tests()
            sys.exit(0 if success else 1)
        
        elif args.command == "info":
            show_system_info()
        
        else:
            parser.print_help()
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
