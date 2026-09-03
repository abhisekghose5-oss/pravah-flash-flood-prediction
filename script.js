/**
 * PRAVAH — Emergency Flood Early Warning System
 * Master Interactive Logic: Warning Popup Modal, Timer & Controls
 */

document.addEventListener('DOMContentLoaded', () => {
  const modalOverlay = document.getElementById('warningModalOverlay');
  const dismissBtn = document.getElementById('dismissAlertBtn');
  const clockEl = document.getElementById('systemClock');

  /**
   * Opens the Advanced Emergency Warning Popup
   * Displays high-priority alert modal with spring entrance animation
   */
  function showWarningPopup() {
    if (modalOverlay) {
      modalOverlay.classList.add('active');
      modalOverlay.setAttribute('aria-hidden', 'false');
      console.log('[PRAVAH] Advanced Warning Modal triggered automatically.');
    }
  }

  /**
   * Dismisses the Warning Popup
   * Removes modal and blur backdrop filter overlay
   */
  function dismissWarningPopup() {
    if (modalOverlay) {
      modalOverlay.classList.remove('active');
      modalOverlay.setAttribute('aria-hidden', 'true');
      console.log('[PRAVAH] Warning Modal dismissed by operator.');
    }
  }

  // REQUIREMENT 4: Trigger popup automatically 2 seconds after page load
  const autoTriggerTimer = setTimeout(() => {
    showWarningPopup();
  }, 2000);

  // Bind Dismiss Button Click
  if (dismissBtn) {
    dismissBtn.addEventListener('click', (e) => {
      e.preventDefault();
      dismissWarningPopup();
    });
  }

  // Close modal when clicking on the dark backdrop outside the card
  if (modalOverlay) {
    modalOverlay.addEventListener('click', (e) => {
      if (e.target === modalOverlay) {
        dismissWarningPopup();
      }
    });
  }

  // Close modal with Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modalOverlay && modalOverlay.classList.contains('active')) {
      dismissWarningPopup();
    }
  });

  // Digital Clock Real-time updater
  function updateClock() {
    if (!clockEl) return;
    const now = new Date();
    const timeStr =
      now.toLocaleTimeString('en-GB', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }) + ' IST';
    clockEl.textContent = timeStr;
  }
  setInterval(updateClock, 1000);
  updateClock();

  let rainfallChartInstance = null;

  /**
   * Requirement 3: Initialize 7-Day Rainfall vs. Flood Threshold Chart
   */
  function initRainfallChart() {
    const canvas = document.getElementById('rainfallTimeseriesChart');
    const customTooltipEl = document.getElementById('chartCustomTooltip');
    if (!canvas || typeof Chart === 'undefined') return;

    const ctx = canvas.getContext('2d');

    // Create Neon Cyan vertical gradient for the rainfall bar/line
    const cyanGradient = ctx.createLinearGradient(0, 0, 0, 240);
    cyanGradient.addColorStop(0, 'rgba(6, 182, 212, 0.45)');
    cyanGradient.addColorStop(1, 'rgba(6, 182, 212, 0.02)');

    const dummyDays = ['Day -6', 'Day -5', 'Day -4', 'Day -3', 'Day -2', 'Day -1', 'Today (T-0)'];
    const dummyRainfall = [22.4, 38.0, 45.2, 59.5, 92.0, 110.5, 85.0];
    const dangerThresholdData = [120, 120, 120, 120, 120, 120, 120];

    rainfallChartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: dummyDays,
        datasets: [
          {
            label: 'Observed Rainfall (mm)',
            data: dummyRainfall,
            borderColor: '#06b6d4',
            borderWidth: 2.8,
            backgroundColor: cyanGradient,
            fill: true,
            tension: 0.38,
            pointBackgroundColor: '#06b6d4',
            pointBorderColor: '#ffffff',
            pointBorderWidth: 2,
            pointRadius: 4.5,
            pointHoverRadius: 7,
            pointHoverBackgroundColor: '#ffffff',
            pointHoverBorderColor: '#06b6d4',
            pointHoverBorderWidth: 3,
            order: 2,
          },
          {
            label: 'Danger Threshold (120 mm)',
            data: dangerThresholdData,
            borderColor: '#ef4444',
            borderWidth: 2,
            borderDash: [6, 6],
            fill: false,
            pointRadius: 0,
            pointHoverRadius: 0,
            order: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          legend: {
            display: false, // Handled by our high-contrast header chips
          },
          tooltip: {
            enabled: false, // Use Custom Styled HTML Tooltip (Requirement 3)
            external: function (context) {
              if (!customTooltipEl) return;
              const { chart, tooltip } = context;

              if (tooltip.opacity === 0) {
                customTooltipEl.style.opacity = '0';
                return;
              }

              const dataIndex = tooltip.dataPoints[0].dataIndex;
              const rainVal = tooltip.dataPoints[0].raw;
              const dayLabel = chart.data.labels[dataIndex];
              const isBreached = rainVal >= 120;

              customTooltipEl.innerHTML = `
                <div class="chart-tooltip-title">${dayLabel}</div>
                <div class="chart-tooltip-val">
                  <span>${Number(rainVal).toFixed(1)} mm</span>
                  <span class="chart-tooltip-badge ${isBreached ? 'danger' : 'safe'}">
                    ${isBreached ? 'CRITICAL BREACH' : 'SUB-THRESHOLD'}
                  </span>
                </div>
              `;

              const canvasRect = chart.canvas.getBoundingClientRect();
              const leftPos = tooltip.caretX + 15;
              const topPos = Math.max(10, tooltip.caretY - 30);

              customTooltipEl.style.opacity = '1';
              customTooltipEl.style.left = `${leftPos}px`;
              customTooltipEl.style.top = `${topPos}px`;
            },
          },
        },
        scales: {
          x: {
            grid: {
              color: 'rgba(255, 255, 255, 0.05)',
              tickColor: 'transparent',
            },
            ticks: {
              color: '#94a3b8',
              font: {
                family: 'JetBrains Mono',
                size: 11,
              },
            },
          },
          y: {
            min: 0,
            max: 140,
            grid: {
              color: 'rgba(255, 255, 255, 0.06)',
            },
            ticks: {
              color: '#94a3b8',
              font: {
                family: 'JetBrains Mono',
                size: 11,
              },
              callback: function (value) {
                return value + ' mm';
              },
            },
          },
        },
      },
    });
  }

  // Initialize Chart on load
  initRainfallChart();

  /**
   * Requirement 4: Dynamic Prediction & Risk UI Updater
   * @param {number} probability - Flood probability (0 to 100 or 0.0 to 1.0)
   * @param {string} riskLevel - 'NORMAL' | 'ADVISORY' | 'WARNING' | 'EMERGENCY'
   * @param {number[]|number} rainData - Array of 7 days rainfall [mm], or 1-day rain number
   * @param {number} [rain3d] - Optional 3-day rain if rainData is single number
   * @param {number} [rain7d] - Optional 7-day rain if rainData is single number
   */
  function updatePredictionUI(probability, riskLevel, rainData, rain3d, rain7d) {
    const pct = Math.round(probability <= 1 ? probability * 100 : probability);
    const circumference = 314.16; // 2 * PI * 50
    const targetOffset = circumference - (circumference * (pct / 100));

    // Elements
    const circle = document.getElementById('gaugeProgressCircle');
    const pctVal = document.getElementById('gaugeProbabilityValue');
    const badge = document.getElementById('predRiskBadge');
    const rain1El = document.getElementById('metricRain1d');
    const rain3El = document.getElementById('metricRain3d');
    const rain7El = document.getElementById('metricRain7d');
    const diagTag = document.getElementById('diagnosisCode');
    const diagText = document.getElementById('diagnosisText');

    // Process Rainfall Data (Support either 7-day array or individual arguments)
    let r1 = 85.0, r3 = 190.4, r7 = 320.0;
    if (Array.isArray(rainData)) {
      r1 = rainData[rainData.length - 1] || 0;
      r3 = rainData.slice(-3).reduce((acc, v) => acc + v, 0);
      r7 = rainData.reduce((acc, v) => acc + v, 0);

      // Update Chart.js dataset smoothly (Requirement 4)
      if (rainfallChartInstance) {
        rainfallChartInstance.data.datasets[0].data = rainData;
        const strokeColor = pct >= 75 || riskLevel === 'EMERGENCY' ? '#ef4444' : pct >= 50 || riskLevel === 'WARNING' ? '#f97316' : pct >= 25 || riskLevel === 'ADVISORY' ? '#eab308' : '#06b6d4';
        rainfallChartInstance.data.datasets[0].borderColor = strokeColor;
        rainfallChartInstance.data.datasets[0].pointBorderColor = strokeColor;
        rainfallChartInstance.update();
      }
    } else if (typeof rainData === 'number') {
      r1 = rainData;
      if (rain3d !== undefined) r3 = rain3d;
      if (rain7d !== undefined) r7 = rain7d;
    }

    // 1. Animate Circular Progress Gauge (Requirement 2)
    if (circle) {
      circle.style.strokeDashoffset = targetOffset;

      // Calibrated Color Mapping
      let strokeColor = '#06b6d4'; // Normal
      if (pct >= 75 || riskLevel === 'EMERGENCY') strokeColor = '#ef4444';
      else if (pct >= 50 || riskLevel === 'WARNING') strokeColor = '#f97316';
      else if (pct >= 25 || riskLevel === 'ADVISORY') strokeColor = '#eab308';

      circle.style.stroke = strokeColor;
    }

    // Number count-up animation
    if (pctVal) {
      let current = 0;
      const stepTime = Math.max(10, Math.floor(1200 / (pct || 1)));
      const counter = setInterval(() => {
        current += 1;
        if (current >= pct) {
          pctVal.textContent = `${pct}%`;
          clearInterval(counter);
        } else {
          pctVal.textContent = `${current}%`;
        }
      }, stepTime);
    }

    // 2. Update Risk Tier Badge with Continuous Pulse (Requirement 2)
    if (badge) {
      const tier = (riskLevel || (pct >= 75 ? 'EMERGENCY' : pct >= 50 ? 'WARNING' : pct >= 25 ? 'ADVISORY' : 'NORMAL')).toUpperCase();
      badge.className = `risk-tier-pill ${tier.toLowerCase()}`;
      
      // Continuous soft pulse on WARNING or EMERGENCY
      if (tier === 'EMERGENCY' || tier === 'WARNING') {
        badge.classList.add('pulse-badge');
      } else {
        badge.classList.remove('pulse-badge');
      }

      const textSpan = badge.querySelector('.tier-text');
      if (textSpan) textSpan.textContent = tier;
    }

    // 3. Update Rainfall Metrics Grid (Requirement 2)
    if (rain1El) rain1El.textContent = Number(r1).toFixed(1);
    if (rain3El) rain3El.textContent = Number(r3).toFixed(1);
    if (rain7El) rain7El.textContent = Number(r7).toFixed(1);

    // 4. Update Diagnosis Narrative
    if (diagTag && diagText) {
      if (pct >= 75) {
        diagTag.className = 'diagnosis-status-tag red';
        diagTag.textContent = 'SURGING INFLOW';
        diagText.textContent = 'High-confidence flood probability detected. Upstream catchment headwaters have breached saturation threshold.';
      } else if (pct >= 50) {
        diagTag.className = 'diagnosis-status-tag orange';
        diagTag.textContent = 'STAGE INUNDATION WATCH';
        diagText.textContent = 'Substantial runoff accumulation detected. Water surface elevation approaching channel warning mark.';
      } else if (pct >= 25) {
        diagTag.className = 'diagnosis-status-tag orange';
        diagTag.textContent = 'ELEVATED BASELINE';
        diagText.textContent = 'Saturated soil profile. Localized surface ponding possible in low-lying bank culverts.';
      } else {
        diagTag.className = 'diagnosis-status-tag green';
        diagTag.textContent = 'STABLE REGIME';
        diagText.textContent = 'Discharge velocity operating safely within seasonal channel carrying capacity.';
      }
    }

    console.log(`[PRAVAH Prediction] Updated: ${pct}% (${riskLevel || 'AUTO'}), Rain: 1d=${r1}mm, 3d=${r3}mm, 7d=${r7}mm`);
  }

  // =========================================================================
  // Catchment Telemetry Master Data (20 Western Ghats Stations)
  // =========================================================================
  const CATCHMENT_STATIONS = {
    'MH_GAK_12': {
      station_id: 'MH_GAK_12',
      name: 'Karad',
      river: 'Krishna',
      district: 'Satara',
      lat: 17.2944,
      lng: 74.1903,
      rainfall: '85.0 mm',
      warning_level_m: 563.0,
      danger_level_m: 565.8,
      risk: 'EMERGENCY',
      flood_prob: 0.84,
      rain_1d: 85.0,
      rain_3d: 195.5,
      rain_7d: 452.6,
      rain_history: [22.4, 38.0, 45.2, 59.5, 92.0, 110.5, 85.0],
      diagnosis_tag: 'SURGING INFLOW',
      diagnosis_text: 'High-confidence flood probability detected. Upstream catchment headwaters have breached saturation threshold. Immediate alert active for low-lying riparian settlements.',
      headline: 'CRITICAL: High Flood Probability (84%) Detected in Krishna River Basin',
      desc: 'Immediate evacuation protocols recommended for Karad and downstream low-lying riparian settlements. SDRF teams placed on standby.'
    },
    'MH_GAK_17': {
      station_id: 'MH_GAK_17',
      name: 'Mahad',
      river: 'Savitri',
      district: 'Raigad',
      lat: 18.0833,
      lng: 73.4167,
      rainfall: '94.2 mm',
      warning_level_m: 6.5,
      danger_level_m: 8.0,
      risk: 'EMERGENCY',
      flood_prob: 0.92,
      rain_1d: 94.2,
      rain_3d: 212.0,
      rain_7d: 498.7,
      rain_history: [28.0, 42.5, 55.0, 68.0, 84.0, 118.0, 94.2],
      diagnosis_tag: 'CRITICAL OVERTOPPING',
      diagnosis_text: 'Severe flash flood surge recorded. Low-lying market area inundated; tidal surge compounding upstream catchment runoff.',
      headline: 'EMERGENCY: Extreme Runoff (92%) Breaching Savitri River Banks at Mahad',
      desc: 'Severe flash flood surge recorded. Low-lying market area inundated; SDRF team and NDRF boat teams deployed.'
    },
    'MH_GAK_01': {
      station_id: 'MH_GAK_01',
      name: 'Terwad',
      river: 'Panchganga',
      district: 'Kolhapur',
      lat: 16.7333,
      lng: 74.5833,
      rainfall: '62.4 mm',
      warning_level_m: 535.0,
      danger_level_m: 537.5,
      risk: 'WARNING',
      flood_prob: 0.65,
      rain_1d: 62.4,
      rain_3d: 148.0,
      rain_7d: 310.5,
      rain_history: [15.0, 24.0, 38.0, 52.0, 65.0, 78.0, 62.4],
      diagnosis_tag: 'STAGE INUNDATION WATCH',
      diagnosis_text: 'Panchganga river levels surging towards danger mark. Agricultural riparian plains under inundation watch.',
      headline: 'WARNING: Rapid River Inflow (65%) on Panchganga River at Terwad',
      desc: 'Agricultural riparian plains under inundation watch. Barrage gates opened to regulate downstream surge.'
    },
    'MH_GAK_18': {
      station_id: 'MH_GAK_18',
      name: 'Badlapur',
      river: 'Ulhas',
      district: 'Thane',
      lat: 19.1500,
      lng: 73.2667,
      rainfall: '58.0 mm',
      warning_level_m: 16.5,
      danger_level_m: 18.2,
      risk: 'WARNING',
      flood_prob: 0.58,
      rain_1d: 58.0,
      rain_3d: 135.0,
      rain_7d: 284.0,
      rain_history: [18.0, 22.0, 35.0, 44.0, 55.0, 64.0, 58.0],
      diagnosis_tag: 'CHANNEL SURCHARGE',
      diagnosis_text: 'Continuous monsoon precipitation causing localized surface pooling along urban culverts. Railway track telemetry monitored.',
      headline: 'WARNING: Ulhas River Approaching Warning Stage at Badlapur (58%)',
      desc: 'Continuous monsoon precipitation causing localized surface pooling along urban culverts. Railway tracks monitoring initiated.'
    },
    'MH_GAK_14': {
      station_id: 'MH_GAK_14',
      name: 'Chiplun',
      river: 'Vashishti',
      district: 'Ratnagiri',
      lat: 17.5333,
      lng: 73.5167,
      rainfall: '68.0 mm',
      warning_level_m: 6.8,
      danger_level_m: 8.2,
      risk: 'WARNING',
      flood_prob: 0.62,
      rain_1d: 68.0,
      rain_3d: 152.0,
      rain_7d: 330.0,
      rain_history: [14.0, 26.0, 39.0, 50.0, 67.0, 82.0, 68.0],
      diagnosis_tag: 'ESTUARINE BACKWATER SURGE',
      diagnosis_text: 'Tidal backwater effect compounding rainfall accumulation. River levels approaching warning line.',
      headline: 'WARNING: High Tide + Upstream Surge Alert on Vashishti River at Chiplun',
      desc: 'Tidal backwater effect compounding rainfall accumulation. Market zones advised to move inventory to upper floors.'
    },
    'MH_GAK_03': {
      station_id: 'MH_GAK_03',
      name: 'Kurundwad',
      river: 'Krishna',
      district: 'Kolhapur',
      lat: 16.6833,
      lng: 74.6000,
      rainfall: '36.5 mm',
      warning_level_m: 532.0,
      danger_level_m: 534.5,
      risk: 'ADVISORY',
      flood_prob: 0.38,
      rain_1d: 36.5,
      rain_3d: 82.0,
      rain_7d: 178.0,
      rain_history: [12.0, 16.0, 22.0, 31.0, 38.0, 42.0, 36.5],
      diagnosis_tag: 'ELEVATED BASELINE',
      diagnosis_text: 'Saturated soil profile. Steady runoff accumulation from upstream Koyna catchment.',
      headline: 'ADVISORY: Saturated Catchment Profile in Krishna Basin at Kurundwad (38%)',
      desc: 'River levels rising steadily. Upstream dams releasing excess discharge at controlled rates.'
    },
    'MH_GAK_02': {
      station_id: 'MH_GAK_02',
      name: 'Shirol',
      river: 'Dudhganga',
      district: 'Kolhapur',
      lat: 16.7167,
      lng: 74.6167,
      rainfall: '34.0 mm',
      warning_level_m: 533.0,
      danger_level_m: 535.5,
      risk: 'ADVISORY',
      flood_prob: 0.35,
      rain_1d: 34.0,
      rain_3d: 78.0,
      rain_7d: 165.0,
      rain_history: [10.0, 14.0, 20.0, 28.0, 35.0, 40.0, 34.0],
      diagnosis_tag: 'CONFLUENCE SWELL',
      diagnosis_text: 'Dudhganga tributary contributing moderate inflow. Low-level bridges under inspection.',
      headline: 'ADVISORY: Dudhganga River Channel Monitoring at Shirol (35%)',
      desc: 'Sub-catchment receiving steady mountain precipitation; low-level bridges monitored.'
    },
    'MH_GAK_16': {
      station_id: 'MH_GAK_16',
      name: 'Poladpur',
      river: 'Savitri',
      district: 'Raigad',
      lat: 17.9833,
      lng: 73.4667,
      rainfall: '32.0 mm',
      warning_level_m: 14.0,
      danger_level_m: 16.0,
      risk: 'ADVISORY',
      flood_prob: 0.32,
      rain_1d: 32.0,
      rain_3d: 74.0,
      rain_7d: 156.0,
      rain_history: [11.0, 15.0, 21.0, 26.0, 34.0, 38.0, 32.0],
      diagnosis_tag: 'GHAT RUNOFF ACCUMULATION',
      diagnosis_text: 'Steep hill slopes generating rapid overland flow into Savitri headwaters.',
      headline: 'ADVISORY: Ghat Runoff Accumulation in Savitri Headwaters at Poladpur',
      desc: 'Steep hill slopes generating rapid overland flow. Landslide alert active along ghat highway.'
    },
    'MH_GAK_08': {
      station_id: 'MH_GAK_08',
      name: 'Bhilawadi',
      river: 'Krishna',
      district: 'Sangli',
      lat: 17.0167,
      lng: 74.4500,
      rainfall: '28.0 mm',
      warning_level_m: 542.0,
      danger_level_m: 544.5,
      risk: 'ADVISORY',
      flood_prob: 0.28,
      rain_1d: 28.0,
      rain_3d: 65.0,
      rain_7d: 138.0,
      rain_history: [9.0, 12.0, 18.0, 24.0, 30.0, 32.0, 28.0],
      diagnosis_tag: 'ELEVATED BASELINE',
      diagnosis_text: 'Moderate runoff from Karad reach passing downstream without channel overflow.',
      headline: 'ADVISORY: River Stage Nearing Normal Buffer at Bhilawadi (28%)',
      desc: 'Irrigation department monitoring ghat runoff discharges.'
    },
    'MH_GAK_09': {
      station_id: 'MH_GAK_09',
      name: 'Sangli Bridge',
      river: 'Krishna',
      district: 'Sangli',
      lat: 16.8500,
      lng: 74.5667,
      rainfall: '18.2 mm',
      warning_level_m: 540.0,
      danger_level_m: 542.5,
      risk: 'NORMAL',
      flood_prob: 0.18,
      rain_1d: 18.2,
      rain_3d: 42.0,
      rain_7d: 95.0,
      rain_history: [6.0, 8.0, 12.0, 16.0, 20.0, 22.0, 18.2],
      diagnosis_tag: 'STABLE REGIME',
      diagnosis_text: 'Discharge velocity operating safely within seasonal channel carrying capacity.',
      headline: 'NORMAL STATUS: Stable Hydrometric Regime at Sangli Bridge (18%)',
      desc: 'Water velocity well within engineered levee capacity. No municipal flood hazard observed.'
    },
    'MH_GAK_04': {
      station_id: 'MH_GAK_04',
      name: 'Arjunwad',
      river: 'Krishna',
      district: 'Kolhapur',
      lat: 16.6333,
      lng: 74.6500,
      rainfall: '16.0 mm',
      warning_level_m: 530.0,
      danger_level_m: 532.5,
      risk: 'NORMAL',
      flood_prob: 0.15,
      rain_1d: 16.0,
      rain_3d: 38.0,
      rain_7d: 84.0,
      rain_history: [5.0, 7.0, 10.0, 14.0, 18.0, 19.0, 16.0],
      diagnosis_tag: 'STABLE REGIME',
      diagnosis_text: 'Flow depth stable. No threat to adjacent agricultural fields.',
      headline: 'NORMAL: Safe Channel Discharge at Arjunwad (15%)',
      desc: 'Routine seasonal water surface elevation maintained.'
    },
    'MH_GAK_05': {
      station_id: 'MH_GAK_05',
      name: 'Rajaapur',
      river: 'Krishna',
      district: 'Kolhapur',
      lat: 16.5833,
      lng: 74.7000,
      rainfall: '14.5 mm',
      warning_level_m: 528.0,
      danger_level_m: 530.5,
      risk: 'NORMAL',
      flood_prob: 0.12,
      rain_1d: 14.5,
      rain_3d: 34.0,
      rain_7d: 76.0,
      rain_history: [4.0, 6.0, 9.0, 12.0, 15.0, 17.0, 14.5],
      diagnosis_tag: 'BASELINE FLOW',
      diagnosis_text: 'Baseline hydrodynamic readings recorded at the interstate discharge gauge.',
      headline: 'NORMAL: Baseline Flow Profile at Rajaapur (12%)',
      desc: 'All downstream irrigation regulators operating normally.'
    },
    'MH_GAK_06': {
      station_id: 'MH_GAK_06',
      name: 'Koyna Dam',
      river: 'Koyna',
      district: 'Satara',
      lat: 17.4000,
      lng: 73.7500,
      rainfall: '45.0 mm',
      warning_level_m: 657.0,
      danger_level_m: 660.0,
      risk: 'NORMAL',
      flood_prob: 0.22,
      rain_1d: 45.0,
      rain_3d: 98.0,
      rain_7d: 210.0,
      rain_history: [12.0, 18.0, 25.0, 34.0, 42.0, 48.0, 45.0],
      diagnosis_tag: 'RESERVOIR BUFFERING',
      diagnosis_text: 'Shivajisagar reservoir operating with ample flood-cushion storage buffer.',
      headline: 'NORMAL: Koyna Dam Reservoir Operating at 78% Capacity (22% Flood Risk)',
      desc: 'Controlled hydro-electric generation spillway discharge. Storage buffer adequate.'
    },
    'MH_GAK_07': {
      station_id: 'MH_GAK_07',
      name: 'Warna Dam',
      river: 'Warna',
      district: 'Sangli',
      lat: 17.1333,
      lng: 73.8000,
      rainfall: '38.0 mm',
      warning_level_m: 624.0,
      danger_level_m: 627.0,
      risk: 'NORMAL',
      flood_prob: 0.20,
      rain_1d: 38.0,
      rain_3d: 86.0,
      rain_7d: 185.0,
      rain_history: [10.0, 15.0, 22.0, 29.0, 36.0, 40.0, 38.0],
      diagnosis_tag: 'REGULATED DISCHARGE',
      diagnosis_text: 'Warna reservoir maintaining calibrated outflow to prevent downstream bank overflow.',
      headline: 'NORMAL: Warna Dam Storage Within Safe Limits (20%)',
      desc: 'No emergency crest gate release scheduled.'
    },
    'MH_GAK_10': {
      station_id: 'MH_GAK_10',
      name: 'Miraj',
      river: 'Krishna',
      district: 'Sangli',
      lat: 16.8333,
      lng: 74.6333,
      rainfall: '15.0 mm',
      warning_level_m: 538.0,
      danger_level_m: 540.5,
      risk: 'NORMAL',
      flood_prob: 0.14,
      rain_1d: 15.0,
      rain_3d: 35.0,
      rain_7d: 78.0,
      rain_history: [4.0, 6.0, 9.0, 12.0, 16.0, 18.0, 15.0],
      diagnosis_tag: 'STABLE REGIME',
      diagnosis_text: 'Water surface elevation 2.5m below stage warning mark.',
      headline: 'NORMAL: Miraj Hydrometric Station Operating at Steady Baseline',
      desc: 'Riparian embankment sensors nominal.'
    },
    'MH_GAK_11': {
      station_id: 'MH_GAK_11',
      name: 'Shirala',
      river: 'Morna',
      district: 'Sangli',
      lat: 16.9833,
      lng: 74.1333,
      rainfall: '21.0 mm',
      warning_level_m: 575.0,
      danger_level_m: 577.5,
      risk: 'NORMAL',
      flood_prob: 0.16,
      rain_1d: 21.0,
      rain_3d: 48.0,
      rain_7d: 106.0,
      rain_history: [6.0, 9.0, 13.0, 18.0, 22.0, 24.0, 21.0],
      diagnosis_tag: 'STABLE REGIME',
      diagnosis_text: 'Catchment soil absorption high; no immediate runoff concerns.',
      headline: 'NORMAL: Morna Tributary Operating Within Banks at Shirala',
      desc: 'Catchment soil absorption high; no immediate runoff concerns.'
    },
    'MH_GAK_13': {
      station_id: 'MH_GAK_13',
      name: 'Patan',
      river: 'Kera',
      district: 'Satara',
      lat: 17.3667,
      lng: 73.9000,
      rainfall: '22.4 mm',
      warning_level_m: 580.0,
      danger_level_m: 582.5,
      risk: 'NORMAL',
      flood_prob: 0.17,
      rain_1d: 22.4,
      rain_3d: 52.0,
      rain_7d: 114.0,
      rain_history: [7.0, 10.0, 14.0, 19.0, 24.0, 26.0, 22.4],
      diagnosis_tag: 'STABLE REGIME',
      diagnosis_text: 'Hill streams flowing safely into Koyna basin.',
      headline: 'NORMAL: Kera River Flow Stable at Patan (17%)',
      desc: 'Hill streams flowing safely into Koyna basin.'
    },
    'MH_GAK_15': {
      station_id: 'MH_GAK_15',
      name: 'Khed',
      river: 'Jagbudi',
      district: 'Ratnagiri',
      lat: 17.7167,
      lng: 73.3833,
      rainfall: '17.5 mm',
      warning_level_m: 6.0,
      danger_level_m: 7.5,
      risk: 'NORMAL',
      flood_prob: 0.15,
      rain_1d: 17.5,
      rain_3d: 40.0,
      rain_7d: 88.0,
      rain_history: [5.0, 8.0, 11.0, 15.0, 19.0, 20.0, 17.5],
      diagnosis_tag: 'STABLE REGIME',
      diagnosis_text: 'Coastal river stage is clear with calm tidal cycles.',
      headline: 'NORMAL: Jagbudi River Flow Clear at Khed (15%)',
      desc: 'Coastal river stage is clear with calm tidal cycles.'
    },
    'MH_GAK_19': {
      station_id: 'MH_GAK_19',
      name: 'Bhivpuri',
      river: 'Pej',
      district: 'Raigad',
      lat: 18.9333,
      lng: 73.3333,
      rainfall: '19.0 mm',
      warning_level_m: 24.0,
      danger_level_m: 26.5,
      risk: 'NORMAL',
      flood_prob: 0.16,
      rain_1d: 19.0,
      rain_3d: 44.0,
      rain_7d: 96.0,
      rain_history: [6.0, 8.0, 12.0, 16.0, 20.0, 21.0, 19.0],
      diagnosis_tag: 'STABLE REGIME',
      diagnosis_text: 'All mountain headwater channels flowing steadily.',
      headline: 'NORMAL: Pej River Tailrace Basin Clear at Bhivpuri',
      desc: 'All mountain headwater channels flowing steadily.'
    },
    'MH_GAK_20': {
      station_id: 'MH_GAK_20',
      name: 'Khopoli',
      river: 'Patalganga',
      district: 'Raigad',
      lat: 18.7833,
      lng: 73.3500,
      rainfall: '23.0 mm',
      warning_level_m: 48.0,
      danger_level_m: 50.5,
      risk: 'NORMAL',
      flood_prob: 0.19,
      rain_1d: 23.0,
      rain_3d: 54.0,
      rain_7d: 118.0,
      rain_history: [7.0, 10.0, 15.0, 20.0, 25.0, 27.0, 23.0],
      diagnosis_tag: 'STABLE REGIME',
      diagnosis_text: 'Industrial corridor drainage network functioning normally.',
      headline: 'NORMAL: Patalganga River Channel Stable at Khopoli (19%)',
      desc: 'Industrial corridor drainage network functioning normally.'
    }
  };

  /**
   * Select and Synchronize any station across the entire dashboard
   * @param {string} stationId - e.g. 'MH_GAK_12'
   */
  function selectStation(stationId) {
    const station = CATCHMENT_STATIONS[stationId];
    if (!station) return;

    // 1. Highlight clicked card in sidebar
    const allCards = document.querySelectorAll('.station-card');
    let targetCard = null;
    allCards.forEach((card) => {
      if (card.getAttribute('data-station-id') === stationId) {
        card.classList.add('active');
        targetCard = card;
      } else {
        card.classList.remove('active');
      }
    });

    if (targetCard) {
      targetCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // 2. Update Prediction & Risk Analysis Panel
    const predLabel = document.getElementById('predStationLabel');
    if (predLabel) {
      predLabel.textContent = `${station.name} (${station.station_id}) • ${station.river} River Basin, ${station.district}`;
    }

    updatePredictionUI(
      Math.round(station.flood_prob * 100),
      station.risk,
      station.rain_history
    );

    // Update diagnosis tag and description specifically
    const diagTag = document.getElementById('diagnosisCode');
    const diagText = document.getElementById('diagnosisText');
    if (diagTag) {
      diagTag.className = `diagnosis-status-tag ${station.risk === 'EMERGENCY' ? 'red' : station.risk === 'WARNING' ? 'orange' : 'green'}`;
      diagTag.textContent = station.diagnosis_tag;
    }
    if (diagText) {
      diagText.textContent = station.diagnosis_text;
    }

    // 3. Update Top Incident Alert Banner
    const bannerHeadline = document.getElementById('alertBannerHeadline');
    const bannerDesc = document.getElementById('alertBannerDescription');
    const bannerBtn = document.getElementById('alertBannerActionBtn');

    if (bannerHeadline) bannerHeadline.textContent = station.headline;
    if (bannerDesc) bannerDesc.textContent = station.desc;
    if (bannerBtn) {
      if (station.risk === 'EMERGENCY') {
        bannerBtn.className = 'btn btn-alert magnetic';
        bannerBtn.innerHTML = '<span>Issue Sirens</span>';
      } else if (station.risk === 'WARNING') {
        bannerBtn.className = 'btn btn-ctrl btn-ctrl-accent magnetic';
        bannerBtn.innerHTML = '<span>Issue Advisory</span>';
      } else {
        bannerBtn.className = 'btn btn-ghost magnetic';
        bannerBtn.innerHTML = '<span>Station Telemetry</span>';
      }
    }

    // 4. Smoothly Fly 3D Globe to Station
    if (window.PRAVAH_GLOBE && window.PRAVAH_GLOBE.flyToStation) {
      window.PRAVAH_GLOBE.flyToStation(stationId);
    }

    console.log(`[PRAVAH] Synchronized to Station: ${station.name} (${stationId})`);
  }

  /**
   * Initialize Catchment Telemetry Search, Clear, and Event Handlers
   */
  function initCatchmentTelemetry() {
    const searchInput = document.getElementById('stationSearchInput');
    const clearBtn = document.getElementById('clearStationSearchBtn');
    const badgeCount = document.getElementById('stationCountBadge');
    const listContainer = document.getElementById('stationListContainer');
    const emptyState = document.getElementById('stationEmptyState');
    const emptyMsg = document.getElementById('stationEmptyMsg');

    if (!listContainer) return;

    // Click on any card in the list (event delegation)
    listContainer.addEventListener('click', (e) => {
      const card = e.target.closest('.station-card');
      if (card) {
        const id = card.getAttribute('data-station-id');
        if (id) selectStation(id);
      }
    });

    // Real-time Search & Filter
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim().toLowerCase();
        const cards = listContainer.querySelectorAll('.station-card');
        let visibleCount = 0;

        cards.forEach((card) => {
          const name = (card.getAttribute('data-name') || '').toLowerCase();
          const code = (card.getAttribute('data-code') || '').toLowerCase();
          const river = (card.getAttribute('data-river') || '').toLowerCase();
          const district = (card.getAttribute('data-district') || '').toLowerCase();
          const risk = (card.getAttribute('data-risk') || '').toLowerCase();

          const matches =
            name.includes(query) ||
            code.includes(query) ||
            river.includes(query) ||
            district.includes(query) ||
            risk.includes(query);

          if (matches) {
            card.style.display = 'flex';
            visibleCount++;
          } else {
            card.style.display = 'none';
          }
        });

        if (clearBtn) {
          clearBtn.style.display = query.length > 0 ? 'inline-flex' : 'none';
        }

        if (badgeCount) {
          badgeCount.textContent = query ? `${visibleCount} / 20 STATIONS` : '20 STATIONS';
        }

        if (emptyState) {
          if (visibleCount === 0) {
            emptyState.style.display = 'flex';
            if (emptyMsg) emptyMsg.textContent = `No river gauges match "${e.target.value}".`;
          } else {
            emptyState.style.display = 'none';
          }
        }
      });
    }

    // Clear Search Input Button
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        if (searchInput) {
          searchInput.value = '';
          searchInput.dispatchEvent(new Event('input'));
          searchInput.focus();
        }
      });
    }
  }

  // Initialize Catchment Telemetry
  initCatchmentTelemetry();

  // Animate Gauge on initial page load (starts at 0% and animates to 84% with 7-day chart data)
  setTimeout(() => {
    selectStation('MH_GAK_12');
  }, 450);

  // =========================================================================
  // Team Modal Logic (Open, Dismiss, Keyboard & Backdrop click)
  // =========================================================================
  const teamModalOverlay = document.getElementById('teamModalOverlay');

  window.openTeamModal = function (e) {
    if (e && e.preventDefault) e.preventDefault();
    if (teamModalOverlay) {
      teamModalOverlay.classList.add('active');
      document.body.style.overflow = 'hidden';
      console.log('[PRAVAH] Team Modal opened.');
    }
  };

  window.closeTeamModal = function () {
    if (teamModalOverlay) {
      teamModalOverlay.classList.remove('active');
      document.body.style.overflow = '';
      console.log('[PRAVAH] Team Modal dismissed.');
    }
  };

  if (teamModalOverlay) {
    // Dismiss when clicking directly on the backdrop
    teamModalOverlay.addEventListener('click', (e) => {
      if (e.target === teamModalOverlay) {
        window.closeTeamModal();
      }
    });

    // Dismiss on Escape key press
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && teamModalOverlay.classList.contains('active')) {
        window.closeTeamModal();
      }
    });
  }

  // Expose global functions for manual testing in browser console
  window.PRAVAH = {
    showWarningPopup,
    dismissWarningPopup,
    openTeamModal: window.openTeamModal,
    closeTeamModal: window.closeTeamModal,
    updatePredictionUI,
    selectStation,
    getStationsData: () => CATCHMENT_STATIONS,
    getChartInstance: () => rainfallChartInstance,
  };
});

