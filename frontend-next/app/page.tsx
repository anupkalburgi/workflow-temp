"use client";

import React, { useEffect, useState } from 'react';
import { Container, Typography, Box, Button, Paper, CircularProgress, Grid, Card, CardContent, CardActionArea } from '@mui/material';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import StorageIcon from '@mui/icons-material/Storage';
import { prettifyTableName, type SchemaMap } from '@/lib/schemaUtils';

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

interface TableStat {
  name: string;
  count: number;
}

export default function Dashboard() {
  const [schema, setSchema] = useState<SchemaMap>({});
  const [tableStats, setTableStats] = useState<TableStat[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch enhanced schema
        const schemaRes = await axios.get(`${API_URL}/schema/enhanced`);
        setSchema(schemaRes.data);

        // For each table, fetch count
        const tableNames = Object.keys(schemaRes.data);
        const stats: TableStat[] = [];

        for (const tableName of tableNames) {
          try {
            const countRes = await axios.post(`${API_URL}/execute`, {
              table: tableName,
              aggregations: [{ function: "count", column: "id", alias: "count" }]
            });
            stats.push({
              name: tableName,
              count: countRes.data[0]?.count || 0
            });
          } catch (error) {
            console.error(`Error fetching count for ${tableName}:`, error);
            stats.push({ name: tableName, count: 0 });
          }
        }

        setTableStats(stats);
      } catch (error) {
        console.error("Error fetching dashboard data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
          <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
            Dynamic SQL Dashboard
          </Typography>
        </Box>

        <Typography variant="body1" sx={{ mb: 4, color: 'text.secondary' }}>
          Select a table to view and manage its data
        </Typography>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Grid container spacing={3}>
            {tableStats.map((stat) => (
              <Grid item xs={12} sm={6} md={4} key={stat.name}>
                <Card
                  sx={{
                    height: '100%',
                    borderRadius: 2,
                    boxShadow: 3,
                    transition: 'transform 0.2s, box-shadow 0.2s',
                    '&:hover': {
                      transform: 'scale(1.03)',
                      boxShadow: 6
                    }
                  }}
                >
                  <CardActionArea
                    onClick={() => router.push(`/tables/${stat.name}`)}
                    sx={{ height: '100%', p: 2 }}
                  >
                    <CardContent sx={{ textAlign: 'center' }}>
                      <StorageIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
                      <Typography variant="h5" component="div" gutterBottom>
                        {prettifyTableName(stat.name)}
                      </Typography>
                      <Typography variant="h3" color="text.secondary" sx={{ fontWeight: 'bold', mb: 1 }}>
                        {stat.count.toLocaleString()}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Records
                      </Typography>
                    </CardContent>
                  </CardActionArea>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </Container>
    </ThemeProvider>
  );
}
