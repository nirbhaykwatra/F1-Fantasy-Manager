// app/api/admin/results/recalculate/route.ts
// API endpoint to recalculate scores from existing race results

import { NextRequest, NextResponse } from 'next/server';
import pool from '@/services/db';
import scoringService from '@/services/scoring';

interface RecalculateRequest {
    grand_prix_id: number;
    league_id: number;
}

export async function POST(request: NextRequest) {
    try {
        const body: RecalculateRequest = await request.json();
        const { grand_prix_id, league_id } = body;

        if (!grand_prix_id || !league_id) {
            return NextResponse.json(
                { error: 'Missing required fields: grand_prix_id and league_id' },
                { status: 400 } as ResponseInit
            );
        }

        const client = await pool.connect();

        try {
            await client.query('BEGIN');

            // Check if race results exist for this GP
            const resultsCheck = await client.query(
                'SELECT COUNT(*) as count FROM race_results WHERE grand_prix_id = $1',
                [grand_prix_id]
            );

            if (parseInt(resultsCheck.rows[0].count) === 0) {
                await client.query('ROLLBACK');
                return NextResponse.json(
                    { error: 'No race results found for this Grand Prix. Please submit results first.' },
                    { status: 400 } as ResponseInit
                );
            }

            // Use the existing scoring service to recalculate points
            // This will use the race_results table data
            await scoringService.calculatePointsForGrandPrix(grand_prix_id, league_id, client);

            await client.query('COMMIT');

            return NextResponse.json({
                success: true,
                message: 'Scores recalculated successfully from existing race results'
            });
        } catch (error) {
            await client.query('ROLLBACK');
            throw error;
        } finally {
            client.release();
        }
    } catch (error) {
        console.error('Error recalculating scores:', error);
        return NextResponse.json(
            {
                error: 'Failed to recalculate scores',
                details: error instanceof Error ? error.message : 'Unknown error'
            },
            { status: 500 } as ResponseInit
        );
    }
}