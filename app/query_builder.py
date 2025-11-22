from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, text, insert, update, delete
from sqlalchemy.orm import DeclarativeMeta
from typing import List, Dict, Any, Type
from .schemas import QueryPlan, Operator, AggregationFunction, SortDirection, WindowFunctionType, MutationPlan, MutationType
from .models import Base

import logging

logger = logging.getLogger(__name__)

# Helper to get model by table name
def get_model_by_tablename(tablename: str) -> Type[DeclarativeMeta]:
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        if cls.__tablename__ == tablename:
            return cls
    raise ValueError(f"Table {tablename} not found")

def build_statement(plan: QueryPlan) -> Any:
    model = get_model_by_tablename(plan.table)
    
    # Start building the query
    stmt = select(model)
    
    # 1. Apply Filters
    for filter_item in plan.filters:
        column = getattr(model, filter_item.column, None)
        if not column:
            raise ValueError(f"Column {filter_item.column} not found in {plan.table}")
        
        if filter_item.operator == Operator.EQ:
            stmt = stmt.where(column == filter_item.value)
        elif filter_item.operator == Operator.NEQ:
            stmt = stmt.where(column != filter_item.value)
        elif filter_item.operator == Operator.GT:
            stmt = stmt.where(column > filter_item.value)
        elif filter_item.operator == Operator.LT:
            stmt = stmt.where(column < filter_item.value)
        elif filter_item.operator == Operator.GTE:
            stmt = stmt.where(column >= filter_item.value)
        elif filter_item.operator == Operator.LTE:
            stmt = stmt.where(column <= filter_item.value)
        elif filter_item.operator == Operator.LIKE:
            stmt = stmt.where(column.like(filter_item.value))
        elif filter_item.operator == Operator.IN:
            stmt = stmt.where(column.in_(filter_item.value))
        elif filter_item.operator == Operator.BETWEEN:
            if not isinstance(filter_item.value, (list, tuple)) or len(filter_item.value) != 2:
                raise ValueError(f"Value for BETWEEN operator must be a list of 2 elements")
            stmt = stmt.where(column.between(filter_item.value[0], filter_item.value[1]))

    # 2. Group By, Aggregations, and Window Functions
    # If there are aggregations or window functions, we need to select specific columns
    if plan.aggregations or plan.group_by or plan.window_functions:
        select_items = []
        
        # Add Group By columns to select
        for group_col_name in plan.group_by:
            column = getattr(model, group_col_name, None)
            if not column:
                raise ValueError(f"Column {group_col_name} not found")
            select_items.append(column)
            stmt = stmt.group_by(column)
            
        # Add Aggregations
        for agg in plan.aggregations:
            column = getattr(model, agg.column, None)
            if not column:
                raise ValueError(f"Column {agg.column} not found")
            
            if agg.function == AggregationFunction.COUNT:
                agg_expr = func.count(column)
            elif agg.function == AggregationFunction.SUM:
                agg_expr = func.sum(column)
            elif agg.function == AggregationFunction.AVG:
                agg_expr = func.avg(column)
            elif agg.function == AggregationFunction.MIN:
                agg_expr = func.min(column)
            elif agg.function == AggregationFunction.MAX:
                agg_expr = func.max(column)
            else:
                raise ValueError(f"Unknown aggregation function {agg.function}")
            
            label = agg.alias or f"{agg.function}_{agg.column}"
            select_items.append(agg_expr.label(label))
            
        # Add Window Functions
        for win in plan.window_functions:
            if win.function == WindowFunctionType.RANK:
                win_func = func.rank()
            elif win.function == WindowFunctionType.DENSE_RANK:
                win_func = func.dense_rank()
            elif win.function == WindowFunctionType.ROW_NUMBER:
                win_func = func.row_number()
            else:
                raise ValueError(f"Unknown window function {win.function}")
            
            # Build Partition By
            partition_exprs = []
            for p_col in win.partition_by:
                col = getattr(model, p_col, None)
                if not col:
                    raise ValueError(f"Partition column {p_col} not found")
                partition_exprs.append(col)
                
            # Build Order By for Window
            order_exprs = []
            for s in win.order_by:
                col = getattr(model, s.column, None)
                if not col:
                    raise ValueError(f"Window order column {s.column} not found")
                if s.direction == SortDirection.ASC:
                    order_exprs.append(asc(col))
                else:
                    order_exprs.append(desc(col))
            
            win_expr = win_func.over(partition_by=partition_exprs, order_by=order_exprs)
            select_items.append(win_expr.label(win.alias))

        # If we have select items (due to group by or agg or window), we replace the default select(model)
        # However, if we only have filters and no group/agg/window, we keep select(model)
        if select_items:
            # If we have window functions but NO group by/agg, we might want to include all model columns too?
            # For now, let's assume if you ask for window functions, you must specify what else you want 
            # OR we can append the window function to the model columns.
            # The current logic assumes if select_items is populated, we ONLY select those.
            # If the user wants model columns + rank, they can't express that easily with current schema 
            # unless we add "select_columns" to the plan.
            # BUT, for the sake of this task, let's assume if window function is present, 
            # we should probably include the model columns unless group by is present.
            
            if plan.window_functions and not plan.group_by and not plan.aggregations:
                 # Add all model columns to select_items
                 for col in model.__table__.columns:
                     select_items.insert(0, col)

            stmt = select(*select_items)
            
            # Re-apply filters
            for filter_item in plan.filters:
                column = getattr(model, filter_item.column)
                if filter_item.operator == Operator.EQ:
                    stmt = stmt.where(column == filter_item.value)
                elif filter_item.operator == Operator.NEQ:
                    stmt = stmt.where(column != filter_item.value)
                elif filter_item.operator == Operator.GT:
                    stmt = stmt.where(column > filter_item.value)
                elif filter_item.operator == Operator.LT:
                    stmt = stmt.where(column < filter_item.value)
                elif filter_item.operator == Operator.GTE:
                    stmt = stmt.where(column >= filter_item.value)
                elif filter_item.operator == Operator.LTE:
                    stmt = stmt.where(column <= filter_item.value)
                elif filter_item.operator == Operator.LIKE:
                    stmt = stmt.where(column.like(filter_item.value))
                elif filter_item.operator == Operator.IN:
                    stmt = stmt.where(column.in_(filter_item.value))
                elif filter_item.operator == Operator.BETWEEN:
                    stmt = stmt.where(column.between(filter_item.value[0], filter_item.value[1]))
            
            for group_col_name in plan.group_by:
                column = getattr(model, group_col_name)
                stmt = stmt.group_by(column)

    # 3. Sorting
    for sort_item in plan.sorts:
        column = getattr(model, sort_item.column, None)
        if not column:
            # It might be an alias from aggregation
            # For simplicity, let's assume sorting on model columns for now
            # Or we can try to find it in select_items if we were smarter.
            # Let's stick to model columns for safety.
            continue 
            
        if sort_item.direction == SortDirection.ASC:
            stmt = stmt.order_by(asc(column))
        else:
            stmt = stmt.order_by(desc(column))

    # 4. Pagination
    if plan.limit:
        stmt = stmt.limit(plan.limit)
    if plan.offset:
        stmt = stmt.offset(plan.offset)
        
    return stmt

