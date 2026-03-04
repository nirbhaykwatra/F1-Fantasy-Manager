// app/api/admin/drivers/route.ts
// API endpoint to fetch drivers for a season

import { NextRequest, NextResponse } from 'next/server';
import pool from '@/lib/db';

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
        d.id,
        d.code,
        d.number,
        d.first_name,
        d.last_name,
        c.short_name as constructor,
        c.color_hex
      FROM drivers d
      JOIN constructors c ON c.id = d.constructor_id
      WHERE d.season_id = $1 AND d.is_active = TRUE
      ORDER BY c.short_name, d.last_name
    `;

        const result = await pool.query(query, [seasonId]);

        return NextResponse.json({
            success: true,
            drivers: result.rows
        });
    } catch (error) {
        console.error('Error fetching drivers:', error);
        return NextResponse.json(
            { error: 'Failed to fetch drivers' },
            { status: 500 }
        );
    }
}