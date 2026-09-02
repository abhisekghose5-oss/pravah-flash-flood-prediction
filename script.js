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

  // Animate Gauge on initial page load (starts at 0% and animates to 84% with 7-day chart data)
  setTimeout(() => {
    updatePredictionUI(84, 'EMERGENCY', [22.4, 38.0, 45.2, 59.5, 92.0, 110.5, 85.0]);
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
    getChartInstance: () => rainfallChartInstance,
  };
});

