// app/api/admin/grands-prix/route.ts
// API endpoint to fetch Grand Prix events

import { NextRequest, NextResponse } from 'next/server';
import pool from '@/services/db';

// GET endpoint - fetch all GPs for a season
export async function GET(request: NextRequest) {
    try {
        const { searchParams } = new URL(request.url);
        const seasonId = searchParams.get('season_id');

        if (!seasonId) {
            return NextResponse.json(
                { error: 'Missing season_id parameter' },
                { status: 400 }
            );
        }

        const query = `
      SELECT 
        id,
        round_number,
        event_name,
        circuit_key,
        event_format,
        race_date_utc,
        is_completed
      FROM grands_prix
      WHERE season_id = $1
      ORDER BY round_number
    `;

        const result = await pool.query(query, [seasonId]);

        return NextResponse.json({
            success: true,
            grands_prix: result.rows
        });
    } catch (error) {
        console.error('Error fetching grands prix:', error);
        return NextResponse.json(
            { error: 'Failed to fetch grands prix' },
            { status: 500 }
        );
    }
}