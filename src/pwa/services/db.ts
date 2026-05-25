// services/db.ts
// This file sets up the connection to your PostgreSQL database using the 'pg' library
import { Pool } from 'pg';

// Create a connection pool - this allows multiple database queries to happen efficiently
// The Pool reuses connections instead of creating new ones each time
const pool = new Pool({
    connectionString: process.env.DATABASE_URL, // Your database connection string from .env file
    ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false,
});

// Export the pool so other files can use it to query the database
export default pool;