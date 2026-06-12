
// app/admin/results/page.tsx
// Admin interface for entering race results

'use client';

import { useState, useEffect } from 'react';

// TypeScript interfaces for our data
interface Driver {
    id: number;
    code: string;
    number: number;
    first_name: string;
    last_name: string;
    constructor: string;
    color_hex: string;
}

interface GrandPrix {
    id: number;
    round_number: number;
    event_name: string;
    event_format: string;
    is_completed: boolean;
}

interface ResultEntry {
    position: number;
    driver_id: number | null;
}

// Results keyed by session type
type SessionResults = Record<string, ResultEntry[]>;

const SESSION_TYPES = ['race', 'qualifying', 'sprint', 'sprint_qualifying'] as const;
type SessionType = typeof SESSION_TYPES[number];

function createEmptyResults(): ResultEntry[] {
    return Array.from({ length: 22 }, (_, i) => ({ position: i + 1, driver_id: null }));
}

export default function AdminResultsPage() {
    const [seasonId] = useState(1);
    const [leagueId] = useState(1);
    const [grandsPrix, setGrandsPrix] = useState<GrandPrix[]>([]);
    const [drivers, setDrivers] = useState<Driver[]>([]);
    const [selectedGP, setSelectedGP] = useState<number | null>(null);
    // Which sessions are enabled
    const [enabledSessions, setEnabledSessions] = useState<Record<SessionType, boolean>>({
        race: true,
        qualifying: true,
        sprint: false,
        sprint_qualifying: false,
    });
    // Active tab for display
    const [activeTab, setActiveTab] = useState<SessionType>('race');
    // Results per session
    const [sessionResults, setSessionResults] = useState<SessionResults>({
        race: createEmptyResults(),
        qualifying: createEmptyResults(),
        sprint: createEmptyResults(),
        sprint_qualifying: createEmptyResults(),
    });
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

    useEffect(() => {
        fetchGrandsPrix();
        fetchDrivers();
    }, []);

    const fetchGrandsPrix = async () => {
        try {
            const response = await fetch(`/api/admin/grands-prix?season_id=${seasonId}`);
            const data = await response.json();
            if (data.success) setGrandsPrix(data.grands_prix);
        } catch (error) {
            console.error('Error fetching GPs:', error);
            setMessage({ type: 'error', text: 'Failed to load Grand Prix events' });
        }
    };

    const fetchDrivers = async () => {
        try {
            const response = await fetch(`/api/admin/drivers?season_id=${seasonId}`);
            const data = await response.json();
            if (data.success) setDrivers(data.drivers);
        } catch (error) {
            console.error('Error fetching drivers:', error);
            setMessage({ type: 'error', text: 'Failed to load drivers' });
        }
    };

    const toggleSession = (session: SessionType) => {
        setEnabledSessions(prev => ({ ...prev, [session]: !prev[session] }));
        // If enabling, switch to that tab
        if (!enabledSessions[session]) setActiveTab(session);
    };

    const assignDriverToPosition = (session: SessionType, position: number, driverId: number | null) => {
        setSessionResults(prev => ({
            ...prev,
            [session]: prev[session].map(r =>
                r.position === position ? { ...r, driver_id: driverId } : r
            ),
        }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!selectedGP) {
            setMessage({ type: 'error', text: 'Please select a Grand Prix' });
            return;
        }

        const activeSessions = SESSION_TYPES.filter(s => enabledSessions[s]);
        if (activeSessions.length === 0) {
            setMessage({ type: 'error', text: 'Please enable at least one session' });
            return;
        }

        setLoading(true);
        setMessage(null);

        try {
            const sessions = activeSessions.map(session => ({
                session_type: session,
                results: sessionResults[session].filter(r => r.driver_id !== null),
            }));

            const response = await fetch('/api/admin/results', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    grand_prix_id: selectedGP,
                    league_id: leagueId,
                    sessions,
                }),
            });

            const data = await response.json();

            if (data.success) {
                setMessage({ type: 'success', text: 'Results submitted and points calculated!' });
            } else {
                setMessage({ type: 'error', text: data.error || 'Failed to submit results' });
            }
        } catch (error) {
            console.error('Error submitting results:', error);
            setMessage({ type: 'error', text: 'An error occurred while submitting results' });
        } finally {
            setLoading(false);
        }
    };

    const handleRecalculate = async () => {
        if (!selectedGP) {
            setMessage({ type: 'error', text: 'Please select a Grand Prix to recalculate' });
            return;
        }

        setLoading(true);
        setMessage(null);

        try {
            const response = await fetch('/api/admin/results/recalculate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    grand_prix_id: selectedGP,
                    league_id: leagueId,
                }),
            });

            const data = await response.json();

            if (data.success) {
                setMessage({ type: 'success', text: 'Scores recalculated successfully from existing race results!' });
            } else {
                setMessage({ type: 'error', text: data.error || 'Failed to recalculate scores' });
            }
        } catch (error) {
            console.error('Error recalculating scores:', error);
            setMessage({ type: 'error', text: 'An error occurred while recalculating scores' });
        } finally {
            setLoading(false);
        }
    };

    const handleLoadExisting = async () => {
        if (!selectedGP) {
            setMessage({ type: 'error', text: 'Please select a Grand Prix to load results for' });
            return;
        }

        setLoading(true);
        setMessage(null);

        try {
            const response = await fetch(`/api/admin/results?grand_prix_id=${selectedGP}`);
            const data = await response.json();

            if (!data.success || !data.results || data.results.length === 0) {
                setMessage({ type: 'error', text: 'No existing results found for this Grand Prix' });
                return;
            }

            // Group results by session type
            const bySession: Record<string, { position: number; driver_id: number }[]> = {};
            for (const row of data.results) {
                if (!bySession[row.session_type]) bySession[row.session_type] = [];
                bySession[row.session_type].push({ position: row.position, driver_id: row.driver_id });
            }

            // Enable the sessions that have results and populate the grids
            const newEnabled = { ...enabledSessions };
            const newResults = { ...sessionResults };

            for (const session of SESSION_TYPES) {
                if (bySession[session]) {
                    newEnabled[session] = true;
                    const empty = createEmptyResults();
                    for (const entry of bySession[session]) {
                        const idx = empty.findIndex(r => r.position === entry.position);
                        if (idx !== -1) empty[idx] = { position: entry.position, driver_id: entry.driver_id };
                    }
                    newResults[session] = empty;
                }
            }

            setEnabledSessions(newEnabled);
            setSessionResults(newResults);

            const sessionNames = Object.keys(bySession).map(s => s.replace('_', ' ')).join(', ');
            setMessage({ type: 'success', text: `Loaded existing results for: ${sessionNames}` });
        } catch (error) {
            console.error('Error loading existing results:', error);
            setMessage({ type: 'error', text: 'An error occurred while loading existing results' });
        } finally {
            setLoading(false);
        }
    };

    const activeSessionList = SESSION_TYPES.filter(s => enabledSessions[s]);

    return (
        <div className="min-h-screen bg-gray-50 p-8">
            <div className="max-w-6xl mx-auto">
                <h1 className="text-4xl font-bold mb-8 text-gray-900">
                    🏁 Admin: Enter Race Results
                </h1>

                {message && (
                    <div
                        className={`mb-6 p-4 rounded-lg ${
                            message.type === 'success'
                                ? 'bg-green-100 text-green-800'
                                : 'bg-red-100 text-red-800'
                        }`}
                    >
                        {message.text}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-md p-6">
                    {/* Grand Prix Selection */}
                    <div className="mb-6">
                        <label className="block text-sm font-medium text-gray-900 mb-2">
                            Select Grand Prix
                        </label>
                        <select
                            value={selectedGP || ''}
                            onChange={(e) => setSelectedGP(Number(e.target.value))}
                            className="w-full px-4 py-2 border border-gray-300 text-gray-900 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                            required
                        >
                            <option value="">Choose a Grand Prix...</option>
                            {grandsPrix.map((gp) => (
                                <option key={gp.id} value={gp.id}>
                                    Round {gp.round_number}: {gp.event_name}
                                    {gp.is_completed ? ' ✓' : ''}
                                </option>
                            ))}
                        </select>
                        <div className="mt-3">
                            <button
                                type="button"
                                onClick={handleLoadExisting}
                                disabled={loading || !selectedGP}
                                className={`px-4 py-2 rounded-lg font-medium text-white text-sm transition-colors ${
                                    loading || !selectedGP
                                        ? 'bg-gray-400 cursor-not-allowed'
                                        : 'bg-amber-600 hover:bg-amber-700'
                                }`}
                            >
                                {loading ? 'Loading...' : '📥 Load Existing Results'}
                            </button>
                            <span className="ml-3 text-xs text-gray-500">
                                    Populate the grid from results already stored in the database
                                </span>
                        </div>
                    </div>

                    {/* Session Toggles */}
                    <div className="mb-6">
                        <label className="block text-sm font-medium text-gray-900 mb-2">
                            Sessions to Submit
                        </label>
                        <div className="flex flex-wrap gap-3">
                            {SESSION_TYPES.map((type) => (
                                <label key={type} className="inline-flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={enabledSessions[type]}
                                        onChange={() => toggleSession(type)}
                                        className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
                                    />
                                    <span className="capitalize text-gray-900">
                                        {type.replace('_', ' ')}
                                    </span>
                                </label>
                            ))}
                        </div>
                    </div>

                    {/* Session Tabs + Results Grid */}
                    {activeSessionList.length > 0 ? (
                        <div className="mb-6">
                            {/* Tab bar */}
                            <div className="flex border-b border-gray-200 mb-4">
                                {activeSessionList.map((session) => (
                                    <button
                                        key={session}
                                        type="button"
                                        onClick={() => setActiveTab(session)}
                                        className={`px-5 py-2 text-sm font-medium capitalize transition-colors ${
                                            activeTab === session
                                                ? 'border-b-2 border-red-600 text-red-600'
                                                : 'text-gray-500 hover:text-gray-800'
                                        }`}
                                    >
                                        {session.replace('_', ' ')}
                                    </button>
                                ))}
                            </div>

                            {/* Active tab results grid */}
                            {activeSessionList.includes(activeTab) && (
                                <div>
                                    <h2 className="text-lg font-semibold mb-4 text-gray-900 capitalize">
                                        {activeTab.replace('_', ' ')} — Assign Drivers to Finishing Positions
                                    </h2>
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                        {sessionResults[activeTab].map((result) => (
                                            <div
                                                key={result.position}
                                                className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:border-gray-300"
                                            >
                                                <div className="flex items-center justify-center w-10 h-10 bg-gray-900 text-white font-bold rounded">
                                                    P{result.position}
                                                </div>
                                                <select
                                                    value={result.driver_id || ''}
                                                    onChange={(e) => assignDriverToPosition(
                                                        activeTab,
                                                        result.position,
                                                        e.target.value ? Number(e.target.value) : null
                                                    )}
                                                    className="flex-1 px-3 py-2 text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                                                >
                                                    <option value="">Select driver...</option>
                                                    {drivers.map((driver) => (
                                                        <option
                                                            key={driver.id}
                                                            value={driver.id}
                                                            disabled={sessionResults[activeTab].some(
                                                                r => r.driver_id === driver.id && r.position !== result.position
                                                            )}
                                                        >
                                                            {driver.first_name} {driver.last_name} (#{driver.number})
                                                        </option>
                                                    ))}
                                                </select>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    ) : (
                        <p className="mb-6 text-gray-500 italic">
                            Enable at least one session above to enter results.
                        </p>
                    )}

                    {/* Submit Button */}
                    <div className="flex justify-end">
                        <button
                            type="submit"
                            disabled={loading || !selectedGP || activeSessionList.length === 0}
                            className={`px-6 py-3 rounded-lg font-semibold text-white transition-colors ${
                                loading || !selectedGP || activeSessionList.length === 0
                                    ? 'bg-gray-400 cursor-not-allowed'
                                    : 'bg-red-600 hover:bg-red-700'
                            }`}
                        >
                            {loading
                                ? 'Processing...'
                                : `Submit ${activeSessionList.length} Session${activeSessionList.length > 1 ? 's' : ''} & Calculate Points`}
                        </button>
                    </div>
                </form>

                {/* Recalculate Button - Separate from form */}
                <div className="mt-6 bg-white rounded-lg shadow-md p-6">
                    <h2 className="text-xl font-semibold mb-4 text-gray-900">
                        🔄 Recalculate Scores
                    </h2>
                    <p className="text-gray-700 mb-4">
                        Use this to recalculate player scores from existing race results in the database.
                        This is useful if scoring rules have changed or if you need to fix calculation errors.
                    </p>
                    <button
                        type="button"
                        onClick={handleRecalculate}
                        disabled={loading || !selectedGP}
                        className={`px-6 py-3 rounded-lg font-semibold text-white transition-colors ${
                            loading || !selectedGP
                                ? 'bg-gray-400 cursor-not-allowed'
                                : 'bg-blue-600 hover:bg-blue-700'
                        }`}
                    >
                        {loading ? 'Recalculating...' : 'Recalculate Scores for Selected GP'}
                    </button>
                </div>

                {/* Info Box */}
                <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
                    <h3 className="font-semibold text-blue-900 mb-2">
                        📝 How It Works
                    </h3>
                    <ul className="list-disc list-inside space-y-1 text-blue-800 text-sm">
                        <li>Select the Grand Prix, then tick the sessions you want to submit</li>
                        <li>Use the tabs to enter finishing positions for each session</li>
                        <li>Click Submit to store all session results and calculate player points in one go</li>
                        <li>Points are automatically calculated across all submitted sessions</li>
                        <li>Driver exhaustion status is updated for the next round</li>
                    </ul>
                </div>
            </div>
        </div>
    );
}