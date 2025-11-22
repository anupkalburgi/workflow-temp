from typing import List, Optional, Any, Union, Dict
from enum import Enum
from pydantic import BaseModel, Field

class Operator(str, Enum):
    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    LIKE = "like"
    IN = "in"
    BETWEEN = "between"

class AggregationFunction(str, Enum):
    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"

class WindowFunctionType(str, Enum):
    RANK = "rank"
    DENSE_RANK = "dense_rank"
    ROW_NUMBER = "row_number"

class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"

class Filter(BaseModel):
    column: str
    operator: Operator
    value: Any

class Aggregation(BaseModel):
    column: str
    function: AggregationFunction
    alias: Optional[str] = None

class Sort(BaseModel):
    column: str
    direction: SortDirection

class WindowFunction(BaseModel):
    function: WindowFunctionType
    partition_by: List[str] = Field(default_factory=list)
    order_by: List[Sort] = Field(default_factory=list)
    alias: str

class QueryPlan(BaseModel):
    table: str
    filters: List[Filter] = Field(default_factory=list)
    group_by: List[str] = Field(default_factory=list)
    aggregations: List[Aggregation] = Field(default_factory=list)
    window_functions: List[WindowFunction] = Field(default_factory=list)
    sorts: List[Sort] = Field(default_factory=list)
    limit: Optional[int] = 100
    offset: Optional[int] = 0

class MutationType(str, Enum):
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"

class MutationPlan(BaseModel):
    table: str
    operation: MutationType
    data: Optional[Dict[str, Any]] = None
    filters: List[Filter] = Field(default_factory=list)

