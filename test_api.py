import asyncio
import aiohttp
import json
from app.schemas import QueryPlan, Filter, Aggregation, Sort, Operator, AggregationFunction, SortDirection

BASE_URL = "http://localhost:8000"

async def seed_data():
    # We can't easily seed via API because we didn't build write endpoints.
    # So we will insert directly into DB using the app's db connection logic.
    from app.database import AsyncSessionLocal
    from app.models import User, Product
    
    async with AsyncSessionLocal() as session:
        # Check if data exists
        result = await session.execute(text("SELECT count(*) FROM users"))
        count = result.scalar()
        if count > 0:
            print("Data already seeded.")
            return

        print("Seeding data...")
        from datetime import datetime
        users = [
            User(name="Alice", age=30, role="admin", salary=100000, joined_at=datetime(2023, 1, 1)),
            User(name="Bob", age=25, role="user", salary=50000, joined_at=datetime(2023, 6, 1)),
            User(name="Charlie", age=35, role="user", salary=60000, joined_at=datetime(2023, 3, 15)),
            User(name="David", age=40, role="manager", salary=80000, joined_at=datetime(2022, 12, 1)),
            User(name="Eve", age=22, role="intern", salary=30000, joined_at=datetime(2023, 8, 1)),
        ]
        session.add_all(users)
        
        products = [
            Product(name="Laptop", category="Electronics", price=1000, stock=50),
            Product(name="Mouse", category="Electronics", price=20, stock=200),
            Product(name="Desk", category="Furniture", price=200, stock=10),
            Product(name="Chair", category="Furniture", price=100, stock=20),
        ]
        session.add_all(products)
        await session.commit()
        print("Data seeded.")

from sqlalchemy import text

async def test_schema():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/schema") as resp:
            print(f"Schema Status: {resp.status}")
            data = await resp.json()
            print(f"Schema: {json.dumps(data, indent=2)}")
            assert "users" in data
            assert "products" in data

