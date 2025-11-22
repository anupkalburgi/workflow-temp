import pytest
from app.schemas import QueryPlan, Filter, Operator, Sort, SortDirection
from app.query_builder import build_statement
from app.models import User

# We need to mock the database session or just test the statement compilation
# Since build_statement returns a sqlalchemy Select object, we can compile it to string.

def compile_stmt(stmt):
    return str(stmt.compile(compile_kwargs={"literal_binds": True}))

def test_simple_select():
    plan = QueryPlan(
        table="users",
        filters=[
            Filter(column="age", operator=Operator.GT, value=25)
        ]
    )
    stmt = build_statement(plan)
    sql = compile_stmt(stmt)
    print(f"Generated SQL: {sql}")
    assert "SELECT users.id, users.name, users.age, users.role, users.is_active, users.salary" in sql
    assert "FROM users" in sql
    assert "WHERE users.age > 25" in sql

def test_between_operator():
    plan = QueryPlan(
        table="users",
        filters=[
            Filter(column="salary", operator=Operator.BETWEEN, value=[50000, 80000])
        ]
    )
    stmt = build_statement(plan)
    sql = compile_stmt(stmt)
    print(f"Generated SQL: {sql}")
    assert "users.salary BETWEEN 50000 AND 80000" in sql

def test_rank_window_function():
    plan = QueryPlan(
        table="users",
        window_functions=[
            {
                "function": "rank",
                "order_by": [{"column": "salary", "direction": "desc"}],
                "alias": "salary_rank"
            }
        ]
    )
    stmt = build_statement(plan)
    sql = compile_stmt(stmt)
    print(f"Generated SQL: {sql}")
    assert "rank() OVER (ORDER BY users.salary DESC) AS salary_rank" in sql