async def execute_query_plan(plan: QueryPlan, session: AsyncSession) -> List[Dict[str, Any]]:
    stmt = build_statement(plan)
    
    # Log the statement
    # Note: compile with literal_binds=True is good for debugging but might fail for some types
    # For production logging we might want to log the statement and params separately
    try:
        compiled_stmt = stmt.compile(compile_kwargs={"literal_binds": True})
        logger.info(f"Generated SQL: {compiled_stmt}")
        print(f"Generated SQL: {compiled_stmt}") # Print for visibility in this demo
    except Exception as e:
        logger.warning(f"Could not compile statement for logging: {e}")

    # Execute
    result = await session.execute(stmt)
    
    # For aggregation/grouping/window, result is rows of values
    if plan.group_by or plan.aggregations or plan.window_functions:
        return [dict(row) for row in result.mappings().all()]
    
    # For simple select, result is model instances
    # We need to convert them to dicts
    rows = result.scalars().all()
    return [{c.name: getattr(row, c.name) for c in row.__table__.columns} for row in rows]

async def execute_mutation_plan(plan: MutationPlan, session: AsyncSession):
    model = get_model_by_tablename(plan.table)
    if not model:
        raise ValueError(f"Table {plan.table} not found")

    if plan.operation == MutationType.INSERT:
        if not plan.data:
            raise ValueError("Data is required for INSERT")
        stmt = insert(model).values(**plan.data)
        
        # Log SQL
        try:
            compiled_stmt = stmt.compile(compile_kwargs={"literal_binds": True})
            logger.info(f"🔧 Generated SQL (INSERT): {compiled_stmt}")
        except Exception as e:
            logger.warning(f"Could not compile statement for logging: {e}")
            
        await session.execute(stmt)
        await session.commit()
        return {"message": "Inserted successfully"}

    elif plan.operation == MutationType.UPDATE:
        if not plan.data:
            raise ValueError("Data is required for UPDATE")
        
        # Convert datetime strings to datetime objects
        from datetime import datetime as dt
        processed_data = {}
        for key, value in plan.data.items():
            column = getattr(model, key, None)
            if column is not None:
                try:
                    # Check if this is a DateTime column by checking the column type name
                    column_type_name = str(column.type)
                    if 'DATETIME' in column_type_name.upper() and isinstance(value, str):
                        # Parse ISO format datetime string
                        parsed_dt = dt.fromisoformat(value.replace('Z', '+00:00'))
                        processed_data[key] = parsed_dt
                        logger.info(f"Converted {key} from '{value}' to {parsed_dt}")
                    else:
                        processed_data[key] = value
                except Exception as e:
                    logger.warning(f"Error processing column {key}: {e}")
                    processed_data[key] = value
            else:
                processed_data[key] = value
        
        logger.info(f"Processed data for UPDATE: {processed_data}")
        stmt = update(model).values(**processed_data)
        
        # Apply filters
        for filter in plan.filters:
            column = getattr(model, filter.column, None)
            if not column:
                raise ValueError(f"Column {filter.column} not found on table {plan.table}")
            
            if filter.operator == Operator.EQ:
                stmt = stmt.where(column == filter.value)
            elif filter.operator == Operator.NEQ:
                stmt = stmt.where(column != filter.value)
            elif filter.operator == Operator.GT:
                stmt = stmt.where(column > filter.value)
            elif filter.operator == Operator.LT:
                stmt = stmt.where(column < filter.value)
            elif filter.operator == Operator.GTE:
                stmt = stmt.where(column >= filter.value)
            elif filter.operator == Operator.LTE:
                stmt = stmt.where(column <= filter.value)
            elif filter.operator == Operator.LIKE:
                stmt = stmt.where(column.like(filter.value))
            elif filter.operator == Operator.IN:
                stmt = stmt.where(column.in_(filter.value))
            elif filter.operator == Operator.BETWEEN:
                stmt = stmt.where(column.between(filter.value[0], filter.value[1]))
        
        # Log SQL
        try:
            compiled_stmt = stmt.compile(compile_kwargs={"literal_binds": True})
            logger.info(f"🔧 Generated SQL (UPDATE): {compiled_stmt}")
        except Exception as e:
            logger.warning(f"Could not compile statement for logging: {e}")
            
        await session.execute(stmt)
        await session.commit()
        return {"message": "Updated successfully"}

    elif plan.operation == MutationType.DELETE:
        stmt = delete(model)
        
        # Apply filters (same logic as update, maybe refactor filter logic later)
        for filter in plan.filters:
            column = getattr(model, filter.column, None)
            if not column:
                raise ValueError(f"Column {filter.column} not found on table {plan.table}")
            
            if filter.operator == Operator.EQ:
                stmt = stmt.where(column == filter.value)
            elif filter.operator == Operator.NEQ:
                stmt = stmt.where(column != filter.value)
            elif filter.operator == Operator.GT:
                stmt = stmt.where(column > filter.value)
            elif filter.operator == Operator.LT:
                stmt = stmt.where(column < filter.value)
            elif filter.operator == Operator.GTE:
                stmt = stmt.where(column >= filter.value)
            elif filter.operator == Operator.LTE:
                stmt = stmt.where(column <= filter.value)
            elif filter.operator == Operator.LIKE:
                stmt = stmt.where(column.like(filter.value))
            elif filter.operator == Operator.IN:
                stmt = stmt.where(column.in_(filter.value))
            elif filter.operator == Operator.BETWEEN:
                stmt = stmt.where(column.between(filter.value[0], filter.value[1]))

        await session.execute(stmt)
        await session.commit()
        return {"message": "Deleted successfully"}
