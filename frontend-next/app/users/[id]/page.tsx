"use client";

import React, { useEffect, useState, use } from 'react';
import { Container, Typography, Box, Button, Paper, TextField, CircularProgress, Grid, Alert } from '@mui/material';
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

export default function UserDetail({ params }: { params: Promise<{ id: string }> }) {
    const [data, setData] = useState<any>({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const router = useRouter();
    const { id } = use(params);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const res = await axios.post(`${API_URL}/execute`, {
                    table: "users",
                    filters: [{ column: "id", operator: "eq", value: parseInt(id) }]
                });
                if (res.data && res.data.length > 0) {
                    setData(res.data[0]);
                } else {
                    setError("User not found");
                }
            } catch (err) {
                console.error("Error fetching user:", err);
                setError("Failed to fetch user data");
            } finally {
                setLoading(false);
            }
        };

        if (id) fetchData();
    }, [id]);

    const handleChange = (key: string, value: any) => {
        setData((prev: any) => ({ ...prev, [key]: value }));
    };

    const handleSave = async () => {
        setSaving(true);
        setError(null);
        try {
            // Prepare data for update (exclude id)
            const { id: _, ...updateData } = data;

            await axios.post(`${API_URL}/mutate`, {
                table: "users",
                operation: "update",
                data: updateData,
                filters: [{ column: "id", operator: "eq", value: parseInt(id) }]
            });

            router.push('/');
        } catch (err) {
            console.error("Error saving:", err);
            setError("Failed to save changes");
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!confirm("Are you sure you want to delete this user?")) return;

        setSaving(true);
        try {
            await axios.post(`${API_URL}/mutate`, {
                table: "users",
                operation: "delete",
                filters: [{ column: "id", operator: "eq", value: parseInt(id) }]
            });

            router.push('/');
        } catch (err) {
            console.error("Error deleting:", err);
            setError("Failed to delete user");
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <ThemeProvider theme={darkTheme}>
                <CssBaseline />
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
                    <CircularProgress />
                </Box>
            </ThemeProvider>
        );
    }

    return (
        <ThemeProvider theme={darkTheme}>
            <CssBaseline />
            <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
                <Paper sx={{ p: 4, borderRadius: 2, boxShadow: 3 }}>
                    <Typography variant="h4" gutterBottom sx={{ mb: 4, color: 'primary.main' }}>
                        Edit User
                    </Typography>

                    {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

                    <Grid container spacing={3}>
                        {Object.keys(data).map((key) => (
                            <Grid size={{ xs: 12, sm: 6 }} key={key}>
                                <TextField
                                    fullWidth
                                    label={key.charAt(0).toUpperCase() + key.slice(1)}
                                    value={data[key]}
                                    onChange={(e) => handleChange(key, e.target.value)}
                                    disabled={key === 'id'}
                                    type={typeof data[key] === 'number' ? 'number' : 'text'}
                                    variant="outlined"
                                    InputLabelProps={{ shrink: true }}
                                />
                            </Grid>
                        ))}
                    </Grid>

                    <Box sx={{ mt: 4, display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
                        <Button variant="outlined" onClick={() => router.push('/')}>
                            Cancel
                        </Button>
                        <Button
                            variant="contained"
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
