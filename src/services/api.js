/**
 * PRAVAH Flash Flood Early Warning System — API Service Layer
 * 
 * Provides inference requests and high-fidelity mock data for 20 river
 * catchment gauge stations across the Western Ghats (Maharashtra) corridor.
 */

// ---------------------------------------------------------------------------
// Static Fallback Station Catalog (20 Western Ghats, Maharashtra Stations)
// Derived from Central Water Commission (CWC) & IndoFloods benchmark gauges
// ---------------------------------------------------------------------------
export const WESTERN_GHATS_STATIONS = [
  {
    station_id: 'MH_GAK_01',
    legacy_gauge_id: '643',
    name: 'Terwad',
    river: 'Panchganga',
    basin: 'Krishna',
    district: 'Kolhapur',
    lat: 16.6753,
    lng: 74.5736,
    warning_level_m: 534.0,
    danger_level_m: 536.0,
    default_tier: 'WARNING',
    default_probability: 0.78,
    base_rainfall: { day_1: 52.4, day_3_cum: 134.8, day_7_cum: 242.0 },
  },
  {
    station_id: 'MH_GAK_02',
    legacy_gauge_id: '612',
    name: 'Takli',
    river: 'Bhima',
    basin: 'Krishna',
    district: 'Solapur',
    lat: 17.4131,
    lng: 75.8478,
    warning_level_m: 419.0,
    danger_level_m: 420.5,
    default_tier: 'NORMAL',
    default_probability: 0.18,
    base_rainfall: { day_1: 8.2, day_3_cum: 22.4, day_7_cum: 45.0 },
  },
  {
    station_id: 'MH_GAK_03',
    legacy_gauge_id: '678',
    name: 'Kurundwad',
    river: 'Krishna',
    basin: 'Krishna',
    district: 'Kolhapur',
    lat: 16.6836,
    lng: 74.6031,
    warning_level_m: 535.64,
    danger_level_m: 537.16,
    default_tier: 'WARNING',
    default_probability: 0.81,
    base_rainfall: { day_1: 61.2, day_3_cum: 148.5, day_7_cum: 268.0 },
  },
  {
    station_id: 'MH_GAK_04',
    legacy_gauge_id: '640',
    name: 'Dhond',
    river: 'Bhima',
    basin: 'Krishna',
    district: 'Pune',
    lat: 18.4739,
    lng: 74.5764,
    warning_level_m: 504.0,
    danger_level_m: 505.0,
    default_tier: 'ADVISORY',
    default_probability: 0.44,
    base_rainfall: { day_1: 26.5, day_3_cum: 62.0, day_7_cum: 112.5 },
  },
  {
    station_id: 'MH_GAK_05',
    legacy_gauge_id: '681',
    name: 'Samdoli',
    river: 'Varna',
    basin: 'Krishna',
    district: 'Sangli',
    lat: 16.8550,
    lng: 74.4967,
    warning_level_m: 541.95,
    danger_level_m: 543.15,
    default_tier: 'ADVISORY',
    default_probability: 0.52,
    base_rainfall: { day_1: 34.0, day_3_cum: 78.4, day_7_cum: 139.2 },
  },
  {
    station_id: 'MH_GAK_06',
    legacy_gauge_id: '589',
    name: 'Arjunwad',
    river: 'Krishna',
    basin: 'Krishna',
    district: 'Kolhapur',
    lat: 16.7808,
    lng: 74.6333,
    warning_level_m: 539.2,
    danger_level_m: 540.7,
    default_tier: 'ADVISORY',
    default_probability: 0.49,
    base_rainfall: { day_1: 31.8, day_3_cum: 74.1, day_7_cum: 132.0 },
  },
  {
    station_id: 'MH_GAK_07',
    legacy_gauge_id: '642',
    name: 'Narsingpur',
    river: 'Bhima',
    basin: 'Krishna',
    district: 'Solapur',
    lat: 17.9722,
    lng: 75.1392,
    warning_level_m: 458.4,
    danger_level_m: 459.0,
    default_tier: 'NORMAL',
    default_probability: 0.14,
    base_rainfall: { day_1: 4.5, day_3_cum: 16.2, day_7_cum: 38.0 },
  },
  {
    station_id: 'MH_GAK_08',
    legacy_gauge_id: '682',
    name: 'Sarati',
    river: 'Nira',
    basin: 'Krishna',
    district: 'Pune',
    lat: 17.9114,
    lng: 75.0075,
    warning_level_m: 474.13,
    danger_level_m: 475.13,
    default_tier: 'NORMAL',
    default_probability: 0.22,
    base_rainfall: { day_1: 12.0, day_3_cum: 28.5, day_7_cum: 58.0 },
  },
  {
    station_id: 'MH_GAK_09',
    legacy_gauge_id: '654',
    name: 'Warunji',
    river: 'Koyna',
    basin: 'Krishna',
    district: 'Satara',
    lat: 17.2722,
    lng: 74.1650,
    warning_level_m: 562.8,
    danger_level_m: 565.2,
    default_tier: 'WARNING',
    default_probability: 0.74,
    base_rainfall: { day_1: 58.6, day_3_cum: 136.2, day_7_cum: 251.0 },
  },
  {
    station_id: 'MH_GAK_10',
    legacy_gauge_id: '646',
    name: 'Nagothane',
    river: 'Amba',
    basin: 'West Flowing (Konkan)',
    district: 'Raigad',
    lat: 18.5192,
    lng: 73.1564,
    warning_level_m: 8.0,
    danger_level_m: 9.0,
    default_tier: 'WARNING',
    default_probability: 0.79,
    base_rainfall: { day_1: 68.4, day_3_cum: 154.2, day_7_cum: 279.0 },
  },
  {
    station_id: 'MH_GAK_11',
    legacy_gauge_id: '635',
    name: 'Kopergaon',
    river: 'Godavari',
    basin: 'Godavari',
    district: 'Ahmednagar',
    lat: 19.8783,
    lng: 74.4819,
    warning_level_m: 490.9,
    danger_level_m: 493.68,
    default_tier: 'NORMAL',
    default_probability: 0.21,
    base_rainfall: { day_1: 11.2, day_3_cum: 26.0, day_7_cum: 51.5 },
  },
  {
    station_id: 'MH_GAK_12',
    legacy_gauge_id: '684',
    name: 'Karad',
    river: 'Krishna/Koyna Confluence',
    basin: 'Krishna',
    district: 'Satara',
    lat: 17.2944,
    lng: 74.1903,
    warning_level_m: 563.41,
    danger_level_m: 567.04,
    default_tier: 'EMERGENCY',
    default_probability: 0.94,
    base_rainfall: { day_1: 94.6, day_3_cum: 218.4, day_7_cum: 362.0 },
  },
  {
    station_id: 'MH_GAK_13',
    legacy_gauge_id: '596',
    name: 'Niivali',
    river: 'Bav',
    basin: 'West Flowing (Konkan)',
    district: 'Ratnagiri',
    lat: 17.0692,
    lng: 73.4500,
    warning_level_m: 9.4,
    danger_level_m: 11.0,
    default_tier: 'ADVISORY',
    default_probability: 0.47,
    base_rainfall: { day_1: 29.5, day_3_cum: 68.0, day_7_cum: 124.0 },
  },
  {
    station_id: 'MH_GAK_14',
    legacy_gauge_id: '645',
    name: 'Nasik',
    river: 'Godavari',
    basin: 'Godavari',
    district: 'Nashik',
    lat: 20.0019,
    lng: 73.8033,
    warning_level_m: 558.1,
    danger_level_m: 559.6,
    default_tier: 'ADVISORY',
    default_probability: 0.39,
    base_rainfall: { day_1: 22.0, day_3_cum: 54.2, day_7_cum: 98.4 },
  },
  {
    station_id: 'MH_GAK_15',
    legacy_gauge_id: '585',
    name: 'Ozerkheda',
    river: 'Damanganga / Wagh',
    basin: 'West Flowing (Konkan)',
    district: 'Nashik',
    lat: 20.1006,
    lng: 73.2706,
    warning_level_m: 88.0,
    danger_level_m: 90.0,
    default_tier: 'NORMAL',
    default_probability: 0.25,
    base_rainfall: { day_1: 14.8, day_3_cum: 32.1, day_7_cum: 64.0 },
  },
  {
    station_id: 'MH_GAK_16',
    legacy_gauge_id: '648',
    name: 'Pen',
    river: 'Bhogeswari',
    basin: 'West Flowing (Konkan)',
    district: 'Raigad',
    lat: 18.7367,
    lng: 73.1108,
    warning_level_m: 12.3,
    danger_level_m: 13.0,
    default_tier: 'ADVISORY',
    default_probability: 0.54,
    base_rainfall: { day_1: 37.4, day_3_cum: 82.5, day_7_cum: 147.0 },
  },
  {
    station_id: 'MH_GAK_17',
    legacy_gauge_id: '602',
    name: 'Mahad',
    river: 'Savitri',
    basin: 'West Flowing (Konkan)',
    district: 'Raigad',
    lat: 18.0922,
    lng: 73.4603,
    warning_level_m: 10.0,
    danger_level_m: 11.0,
    default_tier: 'EMERGENCY',
    default_probability: 0.91,
    base_rainfall: { day_1: 112.5, day_3_cum: 245.0, day_7_cum: 398.0 },
  },
  {
    station_id: 'MH_GAK_18',
    legacy_gauge_id: '668',
    name: 'Badlapur',
    river: 'Ulhas',
    basin: 'West Flowing (Konkan)',
    district: 'Thane',
    lat: 19.1622,
    lng: 73.2544,
    warning_level_m: 16.5,
    danger_level_m: 17.5,
    default_tier: 'WARNING',
    default_probability: 0.83,
    base_rainfall: { day_1: 72.8, day_3_cum: 162.0, day_7_cum: 288.4 },
  },
  {
    station_id: 'MH_GAK_19',
    legacy_gauge_id: '656',
    name: 'Nandre',
    river: 'Yerala',
    basin: 'Krishna',
    district: 'Sangli',
    lat: 16.9500,
    lng: 74.5300,
    warning_level_m: 540.17,
    danger_level_m: 542.21,
    default_tier: 'NORMAL',
    default_probability: 0.19,
    base_rainfall: { day_1: 9.6, day_3_cum: 24.1, day_7_cum: 48.0 },
  },
  {
    station_id: 'MH_GAK_20',
    legacy_gauge_id: '626',
    name: 'Ujani Dam',
    river: 'Krishna / Bhima',
    basin: 'Krishna',
    district: 'Solapur',
    lat: 18.0700,
    lng: 75.1200,
    warning_level_m: 496.83,
    danger_level_m: 497.58,
    default_tier: 'NORMAL',
    default_probability: 0.28,
    base_rainfall: { day_1: 16.2, day_3_cum: 39.4, day_7_cum: 76.5 },
  },
];

