// app/api/admin/results/route.ts
// API endpoint to submit race results and calculate points

import { NextRequest, NextResponse } from 'next/server';
import pool from '@/lib/db';
import scoringService from '@/lib/scoring';

interface ResultEntry {
    driver_id: number;
    position: number;
}

interface SessionPayload {
    session_type: 'qualifying' | 'race' | 'sprint' | 'sprint_qualifying';
    results: ResultEntry[];
}

interface SubmitResultsRequest {
    grand_prix_id: number;
    league_id: number;
    sessions: SessionPayload[];
}

export async function POST(request: NextRequest) {
    try {
        const body: SubmitResultsRequest = await request.json();
        const { grand_prix_id, league_id, sessions } = body;

        if (!grand_prix_id || !league_id || !sessions || sessions.length === 0) {
            return NextResponse.json(
                { error: 'Missing required fields' },
                { status: 400 } as ResponseInit
            );
        }

        const client = await pool.connect();

        try {
            await client.query('BEGIN');

            // Insert/update results for every submitted session in a single transaction
            for (const { session_type, results } of sessions) {
                for (const result of results) {
                    await client.query(
                        `INSERT INTO race_results (grand_prix_id, session_type, driver_id, position)
                         VALUES ($1, $2, $3, $4)
                         ON CONFLICT (grand_prix_id, session_type, driver_id)
                         DO UPDATE SET position = $4`,
                        [grand_prix_id, session_type, result.driver_id, result.position]
                    );
                }
            }

            await client.query('COMMIT');

            // Calculate points once all sessions are stored
            await scoringService.calculatePointsForGrandPrix(grand_prix_id, league_id);

            return NextResponse.json({
                success: true,
                message: 'Results submitted and points calculated successfully'
            });
        } catch (error) {
            await client.query('ROLLBACK');
            throw error;
        } finally {
            client.release();
        }
    } catch (error) {
        console.error('Error submitting results:', error);
        return NextResponse.json(
            { error: 'Failed to submit results' },
            { status: 500 } as ResponseInit
        );
    }
}

// GET endpoint - fetch existing results for a GP
export async function GET(request: NextRequest) {
    try {
        const { searchParams } = new URL(request.url);
        const grandPrixId = searchParams.get('grand_prix_id');
        const sessionType = searchParams.get('session_type');

        if (!grandPrixId) {
            return NextResponse.json(
                { error: 'Missing grand_prix_id parameter' },
                { status: 400 } as ResponseInit
            );
        }

        let query = `
            SELECT
                rr.id,
                rr.driver_id,
                rr.position,
                rr.session_type,
                d.first_name,
                d.last_name,
                d.code,
                c.short_name as constructor
            FROM race_results rr
                     JOIN drivers d ON d.id = rr.driver_id
                     JOIN constructors c ON c.id = d.constructor_id
            WHERE rr.grand_prix_id = $1
        `;

        const params: any[] = [grandPrixId];

        if (sessionType) {
            query += ' AND rr.session_type = $2';
            params.push(sessionType);
        }

        query += ' ORDER BY rr.session_type, rr.position';

        const result = await pool.query(query, params);

        return NextResponse.json({
            success: true,
            results: result.rows
        });
    } catch (error) {
        console.error('Error fetching results:', error);
        return NextResponse.json(
            { error: 'Failed to fetch results' },
            { status: 500 } as ResponseInit
        );
    }
}