"use client";

import React, { useEffect, useState, use } from 'react';
import { Container, Typography, Box, Button, Paper, CircularProgress, Grid, TextField, MenuItem, Select, FormControl, InputLabel, Chip } from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

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

export default function DepartmentDetails({ params }: { params: Promise<{ name: string }> }) {
    const { name } = use(params);
    const decodedName = decodeURIComponent(name);
    const [rows, setRows] = useState([]);
    const [columns, setColumns] = useState<GridColDef[]>([]);
    const [loading, setLoading] = useState(true);
    const [aggResult, setAggResult] = useState<any>(null);
    const router = useRouter();

    // Filter State
    const [filterCol, setFilterCol] = useState("");
    const [filterOp, setFilterOp] = useState("eq");
    const [filterVal, setFilterVal] = useState("");
    const [dateStart, setDateStart] = useState("");
    const [dateEnd, setDateEnd] = useState("");

    // Aggregation State
    const [aggFunc, setAggFunc] = useState("avg");
    const [aggCol, setAggCol] = useState("salary");

    const fetchUsers = async () => {
        setLoading(true);
        try {
            // Build Filters
            const filters = [{ column: "department", operator: "eq", value: decodedName }];

            if (filterCol && filterVal) {
                filters.push({ column: filterCol, operator: filterOp, value: isNaN(Number(filterVal)) ? filterVal : Number(filterVal) });
            }

            if (dateStart && dateEnd) {
                filters.push({ column: "joined_at", operator: "between", value: [dateStart, dateEnd] });
            }

            // Fetch Data
            const res = await axios.post(`${API_URL}/execute`, {
                table: "users",
                filters: filters
            });
            setRows(res.data);

            // Generate Columns if not set
            if (columns.length === 0 && res.data.length > 0) {
                const cols: GridColDef[] = Object.keys(res.data[0]).map(key => ({
                    field: key,
                    headerName: key.charAt(0).toUpperCase() + key.slice(1),
                    flex: 1,
                    minWidth: 100,
                }));

                // Add Actions Column
                cols.push({
                    field: 'actions',
                    headerName: 'Actions',
                    width: 150,
                    renderCell: (params) => (
                        <Button
                            variant="contained"
                            size="small"
                            onClick={() => router.push(`/users/${params.row.id}`)}
                        >
                            View / Edit
                        </Button>
                    ),
                });

                setColumns(cols);
            }
        } catch (error) {
            console.error("Error fetching users:", error);
        } finally {
            setLoading(false);
        }
    };

    const fetchAggregation = async () => {
        try {
            const filters = [{ column: "department", operator: "eq", value: decodedName }];
            if (dateStart && dateEnd) {
                filters.push({ column: "joined_at", operator: "between", value: [dateStart, dateEnd] });
            }

            const res = await axios.post(`${API_URL}/execute`, {
                table: "users",
                filters: filters,
                aggregations: [{ function: aggFunc, column: aggCol, alias: "result" }]
            });

            if (res.data && res.data.length > 0) {
                setAggResult(res.data[0].result);
            }
        } catch (error) {
            console.error("Error fetching aggregation:", error);
        }
    };

    useEffect(() => {
        fetchUsers();
        fetchAggregation();
    }, [decodedName]); // Initial load

    const clearFilters = () => {
        setFilterCol("");
        setFilterOp("eq");
        setFilterVal("");
        setDateStart("");
        setDateEnd("");
        fetchUsers();
        fetchAggregation();
    };

    return (
        <ThemeProvider theme={darkTheme}>
            <CssBaseline />
            <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
                <Button onClick={() => router.push('/')} sx={{ mb: 2 }}>&larr; Back to Dashboard</Button>

                <Typography variant="h4" gutterBottom sx={{ color: 'primary.main', fontWeight: 'bold' }}>
                    {decodedName} Department
                </Typography>

                {/* Aggregation Panel */}
                <Paper sx={{ p: 3, mb: 4, borderRadius: 2 }}>
                    <Typography variant="h6" gutterBottom>Analytics</Typography>
                    <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
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
                        <FormControl size="small" sx={{ minWidth: 120 }}>
                            <InputLabel>Column</InputLabel>
                            <Select value={aggCol} label="Column" onChange={(e) => setAggCol(e.target.value)}>
                                <MenuItem value="salary">Salary</MenuItem>
                                <MenuItem value="age">Age</MenuItem>
                                <MenuItem value="id">ID</MenuItem>
                            </Select>
                        </FormControl>
                        <Button variant="contained" onClick={fetchAggregation}>Calculate</Button>
                        {aggResult !== null && (
                            <Chip label={`${aggFunc.toUpperCase()}(${aggCol}): ${Number(aggResult).toLocaleString()}`} color="success" sx={{ fontSize: '1.1rem', py: 2 }} />
                        )}
                    </Box>
                </Paper>

                {/* Filters Panel */}
                <Paper sx={{ p: 3, mb: 4, borderRadius: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                        <Typography variant="h6">Filters</Typography>
                        <Button variant="outlined" size="small" onClick={clearFilters}>Clear Filters</Button>
                    </Box>
                    <Grid container spacing={2} alignItems="center">
                        {/* General Filter */}
                        <Grid size={{ xs: 12, md: 4 }}>
                            <Box sx={{ display: 'flex', gap: 1 }}>
                                <TextField size="small" label="Column" value={filterCol} onChange={(e) => setFilterCol(e.target.value)} />
                                <Select size="small" value={filterOp} onChange={(e) => setFilterOp(e.target.value)} sx={{ minWidth: 80 }}>
                                    <MenuItem value="eq">=</MenuItem>
                                    <MenuItem value="neq">!=</MenuItem>
                                    <MenuItem value="gt">&gt;</MenuItem>
                                    <MenuItem value="lt">&lt;</MenuItem>
                                    <MenuItem value="like">Like</MenuItem>
                                </Select>
                                <TextField size="small" label="Value" value={filterVal} onChange={(e) => setFilterVal(e.target.value)} />
                            </Box>
                        </Grid>

                        {/* Date Filter */}
                        <Grid size={{ xs: 12, md: 5 }}>
                            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                                <TextField
                                    size="small"
                                    type="date"
                                    label="Joined After"
                                    InputLabelProps={{ shrink: true }}
                                    value={dateStart}
                                    onChange={(e) => setDateStart(e.target.value)}
                                    placeholder=""
                                />
                                <Typography>-</Typography>
                                <TextField
                                    size="small"
                                    type="date"
                                    label="Joined Before"
                                    InputLabelProps={{ shrink: true }}
                                    value={dateEnd}
                                    onChange={(e) => setDateEnd(e.target.value)}
                                    placeholder=""
                                />
                            </Box>
                        </Grid>

                        <Grid size={{ xs: 12, md: 3 }}>
                            <Button variant="contained" fullWidth onClick={() => { fetchUsers(); fetchAggregation(); }}>Apply Filters</Button>
                        </Grid>
                    </Grid>
                </Paper>

                {/* Data Grid */}
                <Paper sx={{ height: 600, width: '100%', p: 2, borderRadius: 2, boxShadow: 3 }}>
                    {loading ? (
                        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                            <CircularProgress />
                        </Box>
                    ) : (
                        <DataGrid
                            rows={rows}
                            columns={columns}
                            initialState={{
                                pagination: { paginationModel: { page: 0, pageSize: 10 } },
                            }}
                            pageSizeOptions={[5, 10, 20]}
                            checkboxSelection
                            disableRowSelectionOnClick
                            sx={{ border: 0 }}
                        />
                    )}
                </Paper>
            </Container>
        </ThemeProvider>
    );
}