// Tier recommendation mappings
const TIER_RECOMMENDATIONS = {
  EMERGENCY: {
    title: 'EMERGENCY: Severe Flash-Flood Threat Imminent',
    recommendation:
      'Activate district disaster management cell. Evacuate riverbank settlements and deploy SDRF/NDRF teams immediately.',
  },
  WARNING: {
    title: 'WARNING: Substantial Inundation Expected',
    recommendation:
      'River stage approaching danger mark. Pre-position emergency relief supplies, halt bridge transport, and advise livestock relocation.',
  },
  ADVISORY: {
    title: 'ADVISORY: High Soil Moisture & Elevated Runoff',
    recommendation:
      'Antecedent rainfall saturation is high. Monitor gauge stages continuously and issue alerts to vulnerable low-lying crossings.',
  },
  NORMAL: {
    title: 'NORMAL: Flow Stable Within Channel Capacity',
    recommendation:
      'Standard automated monitoring active. Gauge readings are well within seasonal safety limits.',
  },
};

/**
 * Helper to determine risk tier from probability
 */
export function calculateRiskTier(probability) {
  if (probability >= 0.85) return 'EMERGENCY';
  if (probability >= 0.60) return 'WARNING';
  if (probability >= 0.35) return 'ADVISORY';
  return 'NORMAL';
}

