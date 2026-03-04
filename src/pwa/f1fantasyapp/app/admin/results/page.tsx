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

export default function AdminResultsPage() {
    // React state variables - these hold the component's data
    const [seasonId] = useState(1); // Hardcoded for now - you can make this dynamic
    const [leagueId] = useState(1); // Hardcoded for now
    const [grandsPrix, setGrandsPrix] = useState<GrandPrix[]>([]);
    const [drivers, setDrivers] = useState<Driver[]>([]);
    const [selectedGP, setSelectedGP] = useState<number | null>(null);
    const [sessionType, setSessionType] = useState<string>('race');
    const [results, setResults] = useState<ResultEntry[]>([]);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

    // useEffect runs when the component first loads
    useEffect(() => {
        fetchGrandsPrix();
        fetchDrivers();
    }, []);

    // Fetch the list of Grand Prix events
    const fetchGrandsPrix = async () => {
        try {
            const response = await fetch(`/api/admin/grands-prix?season_id=${seasonId}`);
            const data = await response.json();

            if (data.success) {
                setGrandsPrix(data.grands_prix);
            }
        } catch (error) {
            console.error('Error fetching GPs:', error);
            setMessage({ type: 'error', text: 'Failed to load Grand Prix events' });
        }
    };

    // Fetch the list of drivers
    const fetchDrivers = async () => {
        try {
            const response = await fetch(`/api/admin/drivers?season_id=${seasonId}`);
            const data = await response.json();

            if (data.success) {
                setDrivers(data.drivers);
                // Initialize results with 22 positions, no drivers assigned yet
                setResults(Array.from({ length: 22 }, (_, i) => ({
                    position: i + 1,
                    driver_id: null
                })));
            }
        } catch (error) {
            console.error('Error fetching drivers:', error);
            setMessage({ type: 'error', text: 'Failed to load drivers' });
        }
    };

    // Assign a driver to a specific position
    const assignDriverToPosition = (position: number, driverId: number | null) => {
        setResults(prev =>
            prev.map(r =>
                r.position === position ? { ...r, driver_id: driverId } : r
            )
        );
    };

    // Submit the results to the API
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault(); // Prevent page reload

        if (!selectedGP) {
            setMessage({ type: 'error', text: 'Please select a Grand Prix' });
            return;
        }

        setLoading(true);
        setMessage(null);

        try {
            const response = await fetch('/api/admin/results', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    grand_prix_id: selectedGP,
                    league_id: leagueId,
                    session_type: sessionType,
                    results: results.filter(r => r.position > 0) // Only send drivers with positions
                })
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

    return (
        <div className="min-h-screen bg-gray-50 p-8">
            <div className="max-w-6xl mx-auto">
                <h1 className="text-4xl font-bold mb-8 text-gray-900">
                    🏁 Admin: Enter Race Results
                </h1>

                {/* Message banner */}
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
                    </div>

                    {/* Session Type Selection */}
                    <div className="mb-6">
                        <label className="block text-sm font-medium text-gray-900 mb-2">
                            Session Type
                        </label>
                        <div className="flex gap-4">
                            {['race', 'qualifying', 'sprint', 'sprint_qualifying'].map((type) => (
                                <label key={type} className="inline-flex items-center">
                                    <input
                                        type="radio"
                                        name="sessionType"
                                        value={type}
                                        checked={sessionType === type}
                                        onChange={(e) => setSessionType(e.target.value)}
                                        className="form-radio text-red-600"
                                    />
                                    <span className="ml-2 capitalize text-gray-900">
                    {type.replace('_', ' ')}
                  </span>
                                </label>
                            ))}
                        </div>
                    </div>

                    {/* Results Entry Grid */}
                    <div className="mb-6">
                        <h2 className="text-lg font-semibold mb-4 text-gray-900">
                            Assign Drivers to Finishing Positions
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {results.map((result) => (
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
                                                disabled={results.some(r => r.driver_id === driver.id && r.position !== result.position)}
                                            >
                                                {driver.first_name} {driver.last_name} (#{driver.number})
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Submit Button */}
                    <div className="flex justify-end">
                        <button
                            type="submit"
                            disabled={loading || !selectedGP}
                            className={`px-6 py-3 rounded-lg font-semibold text-white transition-colors ${
                                loading || !selectedGP
                                    ? 'bg-gray-400 cursor-not-allowed'
                                    : 'bg-red-600 hover:bg-red-700'
                            }`}
                        >
                            {loading ? 'Processing...' : 'Submit Results & Calculate Points'}
                        </button>
                    </div>
                </form>

                {/* Info Box */}
                <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
                    <h3 className="font-semibold text-blue-900 mb-2">
                        📝 How It Works
                    </h3>
                    <ul className="list-disc list-inside space-y-1 text-blue-800 text-sm">
                        <li>Select the Grand Prix and session type</li>
                        <li>Enter the finishing position for each driver</li>
                        <li>Click Submit to store results and calculate player points</li>
                        <li>Points are automatically calculated based on scoring rules</li>
                        <li>Driver exhaustion status is updated for the next round</li>
                    </ul>
                </div>
            </div>
        </div>
    );
}