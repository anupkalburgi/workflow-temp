"use client";

import React, { useEffect, useState } from 'react';
import { Container, Typography, Box, Button, Paper, CircularProgress, TextField, Grid, FormControl, InputLabel, Select, MenuItem, Checkbox, FormControlLabel, Alert } from '@mui/material';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { prettifyTableName, prettifyColumnName, type SchemaMap, type ColumnInfo } from '@/lib/schemaUtils';

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

export default function GenericDetail({ params }: { params: Promise<{ tableName: string, id: string }> }) {
    const { tableName, id } = React.use(params);
    const router = useRouter();

    const [schema, setSchema] = useState<SchemaMap | null>(null);
    const [tableSchema, setTableSchema] = useState<{ columns: ColumnInfo[], primary_keys: string[] } | null>(null);
    const [data, setData] = useState<any>({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Foreign key options
    const [fkOptions, setFkOptions] = useState<Record<string, any[]>>({});

    useEffect(() => {
        const init = async () => {
            try {
                // 1. Fetch Schema
                const schemaRes = await axios.get(`${API_URL}/schema/enhanced`);
                setSchema(schemaRes.data);

                const currentTableSchema = schemaRes.data[tableName];
                if (!currentTableSchema) {
                    setError(`Table ${tableName} not found`);
                    setLoading(false);
                    return;
                }
                setTableSchema(currentTableSchema);

                // 2. Fetch Data
                const pk = currentTableSchema.primary_keys[0] || 'id';
                // Determine if ID is number or string based on schema
                const pkCol = currentTableSchema.columns.find((c: ColumnInfo) => c.name === pk);
                const idValue = pkCol?.type === 'number' ? parseInt(id) : id;

                const dataRes = await axios.post(`${API_URL}/execute`, {
                    table: tableName,
                    filters: [{ column: pk, operator: 'eq', value: idValue }]
                });

                if (dataRes.data.length > 0) {
                    setData(dataRes.data[0]);
                } else {
                    setError("Record not found");
                }

                // 3. Fetch Foreign Key Options
                const fkCols = currentTableSchema.columns.filter((c: ColumnInfo) => c.foreign_key);
                const options: Record<string, any[]> = {};

                for (const col of fkCols) {
                    if (col.foreign_key) {
                        const fkTable = col.foreign_key.table;
                        const fkTargetCol = col.foreign_key.column;

                        // Fetch all rows from the related table (limit 100 for now)
                        // Ideally we'd want a label column, but we'll try to guess one
                        const fkRes = await axios.post(`${API_URL}/execute`, {
                            table: fkTable,
                            limit: 100
                        });

                        options[col.name] = fkRes.data.map((row: any) => ({
                            value: row[fkTargetCol],
                            label: row.name || row.title || row.submission_number || row.claim_number || row[fkTargetCol]
                        }));
                    }
                }
                setFkOptions(options);

            } catch (err: any) {
                console.error("Error initializing detail view:", err);
                setError(err.message || "An error occurred");
            } finally {
                setLoading(false);
            }
        };

        init();
    }, [tableName, id]);

    const handleSave = async () => {
        setSaving(true);
        setError(null);
        try {
            const pk = tableSchema?.primary_keys[0] || 'id';

            // Prepare data for update (exclude PK if it's not changing, but we need it for WHERE clause)
            // Actually, for the mutation endpoint, we pass data and filters separately

            // Filter out keys that are not in the schema columns to avoid errors
            const validData: any = {};
            tableSchema?.columns.forEach(col => {
                if (col.name !== pk && data[col.name] !== undefined) {
                    validData[col.name] = data[col.name];
                }
            });

            const pkCol = tableSchema?.columns.find(c => c.name === pk);
            const idValue = pkCol?.type === 'number' ? parseInt(id) : id;

            await axios.post(`${API_URL}/mutate`, {
                table: tableName,
                operation: "update",
                data: validData,
                filters: [{ column: pk, operator: "eq", value: idValue }]
            });

            router.push(`/tables/${tableName}`);
        } catch (err: any) {
            console.error("Error saving:", err);
            setError(err.response?.data?.detail || "Failed to save changes");
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!confirm("Are you sure you want to delete this record?")) return;

        setSaving(true);
        try {
            const pk = tableSchema?.primary_keys[0] || 'id';
            const pkCol = tableSchema?.columns.find(c => c.name === pk);
            const idValue = pkCol?.type === 'number' ? parseInt(id) : id;

            await axios.post(`${API_URL}/mutate`, {
                table: tableName,
                operation: "delete",
                filters: [{ column: pk, operator: "eq", value: idValue }]
            });

            router.push(`/tables/${tableName}`);
        } catch (err: any) {
            console.error("Error deleting:", err);
            setError(err.response?.data?.detail || "Failed to delete record");
            setSaving(false);
        }
    };

    const handleChange = (field: string, value: any) => {
        setData({ ...data, [field]: value });
    };

    if (loading) {
        return (
            <ThemeProvider theme={darkTheme}>
                <CssBaseline />
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 10 }}>
                    <CircularProgress />
                </Box>
            </ThemeProvider>
        );
    }

    return (
        <ThemeProvider theme={darkTheme}>
            <CssBaseline />
            <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
                <Button onClick={() => router.push(`/tables/${tableName}`)} sx={{ mb: 2 }}>
                    &larr; Back to {prettifyTableName(tableName)}
                </Button>

                <Paper sx={{ p: 4, borderRadius: 2 }}>
                    <Typography variant="h4" gutterBottom sx={{ color: 'primary.main', mb: 4 }}>
                        Edit {prettifyTableName(tableName)} Record
                    </Typography>

                    {error && (
                        <Alert severity="error" sx={{ mb: 3 }}>
                            {error}
                        </Alert>
                    )}

                    <Grid container spacing={3}>
                        {tableSchema?.columns.map((col) => {
                            const isPk = col.primary_key;
                            const isFk = !!col.foreign_key;

                            // Determine input type
                            if (isFk) {
                                return (
                                    <Grid size={{ xs: 12, sm: 6 }} key={col.name}>
                                        <FormControl fullWidth size="small">
                                            <InputLabel>{prettifyColumnName(col.name)}</InputLabel>
                                            <Select
                                                value={data[col.name] || ''}
                                                label={prettifyColumnName(col.name)}
                                                onChange={(e) => handleChange(col.name, e.target.value)}
                                            >
                                                {fkOptions[col.name]?.map((opt) => (
                                                    <MenuItem key={opt.value} value={opt.value}>
                                                        {opt.label}
                                                    </MenuItem>
                                                ))}
                                            </Select>
                                        </FormControl>
                                    </Grid>
                                );
                            }

                            if (col.type === 'boolean') {
                                return (
                                    <Grid size={{ xs: 12, sm: 6 }} key={col.name}>
                                        <FormControlLabel
                                            control={
                                                <Checkbox
                                                    checked={!!data[col.name]}
                                                    onChange={(e) => handleChange(col.name, e.target.checked)}
                                                    disabled={isPk}
                                                />
                                            }
                                            label={prettifyColumnName(col.name)}
                                        />
                                    </Grid>
                                );
                            }

                            return (
                                <Grid size={{ xs: 12, sm: 6 }} key={col.name}>
                                    <TextField
                                        fullWidth
                                        label={prettifyColumnName(col.name)}
                                        value={data[col.name] || ''}
                                        onChange={(e) => handleChange(col.name, e.target.value)}
                                        disabled={isPk}
                                        type={col.type === 'number' ? 'number' : 'text'}
                                        InputLabelProps={col.type === 'date' ? { shrink: true } : undefined}
                                        size="small"
                                    />
                                </Grid>
                            );
                        })}
                    </Grid>

                    <Box sx={{ mt: 4, display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
                        <Button
                            variant="outlined"
                            color="error"
                            onClick={handleDelete}
                            disabled={saving}
                        >
                            Delete
                        </Button>
                        <Button
                            variant="contained"
                            onClick={handleSave}
                            disabled={saving}
                        >
                            {saving ? 'Saving...' : 'Save Changes'}
                        </Button>
                    </Box>
                </Paper>
            </Container>
        </ThemeProvider>
    );
}
