from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import inspect
from typing import List, Dict, Any
from .database import get_db, engine, Base
from .schemas import QueryPlan, MutationPlan
from .query_builder import execute_query_plan, execute_mutation_plan
from .models import User, Product, Submission, Claim
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Dynamic SQL API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    from sqlalchemy import text
    from datetime import datetime, timedelta
    
    # Create tables for demo
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSession(engine) as session:
        # Check if users exist
        result = await session.execute(text("SELECT count(*) FROM users"))
        count = result.scalar()
        if count == 0:
            users = [
                User(id=1, name="Alice", age=30, role="admin", salary=100000, joined_at=datetime(2023, 1, 1), department="Engineering"),
                User(id=2, name="Bob", age=25, role="user", salary=50000, joined_at=datetime(2023, 6, 1), department="Sales"),
                User(id=3, name="Charlie", age=35, role="user", salary=60000, joined_at=datetime(2023, 3, 15), department="Engineering"),
                User(id=4, name="David", age=40, role="manager", salary=90000, joined_at=datetime(2022, 11, 20), department="HR"),
                User(id=5, name="Eve", age=22, role="intern", salary=30000, joined_at=datetime(2023, 8, 1), department="Sales"),
            ]
            session.add_all(users)
            
            products = [
                Product(id=1, name="Laptop", category="Electronics", price=1200.0, stock=50),
                Product(id=2, name="Phone", category="Electronics", price=800.0, stock=100),
                Product(id=3, name="Desk", category="Furniture", price=300.0, stock=20),
            ]
            session.add_all(products)
            
            # Add Submissions
            base_date = datetime(2023, 1, 1)
            submissions = [
                Submission(id=1, submission_number="SUB-2023-001", customer_name="Acme Corp", submission_date=base_date, status="approved", total_amount=5500.0),
                Submission(id=2, submission_number="SUB-2023-002", customer_name="TechStart Inc", submission_date=base_date + timedelta(days=15), status="pending", total_amount=3200.0),
                Submission(id=3, submission_number="SUB-2023-003", customer_name="Global Industries", submission_date=base_date + timedelta(days=30), status="approved", total_amount=8750.0),
                Submission(id=4, submission_number="SUB-2023-004", customer_name="Sunrise LLC", submission_date=base_date + timedelta(days=45), status="rejected", total_amount=1200.0),
                Submission(id=5, submission_number="SUB-2023-005", customer_name="Blue Sky Co", submission_date=base_date + timedelta(days=60), status="approved", total_amount=6400.0),
                Submission(id=6, submission_number="SUB-2023-006", customer_name="Metro Services", submission_date=base_date + timedelta(days=75), status="pending", total_amount=2800.0),
                Submission(id=7, submission_number="SUB-2023-007", customer_name="Peak Performance", submission_date=base_date + timedelta(days=90), status="approved", total_amount=9200.0),
                Submission(id=8, submission_number="SUB-2023-008", customer_name="Valley Tech", submission_date=base_date + timedelta(days=105), status="approved", total_amount=4100.0),
                Submission(id=9, submission_number="SUB-2023-009", customer_name="Coastal Systems", submission_date=base_date + timedelta(days=120), status="pending", total_amount=7300.0),
                Submission(id=10, submission_number="SUB-2023-010", customer_name="Mountain View Inc", submission_date=base_date + timedelta(days=135), status="approved", total_amount=5900.0),
            ]
            session.add_all(submissions)
            
            # Add Claims (3 claims per submission on average)
            claims = [
                # SUB-2023-001 claims
                Claim(id=1, claim_number="CLM-001-A", submission_id=1, claim_date=base_date + timedelta(days=1), claim_type="medical", amount=2500.0, status="approved", description="Hospital visit"),
                Claim(id=2, claim_number="CLM-001-B", submission_id=1, claim_date=base_date + timedelta(days=2), claim_type="dental", amount=1500.0, status="approved", description="Dental work"),
                Claim(id=3, claim_number="CLM-001-C", submission_id=1, claim_date=base_date + timedelta(days=3), claim_type="vision", amount=1500.0, status="approved", description="Eye exam and glasses"),
                
                # SUB-2023-002 claims
                Claim(id=4, claim_number="CLM-002-A", submission_id=2, claim_date=base_date + timedelta(days=16), claim_type="medical", amount=1800.0, status="pending", description="Lab tests"),
                Claim(id=5, claim_number="CLM-002-B", submission_id=2, claim_date=base_date + timedelta(days=17), claim_type="medical", amount=1400.0, status="pending", description="Prescription meds"),
                
                # SUB-2023-003 claims
                Claim(id=6, claim_number="CLM-003-A", submission_id=3, claim_date=base_date + timedelta(days=31), claim_type="medical", amount=4500.0, status="approved", description="Surgery"),
                Claim(id=7, claim_number="CLM-003-B", submission_id=3, claim_date=base_date + timedelta(days=32), claim_type="medical", amount=2250.0, status="approved", description="Physical therapy"),
                Claim(id=8, claim_number="CLM-003-C", submission_id=3, claim_date=base_date + timedelta(days=33), claim_type="dental", amount=2000.0, status="approved", description="Root canal"),
                
                # SUB-2023-004 claims
                Claim(id=9, claim_number="CLM-004-A", submission_id=4, claim_date=base_date + timedelta(days=46), claim_type="vision", amount=1200.0, status="denied", description="Cosmetic lenses"),
                
                # SUB-2023-005 claims
                Claim(id=10, claim_number="CLM-005-A", submission_id=5, claim_date=base_date + timedelta(days=61), claim_type="medical", amount=3200.0, status="approved", description="Emergency room"),
                Claim(id=11, claim_number="CLM-005-B", submission_id=5, claim_date=base_date + timedelta(days=62), claim_type="medical", amount=1800.0, status="approved", description="Follow-up care"),
                Claim(id=12, claim_number="CLM-005-C", submission_id=5, claim_date=base_date + timedelta(days=63), claim_type="dental", amount=1400.0, status="approved", description="Cleaning and filling"),
                
                # SUB-2023-006 claims
                Claim(id=13, claim_number="CLM-006-A", submission_id=6, claim_date=base_date + timedelta(days=76), claim_type="medical", amount=1600.0, status="pending", description="Specialist consultation"),
                Claim(id=14, claim_number="CLM-006-B", submission_id=6, claim_date=base_date + timedelta(days=77), claim_type="vision", amount=1200.0, status="pending", description="Contact lenses"),
                
                # SUB-2023-007 claims
                Claim(id=15, claim_number="CLM-007-A", submission_id=7, claim_date=base_date + timedelta(days=91), claim_type="medical", amount=5000.0, status="approved", description="Imaging scans"),
                Claim(id=16, claim_number="CLM-007-B", submission_id=7, claim_date=base_date + timedelta(days=92), claim_type="medical", amount=2800.0, status="approved", description="Treatment"),
                Claim(id=17, claim_number="CLM-007-C", submission_id=7, claim_date=base_date + timedelta(days=93), claim_type="dental", amount=1400.0, status="approved", description="Orthodontics"),
                
                # SUB-2023-008 claims
                Claim(id=18, claim_number="CLM-008-A", submission_id=8, claim_date=base_date + timedelta(days=106), claim_type="medical", amount=2200.0, status="approved", description="Checkup"),
                Claim(id=19, claim_number="CLM-008-B", submission_id=8, claim_date=base_date + timedelta(days=107), claim_type="vision", amount=900.0, status="approved", description="Eye exam"),
                Claim(id=20, claim_number="CLM-008-C", submission_id=8, claim_date=base_date + timedelta(days=108), claim_type="dental", amount=1000.0, status="approved", description="Dental checkup"),
                
                # SUB-2023-009 claims
                Claim(id=21, claim_number="CLM-009-A", submission_id=9, claim_date=base_date + timedelta(days=121), claim_type="medical", amount=4100.0, status="pending", description="Hospital admission"),
                Claim(id=22, claim_number="CLM-009-B", submission_id=9, claim_date=base_date + timedelta(days=122), claim_type="medical", amount=3200.0, status="pending", description="Medical procedures"),
                
                # SUB-2023-010 claims
                Claim(id=23, claim_number="CLM-010-A", submission_id=10, claim_date=base_date + timedelta(days=136), claim_type="medical", amount=2900.0, status="approved", description="Consultation"),
                Claim(id=24, claim_number="CLM-010-B", submission_id=10, claim_date=base_date + timedelta(days=137), claim_type="dental", amount=1800.0, status="approved", description="Crown"),
                Claim(id=25, claim_number="CLM-010-C", submission_id=10, claim_date=base_date + timedelta(days=138), claim_type="vision", amount=1200.0, status="approved", description="Prescription glasses"),
            ]
            session.add_all(claims)
            
            await session.commit()