async def test_execution():
    async with aiohttp.ClientSession() as session:
        # Test 1: Simple Select
        print("\nTest 1: Simple Select (Users > 25)")
        plan = {
            "table": "users",
            "filters": [
                {"column": "age", "operator": "gt", "value": 25}
            ],
            "sorts": [{"column": "age", "direction": "asc"}]
        }
        async with session.post(f"{BASE_URL}/execute", json=plan) as resp:
            print(f"Status: {resp.status}")
            data = await resp.json()
            print(f"Result: {json.dumps(data, indent=2)}")
            assert len(data) == 3 # Alice, Charlie, David

        # Test 2: Aggregation
        print("\nTest 2: Aggregation (Count by Role)")
        plan = {
            "table": "users",
            "group_by": ["role"],
            "aggregations": [
                {"column": "id", "function": "count", "alias": "count"}
            ]
        }
        async with session.post(f"{BASE_URL}/execute", json=plan) as resp:
            print(f"Status: {resp.status}")
            data = await resp.json()
            print(f"Result: {json.dumps(data, indent=2)}")
            # Should have admin:1, user:2, manager:1, intern:1

        # Test 3: Between Operator
        print("\nTest 3: Between Operator (Salary 40k - 90k)")
        plan = {
            "table": "users",
            "filters": [
                {"column": "salary", "operator": "between", "value": [40000, 90000]}
            ]
        }
        async with session.post(f"{BASE_URL}/execute", json=plan) as resp:
            print(f"Status: {resp.status}")
            data = await resp.json()
            print(f"Result: {json.dumps(data, indent=2)}")
            # Should include Bob(50k), Charlie(60k), David(80k)
            # Excludes Alice(100k), Eve(30k)
            assert len(data) == 3

        # Test 4: Window Function (Rank by Salary)
        print("\nTest 4: Window Function (Rank by Salary DESC)")
        plan = {
            "table": "users",
            "window_functions": [
                {
                    "function": "rank",
                    "order_by": [{"column": "salary", "direction": "desc"}],
                    "alias": "salary_rank"
                }
            ],
            "sorts": [{"column": "salary", "direction": "desc"}]
        }
        async with session.post(f"{BASE_URL}/execute", json=plan) as resp:
            print(f"Status: {resp.status}")
            data = await resp.json()
            print(f"Result: {json.dumps(data, indent=2)}")
            # Alice should be rank 1, David 2, Charlie 3, Bob 4, Eve 5
            assert data[0]["salary_rank"] == 1
            assert data[0]["name"] == "Alice"
            assert data[4]["salary_rank"] == 5
            assert data[4]["name"] == "Eve"

        # Test 5: Date Range (Joined in 2023)
        print("\nTest 5: Date Range (Joined in 2023)")
        plan = {
            "table": "users",
            "filters": [
                {"column": "joined_at", "operator": "between", "value": ["2023-01-01", "2023-12-31"]}
            ]
        }
        async with session.post(f"{BASE_URL}/execute", json=plan) as resp:
            print(f"Status: {resp.status}")
            data = await resp.json()
            print(f"Result: {json.dumps(data, indent=2)}")
            # Should exclude David (2022)
            # Should include Alice, Bob, Charlie, Eve
            assert len(data) == 4
            
        # Test 6: Negative Tests
        print("\nTest 6: Negative Tests")
        
        # Invalid Table
        print("  - Invalid Table")
        plan = {"table": "non_existent_table"}
        async with session.post(f"{BASE_URL}/execute", json=plan) as resp:
            print(f"    Status: {resp.status}")
            assert resp.status == 400 or resp.status == 500
            
        # Invalid Column
        print("  - Invalid Column")
        plan = {
            "table": "users",
            "filters": [{"column": "bad_col", "operator": "eq", "value": 1}]
        }
        async with session.post(f"{BASE_URL}/execute", json=plan) as resp:
            print(f"    Status: {resp.status}")
            assert resp.status == 400 or resp.status == 500
            
        # Invalid Operator (Pydantic Validation Error)
        print("  - Invalid Operator")
        plan = {
            "table": "users",
            "filters": [{"column": "age", "operator": "super_eq", "value": 1}]
        }
        async with session.post(f"{BASE_URL}/execute", json=plan) as resp:
            print(f"    Status: {resp.status}")
            assert resp.status == 422

        # Test 7: CRUD (Mutation)
        print("\nTest 7: CRUD (Mutation)")
        
        # Update User 1 (Alice) salary
        print("  - Update Alice salary to 120000")
        mutation = {
            "table": "users",
            "operation": "update",
            "data": {"salary": 120000},
            "filters": [{"column": "id", "operator": "eq", "value": 1}]
        }
        async with session.post(f"{BASE_URL}/mutate", json=mutation) as resp:
            print(f"    Status: {resp.status}")
            data = await resp.json()
            print(f"    Result: {json.dumps(data, indent=2)}")
            assert resp.status == 200
            
        # Verify update via execute
        plan = {
            "table": "users",
            "filters": [{"column": "id", "operator": "eq", "value": 1}]
        }
        async with session.post(f"{BASE_URL}/execute", json=plan) as resp:
            data = await resp.json()
            assert data[0]["salary"] == 120000

        # Delete User 2 (Bob)
        print("  - Delete Bob")
        mutation = {
            "table": "users",
            "operation": "delete",
            "filters": [{"column": "id", "operator": "eq", "value": 2}]
        }
        async with session.post(f"{BASE_URL}/mutate", json=mutation) as resp:
            print(f"    Status: {resp.status}")
            assert resp.status == 200
            
        # Verify delete
        plan = {
            "table": "users",
            "filters": [{"column": "id", "operator": "eq", "value": 2}]
        }
        async with session.post(f"{BASE_URL}/execute", json=plan) as resp:
            data = await resp.json()
            assert len(data) == 0

async def main():
    # Wait for app to start (we will run this script separately)
    await asyncio.sleep(2) 
    
    # Seed data (requires app code access, so we run this script in the same env)
    await seed_data()
    
    await test_schema()
    await test_execution()

if __name__ == "__main__":
    asyncio.run(main())