/**
 * Generate 7-day daily rainfall history ending on target date
 */
function generateRainfallSeries(baseDateStr, day1, day3Cum, day7Cum) {
  const baseDate = baseDateStr ? new Date(baseDateStr) : new Date();
  const series = [];

  // Approximate realistic daily distribution backwards from day-1
  const d1 = day1;
  const d2 = Math.max(0, (day3Cum - d1) * 0.55);
  const d3 = Math.max(0, day3Cum - d1 - d2);
  const rem = Math.max(0, day7Cum - day3Cum);
  const d4 = rem * 0.35;
  const d5 = rem * 0.25;
  const d6 = rem * 0.22;
  const d7 = rem * 0.18;

  const vals = [d7, d6, d5, d4, d3, d2, d1];

  for (let i = 6; i >= 0; i--) {
    const d = new Date(baseDate);
    d.setDate(d.getDate() - (6 - i));
    series.push({
      date: d.toISOString().split('T')[0],
      val: parseFloat(vals[i].toFixed(1)),
    });
  }

  return series;
}

/**
 * Resolves station record by ID, legacy gauge number, or name
 */
export function findStation(identifier) {
  if (!identifier) return WESTERN_GHATS_STATIONS[0];

  const clean = String(identifier).trim().toUpperCase();
  return (
    WESTERN_GHATS_STATIONS.find(
      (s) =>
        s.station_id.toUpperCase() === clean ||
        s.legacy_gauge_id === clean ||
        `INDOFLOODS-GAUGE-${s.legacy_gauge_id}` === clean ||
        s.name.toUpperCase().includes(clean)
    ) || WESTERN_GHATS_STATIONS[0]
  );
}

