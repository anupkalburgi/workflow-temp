"use client";

import React, { useEffect, useState } from 'react';
import { Container, Typography, Box, Button, Paper, CircularProgress, TextField, MenuItem, Select, FormControl, InputLabel, Chip } from '@mui/material';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { prettifyTableName, prettifyColumnName, getOperatorsForType, type SchemaMap, type ColumnInfo } from '@/lib/schemaUtils';

const darkTheme = createTheme({
    palette: {
        mode: 'dark',
        primary: {
            main: '#90caf9',
        },
        background: {
            default: '#121212',
            paper: '#1e1e1e',
        },
    },
});

const API_URL = "http://127.0.0.1:8000";

export default function TableView({ params }: { params: Promise<{ tableName: string }> }) {
    // Unwrap params for Next.js 15+ compatibility
    const { tableName } = React.use(params);

    const [schema, setSchema] = useState<SchemaMap | null>(null);
    const [tableSchema, setTableSchema] = useState<{ columns: ColumnInfo[], primary_keys: string[] } | null>(null);
    const [rows, setRows] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [columns, setColumns] = useState<GridColDef[]>([]);

    // Filter state
    const [filterCol, setFilterCol] = useState("");
    const [filterOp, setFilterOp] = useState("eq");
    const [filterVal, setFilterVal] = useState("");
    const [dateStart, setDateStart] = useState("");
    const [dateEnd, setDateEnd] = useState("");

    // Aggregation state
    const [aggFunc, setAggFunc] = useState("count");
    const [aggCol, setAggCol] = useState("");
    const [groupCol, setGroupCol] = useState("");
    const [aggResult, setAggResult] = useState<any>(null);

    const router = useRouter();

    const fetchAggregation = async () => {
        if (!aggCol) return;

        try {
            const payload: any = {
                table: tableName,
                aggregations: [{
                    function: aggFunc,
                    column: aggCol,
                    alias: "result"
                }]
            };

            if (groupCol) {
                payload.group_by = [groupCol];
            }

            // Apply current filters to aggregation too!
            const filters = [];
            const selectedColDef = tableSchema?.columns.find(c => c.name === filterCol);
            if (selectedColDef?.type === 'date' && dateStart && dateEnd) {
                filters.push({ column: filterCol, operator: 'between', value: [dateStart, dateEnd] });
            } else if (filterVal) {
                filters.push({ column: filterCol, operator: filterOp, value: filterVal });
            }
            payload.filters = filters;

            const res = await axios.post(`${API_URL}/execute`, payload);

            if (groupCol) {
                setAggResult(res.data);
            } else {
                setAggResult(res.data[0]?.result);
            }
        } catch (error) {
            console.error("Error fetching aggregation:", error);
        }
    };

    useEffect(() => {
        const init = async () => {
            try {
                // Fetch schema
                const schemaRes = await axios.get(`${API_URL}/schema/enhanced`);
                setSchema(schemaRes.data);

                const currentTableSchema = schemaRes.data[tableName];
                if (!currentTableSchema) {
                    console.error(`Table ${tableName} not found`);
                    return;
                }
                setTableSchema(currentTableSchema);

                // Generate Grid Columns
                const gridCols: GridColDef[] = currentTableSchema.columns.map((col: ColumnInfo) => ({
                    field: col.name,
                    headerName: prettifyColumnName(col.name),
                    flex: 1,
                    minWidth: 150,
                }));

                // Add Actions Column
                gridCols.push({
                    field: 'actions',
                    headerName: 'Actions',
                    width: 150,
                    renderCell: (params: GridRenderCellParams) => (
                        <Button
                            variant="contained"
                            size="small"
                            onClick={() => {
                                // Find primary key value (assuming single PK for now)
                                const pk = currentTableSchema.primary_keys[0] || 'id';
                                const id = params.row[pk];
                                router.push(`/tables/${tableName}/${id}`);
                            }}
                        >
                            View / Edit
                        </Button>
                    ),
                });

                setColumns(gridCols);

                // Set default filter column
                if (currentTableSchema.columns.length > 0) {
                    setFilterCol(currentTableSchema.columns[0].name);
                    setAggCol(currentTableSchema.columns[0].name);
                }

                // Fetch initial data
                await fetchData(tableName);

            } catch (error) {
                console.error("Error initializing table view:", error);
            } finally {
                setLoading(false);
            }
        };

        init();
    }, [tableName]);

    const fetchData = async (table: string, filters: any[] = []) => {
        try {
            const res = await axios.post(`${API_URL}/execute`, {
                table: table,
                filters: filters,
                limit: 100
            });
            setRows(res.data);
        } catch (error) {
            console.error("Error fetching data:", error);
        }
    };

    const handleApplyFilter = () => {
        if (!tableSchema) return;

        const filters = [];

        // Check if we are filtering by date range
        const selectedColDef = tableSchema.columns.find(c => c.name === filterCol);

        if (selectedColDef?.type === 'date' && dateStart && dateEnd) {
            filters.push({
                column: filterCol,
                operator: 'between',
                value: [dateStart, dateEnd]
            });
        } else if (filterVal) {
            filters.push({
                column: filterCol,
                operator: filterOp,
                value: filterVal
            });
        }

        fetchData(tableName, filters);
    };

    const handleClearFilter = () => {
        setFilterVal("");
        setDateStart("");
        setDateEnd("");
        setFilterOp("eq");
        fetchData(tableName);
    };

    const getFilterInput = () => {
        if (!tableSchema || !filterCol) return null;

        const colDef = tableSchema.columns.find(c => c.name === filterCol);
        if (!colDef) return null;

        if (colDef.type === 'date') {
            return (
                <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                    <TextField
                        size="small"
                        type="date"
                        label="Start"
                        InputLabelProps={{ shrink: true }}
                        value={dateStart}
                        onChange={(e) => setDateStart(e.target.value)}
                    />
                    <Typography>-</Typography>
                    <TextField
                        size="small"
                        type="date"
                        label="End"
                        InputLabelProps={{ shrink: true }}
                        value={dateEnd}
                        onChange={(e) => setDateEnd(e.target.value)}
                    />
                </Box>
            );
        }

        return (
            <TextField
                size="small"
                label="Value"
                value={filterVal}
                onChange={(e) => setFilterVal(e.target.value)}
                type={colDef.type === 'number' ? 'number' : 'text'}
            />
        );
    };

    return (
        <ThemeProvider theme={darkTheme}>
            <CssBaseline />
            <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
                <Button onClick={() => router.push('/')} sx={{ mb: 2 }}>&larr; Back to Dashboard</Button>

                <Typography variant="h4" gutterBottom sx={{ color: 'primary.main', fontWeight: 'bold' }}>
                    {prettifyTableName(tableName)}
                </Typography>

                {/* Analytics Panel */}
                <Paper sx={{ p: 3, mb: 4, borderRadius: 2 }}>
                    <Typography variant="h6" gutterBottom>Analytics</Typography>
                    <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap', mb: 2 }}>
                        <FormControl size="small" sx={{ minWidth: 120 }}>
                            <InputLabel>Function</InputLabel>
                            <Select value={aggFunc} label="Function" onChange={(e) => setAggFunc(e.target.value)}>
                                <MenuItem value="count">Count</MenuItem>
                                <MenuItem value="sum">Sum</MenuItem>
                                <MenuItem value="avg">Average</MenuItem>
                                <MenuItem value="min">Min</MenuItem>
                                <MenuItem value="max">Max</MenuItem>
                            </Select>
                        </FormControl>

                        <FormControl size="small" sx={{ minWidth: 150 }}>
                            <InputLabel>Column</InputLabel>
                            <Select value={aggCol} label="Column" onChange={(e) => setAggCol(e.target.value)}>
                                {tableSchema?.columns.map(col => (
                                    <MenuItem key={col.name} value={col.name}>
                                        {prettifyColumnName(col.name)}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>

                        <FormControl size="small" sx={{ minWidth: 150 }}>
                            <InputLabel>Group By (Optional)</InputLabel>
                            <Select value={groupCol} label="Group By (Optional)" onChange={(e) => setGroupCol(e.target.value)} displayEmpty>
                                <MenuItem value=""><em>None</em></MenuItem>
                                {tableSchema?.columns.map(col => (
                                    <MenuItem key={col.name} value={col.name}>
                                        {prettifyColumnName(col.name)}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>

                        <Button variant="contained" onClick={fetchAggregation}>Calculate</Button>
                    </Box>

                    {/* Aggregation Results */}
                    {aggResult && !Array.isArray(aggResult) && (
                        <Box sx={{ mt: 2 }}>
                            <Chip
                                label={`${aggFunc.toUpperCase()}(${prettifyColumnName(aggCol)}): ${typeof aggResult === 'number' ? aggResult.toLocaleString() : aggResult}`}
                                color="success"
                                sx={{ fontSize: '1.1rem', py: 2 }}
                            />
                        </Box>
                    )}

                    {aggResult && Array.isArray(aggResult) && (
                        <Box sx={{ mt: 2, height: 300, width: '100%' }}>
                            <DataGrid
                                rows={aggResult.map((r, i) => ({ id: i, ...r }))}
                                columns={[
                                    { field: groupCol, headerName: prettifyColumnName(groupCol), flex: 1 },
                                    { field: 'result', headerName: `${aggFunc.toUpperCase()} of ${prettifyColumnName(aggCol)}`, flex: 1 }
                                ]}
                                sx={{ border: 0 }}
                                density="compact"
                            />
                        </Box>
                    )}
                </Paper>

                {/* Filters Panel */}
                <Paper sx={{ p: 3, mb: 4, borderRadius: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                        <Typography variant="h6">Filters</Typography>
                        <Button variant="outlined" size="small" onClick={handleClearFilter}>Clear Filters</Button>
                    </Box>

                    <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
                        <FormControl size="small" sx={{ minWidth: 150 }}>
                            <InputLabel>Column</InputLabel>
                            <Select
                                value={filterCol}
                                label="Column"
                                onChange={(e) => {
                                    setFilterCol(e.target.value);
                                    setFilterVal(""); // Clear value when column changes
                                    setFilterOp("eq"); // Reset operator
                                }}
                            >
                                {tableSchema?.columns.map(col => (
                                    <MenuItem key={col.name} value={col.name}>
                                        {prettifyColumnName(col.name)}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>

                        {filterCol && tableSchema && (
                            <FormControl size="small" sx={{ minWidth: 100 }}>
                                <InputLabel>Operator</InputLabel>
                                <Select
                                    value={filterOp}
                                    label="Operator"
                                    onChange={(e) => setFilterOp(e.target.value)}
                                >
                                    {getOperatorsForType(tableSchema.columns.find(c => c.name === filterCol)?.type || 'string').map(op => (
                                        <MenuItem key={op.value} value={op.value}>{op.label}</MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        )}

                        {getFilterInput()}

                        <Button variant="contained" onClick={handleApplyFilter}>Apply</Button>
                    </Box>
                </Paper>

                {/* Data Grid */}
                <Paper sx={{ height: 600, width: '100%', borderRadius: 2, overflow: 'hidden' }}>
                    {loading ? (
                        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                            <CircularProgress />
                        </Box>
                    ) : (
                        <DataGrid
                            rows={rows}
                            columns={columns}
                            getRowId={(row) => {
                                const pk = tableSchema?.primary_keys[0] || 'id';
                                return row[pk] || Math.random();
                            }}
                            sx={{ border: 0 }}
                        />
                    )}
                </Paper>
            </Container>
        </ThemeProvider>
    );
}