@app.post("/execute", response_model=List[Any])
async def execute_plan(plan: QueryPlan, db: AsyncSession = Depends(get_db)):
    logger.info(f"📥 Received QueryPlan: {plan.model_dump_json(indent=2)}")
    try:
        results = await execute_query_plan(plan, db)
        return results
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mutate")
async def mutate(plan: MutationPlan, db: AsyncSession = Depends(get_db)):
    logger.info(f"📥 Received MutationPlan: {plan.model_dump_json(indent=2)}")
    try:
        result = await execute_mutation_plan(plan, db)
        return result
    except ValueError as e:
        logger.error(f"Validation error in mutation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing mutation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/schema", response_model=Dict[str, List[str]])
async def get_schema():
    # Introspect the database to get tables and columns
    # Note: inspect is synchronous, so we might need to run it in a thread if we want to be purely async,
    # but for schema inspection it's usually fine or we can use run_sync.
    
    def _get_schema_sync(connection):
        inspector = inspect(connection)
        schema = {}
        for table_name in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns(table_name)]
            schema[table_name] = columns
        return schema

    async with engine.connect() as conn:
        schema = await conn.run_sync(_get_schema_sync)
    
    return schema

@app.get("/schema/enhanced")
async def get_enhanced_schema():
    """
    Enhanced schema endpoint that returns:
    - Table names
    - Column names with types
    - Primary keys
    - Foreign keys
    """
    def _get_enhanced_schema_sync(connection):
        inspector = inspect(connection)
        enhanced_schema = {}
        
        for table_name in inspector.get_table_names():
            columns_info = []
            pk_columns = inspector.get_pk_constraint(table_name).get("constrained_columns", [])
            fk_constraints = inspector.get_foreign_keys(table_name)
            
            for col in inspector.get_columns(table_name):
                col_type = str(col["type"]).upper()
                
                # Map SQLAlchemy types to simple categories
                if "VARCHAR" in col_type or "TEXT" in col_type or "STRING" in col_type:
                    simple_type = "string"
                elif "INTEGER" in col_type or "BIGINT" in col_type or "SMALLINT" in col_type:
                    simple_type = "number"
                elif "FLOAT" in col_type or "REAL" in col_type or "DECIMAL" in col_type or "NUMERIC" in col_type:
                    simple_type = "number"
                elif "BOOLEAN" in col_type or "BOOL" in col_type:
                    simple_type = "boolean"
                elif "DATE" in col_type or "TIME" in col_type:
                    simple_type = "date"
                else:
                    simple_type = "string"  # default
                
                # Check if this column is a foreign key
                foreign_key_info = None
                for fk in fk_constraints:
                    if col["name"] in fk["constrained_columns"]:
                        fk_index = fk["constrained_columns"].index(col["name"])
                        foreign_key_info = {
                            "table": fk["referred_table"],
                            "column": fk["referred_columns"][fk_index]
                        }
                        break
                
                columns_info.append({
                    "name": col["name"],
                    "type": simple_type,
                    "nullable": col["nullable"],
                    "primary_key": col["name"] in pk_columns,
                    "foreign_key": foreign_key_info
                })
            
            enhanced_schema[table_name] = {
                "columns": columns_info,
                "primary_keys": pk_columns
            }
        
        return enhanced_schema
    
    async with engine.connect() as conn:
        schema = await conn.run_sync(_get_enhanced_schema_sync)
    
    return schema

@app.get("/")
async def root():
    return {"message": "Dynamic SQL API is running"}
