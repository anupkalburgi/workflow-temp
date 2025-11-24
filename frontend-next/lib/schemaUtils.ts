/**
 * Helper functions for working with schema metadata
 */

export interface ColumnInfo {
    name: string;
    type: "string" | "number" | "boolean" | "date";
    nullable: boolean;
    primary_key: boolean;
    foreign_key: { table: string; column: string } | null;
}

export interface TableSchema {
    columns: ColumnInfo[];
    primary_keys: string[];
}

export type SchemaMap = Record<string, TableSchema>;

/**
 * Convert table name from snake_case to Title Case
 * Examples: "users" → "Users", "claim_items" → "Claim Items"
 */
export function prettifyTableName(tableName: string): string {
    return tableName
        .split("_")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

/**
 * Convert column name from snake_case to Title Case
 * Examples: "user_id" → "User ID", "first_name" → "First Name"
 */
export function prettifyColumnName(columnName: string): string {
    return columnName
        .split("_")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

/**
 * Get appropriate operator for a column type
 */
export function getOperatorsForType(type: string): Array<{ value: string, label: string }> {
    if (type === "string") {
        return [
            { value: "eq", label: "=" },
            { value: "neq", label: "!=" },
            { value: "like", label: "Contains" },
        ];
    } else if (type === "number" || type === "date") {
        return [
            { value: "eq", label: "=" },
            { value: "neq", label: "!=" },
            { value: "gt", label: ">" },
            { value: "lt", label: "<" },
            { value: "gte", label: ">=" },
            { value: "lte", label: "<=" },
            { value: "between", label: "Between" },
        ];
    } else if (type === "boolean") {
        return [
            { value: "eq", label: "=" },
        ];
    }
    return [{ value: "eq", label: "=" }];
}

/**
 * Get aggregation functions suitable for a column type
 */
export function getAggregationsForType(type: string): Array<{ value: string, label: string }> {
    if (type === "number") {
        return [
            { value: "count", label: "Count" },
            { value: "sum", label: "Sum" },
            { value: "avg", label: "Average" },
            { value: "min", label: "Min" },
            { value: "max", label: "Max" },
        ];
    }
    return [{ value: "count", label: "Count" }];
}