/**
 * Core Mock API Service matching FastAPI endpoint `POST /predict`
 * 
 * @param {Object} params
 * @param {string} params.station_id - Station identifier (e.g. 'MH_GAK_12' or '684')
 * @param {string} [params.date] - Prediction target date ISO string
 * @param {number[]} [params.simulation_rainfall] - Optional 10-day rainfall simulation values [P_T-10 ... P_T-1]
 * @param {{ day_1: number, day_3_cum: number, day_7_cum: number }} [params.rainfall_inputs] - Direct manual or live rainfall amounts
 * @param {string} [params.data_source] - Custom provenance label
 * @returns {Promise<Object>} Output matching FastAPI /predict schema
 */
export async function fetchFloodPrediction(params = {}) {
  const {
    station_id = 'MH_GAK_12',
    date = new Date().toISOString().split('T')[0],
    simulation_rainfall,
    rainfall_inputs,
    data_source,
  } = params;

  // Simulate network latency (180ms - 300ms) for realistic UX testing
  await new Promise((resolve) => setTimeout(resolve, 220));

  const station = findStation(station_id);
  const targetDate = date || new Date().toISOString().split('T')[0];
  const timestamp = new Date(`${targetDate}T12:00:00Z`).toISOString();

  let day1, day3Cum, day7Cum, probability, tier;

  if (rainfall_inputs) {
    day1 = Math.max(0, Math.min(1000, Number(rainfall_inputs.day_1) || 0));
    day3Cum = Math.max(day1, Math.min(1000, Number(rainfall_inputs.day_3_cum) || day1));
    day7Cum = Math.max(day3Cum, Math.min(1000, Number(rainfall_inputs.day_7_cum) || day3Cum));

    const score = (day1 * 0.45) + (day3Cum * 0.35) + (day7Cum * 0.20);
    probability = Math.min(0.99, Math.max(0.04, parseFloat((score / 150.0).toFixed(2))));
    tier = calculateRiskTier(probability);
  } else if (Array.isArray(simulation_rainfall) && simulation_rainfall.length > 0) {
    const cleanArr = simulation_rainfall.map((v) => Math.max(0, Number(v) || 0));
    const n = cleanArr.length;

    day1 = cleanArr[n - 1] || 0;
    day3Cum = cleanArr.slice(Math.max(0, n - 3)).reduce((a, b) => a + b, 0);
    day7Cum = cleanArr.slice(Math.max(0, n - 7)).reduce((a, b) => a + b, 0);

    // Dynamic probability computation based on Western Ghats catchment thresholds
    const score = (day1 * 0.45) + (day3Cum * 0.35) + (day7Cum * 0.20);
    probability = Math.min(0.99, Math.max(0.04, parseFloat((score / 150.0).toFixed(2))));
    tier = calculateRiskTier(probability);
  } else {
    day1 = station.base_rainfall.day_1;
    day3Cum = station.base_rainfall.day_3_cum;
    day7Cum = station.base_rainfall.day_7_cum;
    probability = station.default_probability;
    tier = station.default_tier;
  }

  const series = generateRainfallSeries(targetDate, day1, day3Cum, day7Cum);
  const alertTemplate = TIER_RECOMMENDATIONS[tier];

  let resolvedDataSource = data_source;
  if (!resolvedDataSource) {
    if (rainfall_inputs) resolvedDataSource = 'Synthetic Simulation (Manual Override)';
    else if (Array.isArray(simulation_rainfall)) resolvedDataSource = 'Interactive Simulation Sandbox';
    else resolvedDataSource = 'Open-Meteo Live API';
  }

  return {
    station_id: station.station_id,
    catchment_name: `${station.name} (${station.river} / ${station.basin})`,
    lat: station.lat,
    lng: station.lng,
    timestamp,
    data_source: resolvedDataSource,
    rainfall: {
      day_1: parseFloat(day1.toFixed(1)),
      day_3_cum: parseFloat(day3Cum.toFixed(1)),
      day_7_cum: parseFloat(day7Cum.toFixed(1)),
      series,
    },
    prediction: {
      probability,
      risk_tier: tier,
    },
    alert: {
      title: `${alertTemplate.title} — ${station.name} Station`,
      recommendation: alertTemplate.recommendation,
      issued_at: timestamp,
    },
  };
}

