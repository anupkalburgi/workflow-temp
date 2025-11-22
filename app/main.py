from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import inspect
from typing import List, Dict, Any
from .database import get_db, engine, Base
from .schemas import QueryPlan, MutationPlan
from .query_builder import execute_query_plan, execute_mutation_plan
from .models import User, Product
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
    from datetime import datetime
    
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

@app.get("/")
async def root():
    return {"message": "Dynamic SQL API is running"}
