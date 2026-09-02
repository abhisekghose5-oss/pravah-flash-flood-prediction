/**
 * PRAVAH — Web GIS 3D Globe Controller
 * Powered by Three.js & Globe.gl with holographic terminal HUD
 */

(function () {
  // 20 Central Water Commission & IndoFloods Western Ghats gauge stations
  const WESTERN_GHATS_STATIONS = [
    {
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
      color: '#ef4444',
      altitude: 0.09,
      radius: 0.85,
    },
    {
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
      color: '#ef4444',
      altitude: 0.09,
      radius: 0.85,
    },
    {
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
      color: '#f97316',
      altitude: 0.06,
      radius: 0.65,
    },
    {
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
      color: '#f97316',
      altitude: 0.06,
      radius: 0.65,
    },
    {
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
      color: '#eab308',
      altitude: 0.045,
      radius: 0.5,
    },
    {
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
      color: '#06b6d4',
      altitude: 0.035,
      radius: 0.45,
    },
    {
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
      color: '#eab308',
      altitude: 0.045,
      radius: 0.5,
    },
    {
      station_id: 'MH_GAK_04',
      name: 'Takli',
      river: 'Krishna',
      district: 'Kolhapur',
      lat: 16.6167,
      lng: 74.5500,
      rainfall: '14.5 mm',
      warning_level_m: 530.0,
      danger_level_m: 532.5,
      risk: 'NORMAL',
      color: '#06b6d4',
      altitude: 0.035,
      radius: 0.45,
    },
    {
      station_id: 'MH_GAK_05',
      name: 'Bhedasgaon',
      river: 'Varna',
      district: 'Kolhapur',
      lat: 16.8833,
      lng: 74.0167,
      rainfall: '16.0 mm',
      warning_level_m: 550.0,
      danger_level_m: 552.5,
      risk: 'NORMAL',
      color: '#06b6d4',
      altitude: 0.035,
      radius: 0.45,
    },
    {
      station_id: 'MH_GAK_06',
      name: 'Arjunwad',
      river: 'Krishna',
      district: 'Kolhapur',
      lat: 16.6500,
      lng: 74.5833,
      rainfall: '28.0 mm',
      warning_level_m: 531.0,
      danger_level_m: 533.5,
      risk: 'ADVISORY',
      color: '#eab308',
      altitude: 0.045,
      radius: 0.5,
    },
    {
      station_id: 'MH_GAK_07',
      name: 'Bastwad',
      river: 'Dudhganga',
      district: 'Kolhapur',
      lat: 16.6000,
      lng: 74.6333,
      rainfall: '12.0 mm',
      warning_level_m: 529.0,
      danger_level_m: 531.5,
      risk: 'NORMAL',
      color: '#06b6d4',
      altitude: 0.035,
      radius: 0.45,
    },
    {
      station_id: 'MH_GAK_08',
      name: 'Kowad',
      river: 'Tamraparni',
      district: 'Kolhapur',
      lat: 15.9500,
      lng: 74.3167,
      rainfall: '15.0 mm',
      warning_level_m: 640.0,
      danger_level_m: 642.5,
      risk: 'NORMAL',
      color: '#06b6d4',
      altitude: 0.035,
      radius: 0.45,
    },
    {
      station_id: 'MH_GAK_10',
      name: 'Warunji',
      river: 'Koyna',
      district: 'Satara',
      lat: 17.3167,
      lng: 74.1500,
      rainfall: '19.5 mm',
      warning_level_m: 564.0,
      danger_level_m: 566.5,
      risk: 'NORMAL',
      color: '#06b6d4',
      altitude: 0.035,
      radius: 0.45,
    },
    {
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
      color: '#06b6d4',
      altitude: 0.035,
      radius: 0.45,
    },
    {
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
      color: '#06b6d4',
      altitude: 0.035,
      radius: 0.45,
    },
    {
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
      color: '#f97316',
      altitude: 0.06,
      radius: 0.65,
    },
    {
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
      color: '#06b6d4',
      altitude: 0.035,
      radius: 0.45,
    },
    {
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
      color: '#eab308',
      altitude: 0.045,
      radius: 0.5,
    },
    {
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
      color: '#06b6d4',
      altitude: 0.035,
      radius: 0.45,
    },
    {
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
      color: '#06b6d4',
      altitude: 0.035,
      radius: 0.45,
    },
  ];

  let globeInstance = null;
  let idleTimer = null;
  let isInteracting = false;

  // Western Ghats regional target coordinate
  const WESTERN_GHATS_VIEW = {
    lat: 18.2,
    lng: 73.9,
    altitude: 0.72,
  };

  const GLOBAL_SPACE_VIEW = {
    lat: 20.0,
    lng: 55.0,
    altitude: 2.6,
  };

  /**
   * Initializes the 3D Globe using Globe.gl & Three.js
   */
  function initGlobe() {
    const container = document.getElementById('globeViewport');
    const loader = document.getElementById('globeLoader');
    const tooltip = document.getElementById('globeTooltip');

    if (!container) return;

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 540;

    // Check if Globe.gl library is loaded
    if (typeof Globe === 'undefined') {
      console.warn('[PRAVAH Globe] Globe.gl library not detected. Loading dynamically...');
      loadGlobeLibraries(() => initGlobe());
      return;
    }

    try {
      // 1. Initialize 3D Globe Instance
      globeInstance = Globe()(container)
        .width(width)
        .height(height)
        .globeImageUrl('https://unpkg.com/three-globe/example/img/earth-night.jpg')
        .bumpImageUrl('https://unpkg.com/three-globe/example/img/earth-topology.png')
        .backgroundImageUrl('https://unpkg.com/three-globe/example/img/night-sky.png')
        .atmosphereColor('#06b6d4')
        .atmosphereAltitude(0.24)
        .showAtmosphere(true);

      // 2. Add 20 Gauge Stations Points
      globeInstance
        .pointsData(WESTERN_GHATS_STATIONS)
        .pointLat('lat')
        .pointLng('lng')
        .pointColor('color')
        .pointAltitude('altitude')
        .pointRadius('radius')
        .pointResolution(24)
        .onPointHover((point, prevPoint) => {
          handlePointHover(point, tooltip);
        })
        .onPointClick((point) => {
          if (!point) return;
          // Smoothly fly camera to clicked gauge station
          globeInstance.pointOfView(
            {
              lat: point.lat,
              lng: point.lng,
              altitude: 0.45,
            },
            1200
          );
          // Highlight left sidebar station if available
          if (window.PRAVAH && window.PRAVAH.selectStation) {
            window.PRAVAH.selectStation(point.station_id);
          }
        });

      // 3. Add Pulsing Radar Wave Rings (Pulsing Red for Emergency & Cyan for Normal)
      globeInstance
        .ringsData(WESTERN_GHATS_STATIONS)
        .ringLat('lat')
        .ringLng('lng')
        .ringColor((d) =>
          d.risk === 'EMERGENCY'
            ? () => 'rgba(239, 68, 68, 0.75)'
            : d.risk === 'WARNING'
            ? () => 'rgba(249, 115, 22, 0.65)'
            : () => 'rgba(6, 182, 212, 0.55)'
        )
        .ringMaxRadius((d) => (d.risk === 'EMERGENCY' ? 4.2 : 2.0))
        .ringPropagationSpeed((d) => (d.risk === 'EMERGENCY' ? 3.8 : 1.6))
        .ringRepeatPeriod((d) => (d.risk === 'EMERGENCY' ? 650 : 1300));

      // 4. Set Initial Zoomed-Out Camera View (Space perspective)
      globeInstance.pointOfView(GLOBAL_SPACE_VIEW, 0);

      // 5. Configure Idle Spin (Slow Earth Rotation)
      const controls = globeInstance.controls();
      controls.autoRotate = true;
      controls.autoRotateSpeed = 0.5;
      controls.enableDamping = true;
      controls.dampingFactor = 0.08;

      // Pause rotation during user interaction, resume after 3.5s idle
      controls.addEventListener('start', () => {
        isInteracting = true;
        controls.autoRotate = false;
        clearTimeout(idleTimer);
      });

      controls.addEventListener('end', () => {
        clearTimeout(idleTimer);
        idleTimer = setTimeout(() => {
          isInteracting = false;
          controls.autoRotate = true;
        }, 3500);
      });

      // 6. Smoothly animate to Western Ghats on initial presentation after 1.8s
      setTimeout(() => {
        globeInstance.pointOfView(WESTERN_GHATS_VIEW, 2400);
      }, 1800);

      // 7. Hide Loader
      if (loader) {
        loader.style.opacity = '0';
        setTimeout(() => {
          loader.style.display = 'none';
        }, 400);
      }

      // 8. Bind Floating Overlay Controls
      bindMapControls();

      // 9. Handle Window Resize
      window.addEventListener('resize', handleResize);

      console.log('[PRAVAH] 3D Holographic Globe Initialized Successfully.');
    } catch (err) {
      console.error('[PRAVAH Globe Error]', err);
      if (loader) {
        loader.innerHTML = `
          <div style="color: #ef4444; font-family: monospace; text-align: center; padding: 2rem;">
            <p>Holographic 3D Globe Render Error</p>
            <small style="color: #94a3b8;">${err.message}</small>
          </div>
        `;
      }
    }
  }

  /**
   * Handles Tooltip positioning & custom styling on marker hover
   */
  function handlePointHover(point, tooltip) {
    if (!tooltip) return;

    if (!point) {
      tooltip.style.display = 'none';
      return;
    }

    // Populate Tooltip Fields
    const idEl = document.getElementById('tooltipStationId');
    const badgeEl = document.getElementById('tooltipRiskBadge');
    const nameEl = document.getElementById('tooltipStationName');
    const basinEl = document.getElementById('tooltipRiverBasin');
    const rainEl = document.getElementById('tooltipRainfall');
    const warnEl = document.getElementById('tooltipWarning');

    if (idEl) idEl.textContent = point.station_id;
    if (nameEl) nameEl.textContent = `${point.name} Gauge`;
    if (basinEl) basinEl.textContent = `${point.river} River • ${point.district}`;
    if (rainEl) rainEl.textContent = point.rainfall;
    if (warnEl) warnEl.textContent = `${point.warning_level_m} m`;

    if (badgeEl) {
      badgeEl.textContent = `${point.risk} RISK`;
      badgeEl.className = `tooltip-risk-pill ${point.risk.toLowerCase()}`;
    }

    // Position tooltip near mouse pointer
    tooltip.style.display = 'block';
  }

  /**
   * Bind Floating Glassmorphism Map Controls
   */
  function bindMapControls() {
    const zoomInBtn = document.getElementById('globeZoomInBtn');
    const zoomOutBtn = document.getElementById('globeZoomOutBtn');
    const resetBtn = document.getElementById('globeResetGhatsBtn');

    if (zoomInBtn) {
      zoomInBtn.addEventListener('click', () => {
        if (!globeInstance) return;
        const currentPov = globeInstance.pointOfView();
        globeInstance.pointOfView(
          {
            ...currentPov,
            altitude: Math.max(0.18, currentPov.altitude - 0.35),
          },
          600
        );
      });
    }

    if (zoomOutBtn) {
      zoomOutBtn.addEventListener('click', () => {
        if (!globeInstance) return;
        const currentPov = globeInstance.pointOfView();
        globeInstance.pointOfView(
          {
            ...currentPov,
            altitude: Math.min(3.5, currentPov.altitude + 0.45),
          },
          600
        );
      });
    }

    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        if (!globeInstance) return;
        globeInstance.pointOfView(WESTERN_GHATS_VIEW, 1600);
      });
    }
  }

  /**
   * Resize Handler
   */
  function handleResize() {
    const container = document.getElementById('globeViewport');
    if (!container || !globeInstance) return;
    globeInstance.width(container.clientWidth).height(container.clientHeight);
  }

  /**
   * Dynamic CDN Loader fallback
   */
  function loadGlobeLibraries(onReady) {
    if (typeof THREE === 'undefined') {
      const threeScript = document.createElement('script');
      threeScript.src = 'https://unpkg.com/three@0.160.0/build/three.min.js';
      threeScript.onload = () => {
        loadGlobeScript(onReady);
      };
      document.head.appendChild(threeScript);
    } else {
      loadGlobeScript(onReady);
    }
  }

  function loadGlobeScript(onReady) {
    const globeScript = document.createElement('script');
    globeScript.src = 'https://unpkg.com/globe.gl@2.32.0/dist/globe.gl.min.js';
    globeScript.onload = () => {
      if (onReady) onReady();
    };
    document.head.appendChild(globeScript);
  }

  // Auto-boot on DOM Content Loaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initGlobe);
  } else {
    initGlobe();
  }

  // Expose global control instance
  window.PRAVAH_GLOBE = {
    resetToWesternGhats: () => globeInstance && globeInstance.pointOfView(WESTERN_GHATS_VIEW, 1500),
    zoomToGlobal: () => globeInstance && globeInstance.pointOfView(GLOBAL_SPACE_VIEW, 1500),
    getStations: () => WESTERN_GHATS_STATIONS,
  };
})();