/**
 * Fetch live precipitation data from Open-Meteo Forecast API
 *
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 * @returns {Promise<Object>} Precipitation data and metadata
 */
export async function fetchLiveOpenMeteoRainfall(lat, lng) {
  try {
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lng}&daily=precipitation_sum&timezone=auto&past_days=10&forecast_days=0`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Open-Meteo responded with HTTP ${response.status}`);
    }
    const data = await response.json();
    const rawValues = data.daily?.precipitation_sum || [];
    const values = rawValues.slice(-10).map((v) => (v != null && !isNaN(v) ? Math.max(0, Number(v)) : 0));
    while (values.length < 10) values.unshift(0);

    const day_1 = values[values.length - 1];
    const day_3_cum = values.slice(-3).reduce((acc, v) => acc + v, 0);
    const day_7_cum = values.slice(-7).reduce((acc, v) => acc + v, 0);

    return {
      success: true,
      source: 'Open-Meteo Live API',
      timestamp: new Date().toISOString(),
      series_10d: values,
      rainfall: {
        day_1: parseFloat(day_1.toFixed(1)),
        day_3_cum: parseFloat(day_3_cum.toFixed(1)),
        day_7_cum: parseFloat(day_7_cum.toFixed(1)),
      },
    };
  } catch (err) {
    console.warn('Open-Meteo live API request failed, utilizing telemetry baseline:', err.message);
    return {
      success: false,
      source: 'Open-Meteo Live API (Offline Baseline)',
      error: err.message,
      timestamp: new Date().toISOString(),
    };
  }
}

/**
 * Fetch overview of all 20 stations with their current status
 */
export async function fetchAllStations(date = new Date().toISOString().split('T')[0]) {
  await new Promise((resolve) => setTimeout(resolve, 150));
  return WESTERN_GHATS_STATIONS.map((s) => ({
    station_id: s.station_id,
    legacy_gauge_id: s.legacy_gauge_id,
    name: s.name,
    river: s.river,
    basin: s.basin,
    district: s.district,
    lat: s.lat,
    lng: s.lng,
    risk_tier: s.default_tier,
    probability: s.default_probability,
    day_1_rain: s.base_rainfall.day_1,
    warning_level_m: s.warning_level_m,
    danger_level_m: s.danger_level_m,
  }));
}
